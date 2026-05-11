from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session, select
from decimal import Decimal

class Leader(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    address: str = Field(index=True, unique=True)
    nickname: Optional[str] = None
    is_active: bool = Field(default=True)
    total_trades: int = Field(default=0)
    total_pnl: Decimal = Field(default=Decimal("0"), decimal_places=6, max_digits=20)
    last_seen_ledger: Optional[int] = None

class Follower(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    address: str = Field(index=True, unique=True)
    sizing_pct: Decimal = Field(default=Decimal("10.0"), decimal_places=2, max_digits=5)
    max_per_trade_xrp: Decimal = Field(default=Decimal("100"), decimal_places=2, max_digits=10)
    is_active: bool = Field(default=True)

class FollowRelation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    follower_id: int = Field(foreign_key="follower.id")
    leader_id: int = Field(foreign_key="leader.id")

class MirrorTrade(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    leader_id: int = Field(foreign_key="leader.id")
    follower_id: int = Field(foreign_key="follower.id")
    leader_tx_hash: str
    follower_tx_hash: str
    pair: str
    direction: str  # buy/sell
    amount: Decimal = Field(decimal_places=6, max_digits=20)
    entry_price: Decimal = Field(decimal_places=6, max_digits=20)
    status: str = Field(default="pending") # pending, success, failed
    timestamp: datetime = Field(default_factory=datetime.utcnow)

def init_db(db_url: str):
    engine = create_engine(db_url)
    SQLModel.metadata.create_all(engine)
    return engine
