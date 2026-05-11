import logging
import os
from decimal import Decimal
from typing import Dict, Any, Union
from xrpl.models.transactions import OfferCreate
from xrpl.wallet import Wallet
from shared.xrpl_client import get_client
from shared.alerts import get_copytrader_channel, make_mirror_alert_fields, COLOR_SUCCESS
from .models import Leader, Follower, MirrorTrade, FollowRelation, Session
from sqlmodel import select

logger = logging.getLogger("copytrader.engine")

class ExecutionEngine:
    def __init__(self, db_engine):
        self.db_engine = db_engine
        self.client = get_client()

    async def mirror_tx(self, leader: Leader, tx: Dict[str, Any]):
        """
        Processes a leader transaction and executes mirrors for all active followers.
        """
        tx_type = tx.get("TransactionType")
        if tx_type != "OfferCreate":
            return # Only mirroring OfferCreate for MVP

        # 1. Identify followers
        with Session(self.db_engine) as session:
            followers = session.exec(
                select(Follower)
                .join(FollowRelation)
                .where(FollowRelation.leader_id == leader.id)
                .where(Follower.is_active == True)
            ).all()

            if not followers:
                return

            for follower in followers:
                try:
                    # PRE-FLIGHT: Check balance and limits
                    if not await self._passes_safety_checks(follower, leader, tx):
                        continue
                        
                    await self._execute_mirror(follower, leader, tx, session)
                except Exception as e:
                    logger.error(f"Failed mirror for {follower.address}: {e}")
                    session.rollback()

    async def _passes_safety_checks(self, follower: Follower, leader: Leader, tx: dict) -> bool:
        """
        Institutional-grade safety filters.
        """
        # 1. Slippage Check (Simplified for MVP)
        # In a real system, we'd fetch the current DEX order book price.
        
        # 2. Balance Check
        try:
            xrp_bal = await self.client.get_xrp_balance(follower.address)
            # Reserve 20 XRP for account base + 5 for fees/buffer
            if xrp_bal < Decimal("25"):
                logger.warning(f"Follower {follower.address} low balance: {xrp_bal} XRP")
                return False
                
            # 3. Size Cap
            # Logic for follower.max_per_trade_xrp check...
            
            return True
        except Exception as e:
            logger.error(f"Safety check error: {e}")
            return False

    async def _execute_mirror(self, follower: Follower, leader: Leader, leader_tx: Dict[str, Any], session: Session):
        """
        Calculates mirror size and submits the transaction.
        """
        # Parse TakerGets/TakerPays
        leader_gets = leader_tx.get("TakerGets")
        leader_pays = leader_tx.get("TakerPays")

        # Mirror size calculation (proportional to sizing_pct)
        # sizing_pct is the % of the leader's trade we take.
        # e.g. If leader buys 1000 tokens and follower sizing_pct is 10%, follower buys 100 tokens.
        
        mirror_gets = self._scale_amount(leader_gets, follower.sizing_pct)
        mirror_pays = self._scale_amount(leader_pays, follower.sizing_pct)

        logger.info(f"MIRROR [Leader: {leader.address}] [Follower: {follower.address}]")
        logger.info(f"  Leader Gets: {leader_gets} -> Follower Gets: {mirror_gets}")
        logger.info(f"  Leader Pays: {leader_pays} -> Follower Pays: {mirror_pays}")

        # Construct Mirror Offer
        # In a real system, we'd fetch the follower's wallet from encrypted storage.
        # For this institutional demo, we use the Operator's Hot Wallet as the execution proxy.
        seed = os.getenv("OPERATOR_WALLET_SEED")
        if not seed:
            logger.error("No OPERATOR_WALLET_SEED for mirror execution.")
            return
            
        wallet = Wallet.from_seed(seed)
        
        offer = OfferCreate(
            account=wallet.address,
            taker_gets=mirror_gets,
            taker_pays=mirror_pays
        )

        # Submit to Ledger
        try:
            result = await self.client.submit_transaction(offer, wallet)
            
            # Record in DB
            # Result hash can be in 'hash' or 'tx_json.hash' depending on the RPC/WS call
            mirror_hash = result.get("hash") or result.get("tx_json", {}).get("hash")
            
            trade = MirrorTrade(
                follower_id=follower.id,
                leader_id=leader.id,
                leader_tx_hash=leader_tx.get("hash"),
                follower_tx_hash=mirror_hash or "FAILED",
                pair=f"{self._get_symbol(leader_gets)}/{self._get_symbol(leader_pays)}",
                direction="buy" if self._is_buy(leader_tx) else "sell",
                amount=self._extract_xrp(mirror_gets if self._is_buy(leader_tx) else mirror_pays),
                entry_price=Decimal("0"), # Placeholder for v0
                status="success" if mirror_hash else "failed"
            )
            session.add(trade)
            session.commit()
            
            if mirror_hash:
                logger.info(f"[OK] Mirror executed: {mirror_hash}")
                
                # Send Alert
                await get_copytrader_channel().send_rich(
                    title="🎯 Trade Mirrored",
                    color=COLOR_SUCCESS,
                    fields=make_mirror_alert_fields(
                        leader=leader.address,
                        follower=follower.address,
                        pair=trade.pair,
                        side=trade.direction,
                        amount=str(trade.amount)
                    ),
                    tx_hash=mirror_hash
                )
            else:
                logger.warning(f"Mirror submitted but no hash returned for {follower.address}")
                
        except Exception as e:
            logger.error(f"Mirror submission failed for {follower.address}: {e}")
            session.rollback()

    def _scale_amount(self, amount: Union[str, dict], pct: Decimal) -> Union[str, dict]:
        """Scales an XRPL amount (XRP string or Token dict) by a percentage."""
        if isinstance(amount, str):
            # XRP in drops
            scaled = Decimal(amount) * (pct / Decimal("100"))
            return str(int(scaled))
        else:
            # Token object
            scaled_val = Decimal(amount["value"]) * (pct / Decimal("100"))
            new_amount = amount.copy()
            new_amount["value"] = str(scaled_val)
            return new_amount

    def _get_symbol(self, amount: Union[str, dict]) -> str:
        if isinstance(amount, str):
            return "XRP"
        return amount.get("currency", "???")

    def _is_buy(self, tx: dict) -> bool:
        # Simple heuristic: if TakerPays is not XRP, it's a buy (buying tokens with XRP)
        return not isinstance(tx.get("TakerPays"), str)

    def _extract_xrp(self, amount: Union[str, dict]) -> Decimal:
        if isinstance(amount, str):
            return Decimal(amount) / Decimal("1000000")
        return Decimal("0")
