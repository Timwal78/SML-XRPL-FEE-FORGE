import logging
import os
import hashlib
from decimal import Decimal
from typing import Optional
from shared.xrpl_client import get_client
from .models import Token, LaunchTrade
from .curve import BondingCurve
from shared.alerts import get_launchpad_channel, make_launchpad_alert_fields, COLOR_SUCCESS, COLOR_INFO
from xrpl.models.transactions import AMMCreate, Payment, TrustSet
from xrpl.wallet import Wallet
from xrpl.asyncio.transaction import autofill_and_sign, submit_and_wait
from xrpl.models.amounts import IssuedCurrencyAmount

from .models import Token, LaunchTrade, Session
from sqlmodel import select

logger = logging.getLogger("launchpad.forge")

class TokenForge:
    def __init__(self, db_engine):
        self.db_engine = db_engine
        self.client = get_client()
        self.curve = BondingCurve()

    async def create_token(self, name: str, symbol: str, creator_addr: str) -> Token:
        # Generate a unique currency code (40-char hex)
        # Using uppercase hex as per XRPL standard
        currency_code = hashlib.sha256(f"{symbol}-{name}-{creator_addr}".encode()).hexdigest()[:40].upper()
        
        with Session(self.db_engine) as session:
            token = Token(
                name=name,
                symbol=symbol,
                currency_code=currency_code,
                issuer=os.getenv("OPERATOR_WALLET_ADDRESS"),
                creator_address=creator_addr
            )
            session.add(token)
            session.commit()
            session.refresh(token)
            return token

    async def buy_tokens(self, token_id: int, buyer_addr: str, amount_tokens: Decimal):
        with Session(self.db_engine) as session:
            token = session.get(Token, token_id)
            if not token or token.status != "bonding":
                raise ValueError("Token not available for bonding.")

            cost_xrp = self.curve.calculate_cost(token.circulating_supply, amount_tokens)
            
            # 1. Update DB
            token.circulating_supply += amount_tokens
            token.funding_raised_xrp += cost_xrp
            token.current_price_xrp = self.curve.get_price(token.circulating_supply)
            
            trade = LaunchTrade(
                token_id=token.id,
                buyer_address=buyer_addr,
                direction="buy",
                amount_tokens=amount_tokens,
                amount_xrp=cost_xrp,
                price_xrp=token.current_price_xrp
            )
            
            session.add(token)
            session.add(trade)
            
            # Send Alert
            await get_launchpad_channel().send_rich(
                title="🚀 Token Purchase",
                color=COLOR_SUCCESS,
                fields=make_launchpad_alert_fields(
                    token=token.name,
                    symbol=token.symbol,
                    action="buy",
                    amount=f"{amount_tokens} {token.symbol}",
                    price=str(token.current_price_xrp)
                )
            )

            # Check if goal reached
            if token.funding_raised_xrp >= token.funding_goal_xrp:
                await self._seed_amm(token, session)
            
            session.commit()
            return trade

    async def _seed_amm(self, token: Token, session: Session):
        """
        Migrates the bonding curve to the native XRPL AMM.
        """
        logger.info(f"Token {token.symbol} reached funding goal! Seeding AMM...")
        
        seed = os.getenv("OPERATOR_WALLET_SEED")
        if not seed:
            logger.error("No OPERATOR_WALLET_SEED for AMM seeding.")
            return
            
        wallet = Wallet.from_seed(seed)
        
        # 1. Prepare amounts
        # We put all raised XRP and the remaining supply into the AMM
        total_supply = token.total_supply
        remaining_tokens = total_supply - token.circulating_supply
        raised_drops = str(int(token.funding_raised_xrp * Decimal("1000000")))
        
        token_amount = IssuedCurrencyAmount(
            currency=token.currency_code,
            issuer=token.issuer,
            value=str(remaining_tokens)
        )
        
        # 2. Create AMM
        # Asset1 = XRP, Asset2 = New Token
        amm_req = AMMCreate(
            account=wallet.address,
            amount=raised_drops,
            amount2=token_amount,
            trading_fee=50 # 0.5% fee
        )
        
        try:
            signed = await autofill_and_sign(amm_req, self.client.rpc, wallet)
            result = await submit_and_wait(signed, self.client.rpc, wallet)
            
            if result.is_successful():
                token.status = "seeded"
                logger.info(f"[OK] AMM Created for {token.symbol}: {result.result.get('hash')}")
                
                # Send Alert
                await get_launchpad_channel().send_rich(
                    title="💎 AMM Seeded (Goal Reached)",
                    color=COLOR_INFO,
                    fields=make_launchpad_alert_fields(
                        token=token.name,
                        symbol=token.symbol,
                        action="migration",
                        amount=f"{token.total_supply} {token.symbol}",
                        price=str(token.current_price_xrp)
                    ),
                    tx_hash=result.result.get("hash")
                )
            else:
                logger.error(f"[X] AMM Creation failed: {result.result.get('meta', {}).get('TransactionResult')}")
                token.status = "failed"
                
        except Exception as e:
            logger.exception(f"Error during AMM seeding: {e}")
            token.status = "failed"
            
        session.add(token)
        # Note: commit happens in the calling function (buy_tokens)
