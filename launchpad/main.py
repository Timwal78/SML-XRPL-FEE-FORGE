import logging
from fastapi import FastAPI, Depends
from sqlmodel import Session, select
from .models import init_db, Token, LaunchTrade
from .forge import TokenForge
import os
from dotenv import load_dotenv
from decimal import Decimal

load_dotenv()
DB_URL = os.getenv("LAUNCHPAD_DB_URL", "sqlite:///./launchpad.db")
db_engine = init_db(DB_URL)

app = FastAPI(title="SML Memecoin Launchpad")

def get_session():
    with Session(db_engine) as session:
        yield session

@app.get("/health")
def health():
    return {"status": "healthy", "engine": "launchpad"}

@app.post("/tokens")
async def create_token(name: str, symbol: str, creator_addr: str):
    forge = TokenForge(db_engine)
    return await forge.create_token(name, symbol, creator_addr)

@app.get("/tokens")
def list_tokens(session: Session = Depends(get_session)):
    return session.exec(select(Token)).all()

@app.post("/buy")
async def buy_token(token_id: int, buyer_addr: str, amount_tokens: float):
    forge = TokenForge(db_engine)
    return await forge.buy_tokens(token_id, buyer_addr, Decimal(str(amount_tokens)))
