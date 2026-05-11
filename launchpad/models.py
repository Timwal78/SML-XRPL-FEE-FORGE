from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session, select
from decimal import Decimal

class Token(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    name: str
    currency_code: str = Field(unique=True) # 40-char hex
    issuer: str
    creator_address: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    
    # Bonding curve stats
    total_supply: Decimal = Field(default=Decimal("1000000000"), decimal_places=6, max_digits=30)
    circulating_supply: Decimal = Field(default=Decimal("0"), decimal_places=6, max_digits=30)
    current_price_xrp: Decimal = Field(default=Decimal("0.00001"), decimal_places=10, max_digits=20)
    market_cap_xrp: Decimal = Field(default=Decimal("0"), decimal_places=6, max_digits=30)
    funding_raised_xrp: Decimal = Field(default=Decimal("0"), decimal_places=6, max_digits=30)
    funding_goal_xrp: Decimal = Field(default=Decimal("50000"), decimal_places=6, max_digits=30) # Goal to seed AMM
    
    status: str = Field(default="bonding") # bonding, seeded, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)

class LaunchTrade(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    token_id: int = Field(foreign_key="token.id")
    buyer_address: str
    direction: str # buy/sell
    amount_tokens: Decimal = Field(decimal_places=6, max_digits=30)
    amount_xrp: Decimal = Field(decimal_places=6, max_digits=30)
    price_xrp: Decimal = Field(decimal_places=10, max_digits=20)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

def init_db(db_url: str):
    engine = create_engine(db_url)
    SQLModel.metadata.create_all(engine)
    return engine
