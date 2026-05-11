import os
from sqlmodel import Session, create_engine
from copytrader.models import Leader, Follower, FollowRelation, init_db
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("COPYTRADER_DB_URL", "sqlite:///./copytrader.db")

def seed():
    engine = init_db(DB_URL)
    with Session(engine) as session:
        # 1. Add a Leader (Example testnet address)
        leader = Leader(address="rPT1Sjq2YGrvB3yS2FY8Qs9zbsPdmAFWGi", nickname="DEX_Whale_1")
        session.add(leader)
        
        # 2. Add a Follower (The operator wallet we just created)
        operator_addr = os.getenv("OPERATOR_WALLET_ADDRESS")
        follower = Follower(address=operator_addr, sizing_pct=10.0)
        session.add(follower)
        
        session.commit()
        session.refresh(leader)
        session.refresh(follower)
        
        # 3. Create Relation
        relation = FollowRelation(leader_id=leader.id, follower_id=follower.id)
        session.add(relation)
        session.commit()
        
        print(f"[OK] Copy-Trader DB seeded.")
        print(f"  Leader:   {leader.address}")
        print(f"  Follower: {follower.address}")

if __name__ == "__main__":
    seed()
