import asyncio
import os
import json
import logging
from decimal import Decimal
from xrpl.asyncio.wallet import generate_faucet_wallet
from xrpl.wallet import Wallet
from xrpl.models.transactions import OfferCreate
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.asyncio.transaction import autofill_and_sign, submit_and_wait
from shared.xrpl_client import get_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stress-test")

STATE_FILE = "scratch/stress_leader.json"

async def run_stress_test(num_trades: int = 10):
    client = get_client()
    
    logger.info("--- STRESS TEST START ---")
    
    # 1. Load or Generate Leader
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            leader_wallet = Wallet.from_seed(data["seed"])
            logger.info(f"Loaded existing Stress Leader: {leader_wallet.address}")
    else:
        logger.info("Generating and funding NEW Stress Leader wallet...")
        leader_wallet = await generate_faucet_wallet(client.rpc)
        os.makedirs("scratch", exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump({"address": leader_wallet.address, "seed": leader_wallet.seed}, f)
        logger.info(f"Saved NEW Leader: {leader_wallet.address}")
    
    # 2. Register in DB
    from copytrader.models import Leader, Follower, FollowRelation
    from sqlmodel import Session, create_engine, select
    
    db_url = os.getenv("COPYTRADER_DATABASE_URL", "sqlite:///copytrader.db")
    engine = create_engine(db_url)
    
    with Session(engine) as session:
        db_leader = session.exec(select(Leader).where(Leader.address == leader_wallet.address)).first()
        if not db_leader:
            db_leader = Leader(address=leader_wallet.address, nickname="Stress Test Whale")
            session.add(db_leader)
            session.commit()
            session.refresh(db_leader)
            logger.info("Registered Leader in DB. PLEASE RESTART COPYTRADER NOW if not running.")
            await asyncio.sleep(5) # Pause to allow restart if manual
        
        db_follower = session.exec(select(Follower)).first()
        if not db_follower:
            addr = os.getenv("OPERATOR_WALLET_ADDRESS", "rPT1Sjq2YGrvB3yS2FY8Qs9zbsPdmAFWGi")
            db_follower = Follower(address=addr, sizing_pct=Decimal("10"))
            session.add(db_follower)
            session.commit()
            session.refresh(db_follower)
            
        rel = session.exec(
            select(FollowRelation)
            .where(FollowRelation.leader_id == db_leader.id)
            .where(FollowRelation.follower_id == db_follower.id)
        ).first()
        if not rel:
            rel = FollowRelation(leader_id=db_leader.id, follower_id=db_follower.id)
            session.add(rel)
            session.commit()
        
    logger.info("Starting burst of trades...")

    # 3. Burst Trades
    for i in range(num_trades):
        logger.info(f"Firing Leader Trade #{i+1}...")
        offer = OfferCreate(
            account=leader_wallet.address,
            taker_gets="1000000",
            taker_pays=IssuedCurrencyAmount(
                currency="STR",
                issuer=leader_wallet.address,
                value=str(Decimal("100") + Decimal(i))
            )
        )
        
        try:
            signed = await autofill_and_sign(offer, client.rpc, leader_wallet)
            result = await submit_and_wait(signed, client.rpc)
            logger.info(f"  Sent: {signed.get_hash()} - Status: {result.result.get('meta', {}).get('TransactionResult')}")
        except Exception as e:
            logger.error(f"  Error firing trade: {e}")
            
        await asyncio.sleep(1)

    logger.info("--- BURST COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(run_stress_test(5))
