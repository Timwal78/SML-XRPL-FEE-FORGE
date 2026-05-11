import asyncio
import os
import random
import logging
from decimal import Decimal
from dotenv import load_dotenv
from launchpad.forge import TokenForge
from launchpad.models import init_db, Token
from sqlmodel import Session, create_engine, select

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("launchpad-test")

async def run_test():
    db_url = os.getenv("LAUNCHPAD_DATABASE_URL", "sqlite:///launchpad.db")
    engine = init_db(db_url)
    
    with Session(engine) as session:
        forge = TokenForge(session)
        
        # 1. Create Token
        symbol = f"STRS{random.randint(100, 999)}"
        logger.info(f"Creating token {symbol}...")
        token = await forge.create_token("Stress Coin", symbol, "rBuyerAddress...")
        token.funding_goal_xrp = Decimal("10") # Lower goal for test
        session.add(token)
        session.commit()
        
        logger.info(f"Created: {token.name} ({token.symbol}) - ID: {token.id}")
        
        # 2. Buy enough to trigger migration
        logger.info("Buying tokens to hit goal...")
        token.funding_raised_xrp = Decimal("9.9")
        session.add(token)
        session.commit()
        
        logger.info("Final buy to trigger AMM migration...")
        trade = await forge.buy_tokens(token.id, "rBuyerAddress...", Decimal("100000"))
        logger.info(f"Trade result: {trade.amount_xrp} XRP spent")
        logger.info(f"New funding level: {token.funding_raised_xrp}")
        
        # Check token status
        session.refresh(token)
        logger.info(f"Final Token Status: {token.status}")

if __name__ == "__main__":
    asyncio.run(run_test())
