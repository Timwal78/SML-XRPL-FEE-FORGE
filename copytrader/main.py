import logging
import asyncio
from typing import Optional, List
from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from .models import init_db, Leader, Follower, Session, select
from .watcher import LeaderWatcher
from shared.xrpl_client import get_client

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("copytrader.main")

# Database URL from env
import os
from dotenv import load_dotenv
load_dotenv()
DB_URL = os.getenv("COPYTRADER_DB_URL", "sqlite:///./copytrader.db")
db_engine = init_db(DB_URL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the watcher in the background
    logger.info("Starting COPY-TRADER service...")
    
    with Session(db_engine) as session:
        leaders = session.exec(select(Leader).where(Leader.is_active == True)).all()
        leader_addrs = [l.address for l in leaders]

    if leader_addrs:
        watcher = LeaderWatcher(db_engine)
        asyncio.create_task(watcher.start(leader_addrs))
    else:
        logger.warning("No active leaders found to watch.")
        
    yield
    # Shutdown logic if needed

app = FastAPI(title="SML Copy-Trader", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "healthy", "engine": "copy-trader"}

@app.post("/leaders")
def add_leader(address: str, nickname: Optional[str] = None):
    with Session(db_engine) as session:
        leader = Leader(address=address, nickname=nickname)
        session.add(leader)
        session.commit()
        session.refresh(leader)
        return leader

@app.get("/leaders")
def list_leaders():
    with Session(db_engine) as session:
        return session.exec(select(Leader)).all()
