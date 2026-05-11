"""
TIPHAWK — SQLite ledger.

Persists every tip event for accounting, dashboard, and AI digest input.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select


class TipRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Twitter context
    tweet_id: str = Field(index=True)
    sender_handle: str = Field(index=True)
    recipient_handle: str = Field(index=True)
    tweet_text: str

    # XRPL context
    sender_addr: str
    recipient_addr: str
    currency: str  # XRP or RLUSD
    gross_amount: str  # Decimal as string
    fee_amount: str
    net_amount: str

    # Result
    status: str = Field(default="pending", index=True)  # pending|sent|failed
    tx_hash: Optional[str] = Field(default=None, index=True)
    error: Optional[str] = None


class Ledger:
    def __init__(self, db_url: Optional[str] = None):
        url = db_url or os.environ.get("TIPHAWK_DB_URL", "sqlite:///./tiphawk.db")
        self.engine = create_engine(url, echo=False)
        # Enable WAL for concurrent reads during writes (SQLite only)
        if url.startswith("sqlite"):
            with self.engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.commit()
        SQLModel.metadata.create_all(self.engine)

    def record(self, **kwargs) -> TipRecord:
        with Session(self.engine) as s:
            row = TipRecord(**kwargs)
            s.add(row)
            s.commit()
            s.refresh(row)
            return row

    def update_status(
        self,
        record_id: int,
        status: str,
        tx_hash: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        with Session(self.engine) as s:
            row = s.get(TipRecord, record_id)
            if row:
                row.status = status
                if tx_hash:
                    row.tx_hash = tx_hash
                if error:
                    row.error = error
                s.add(row)
                s.commit()

    def recent(self, limit: int = 50) -> list[TipRecord]:
        with Session(self.engine) as s:
            stmt = select(TipRecord).order_by(TipRecord.id.desc()).limit(limit)
            return list(s.exec(stmt))

    def by_status(self, status: str, limit: int = 100) -> list[TipRecord]:
        with Session(self.engine) as s:
            stmt = (
                select(TipRecord)
                .where(TipRecord.status == status)
                .order_by(TipRecord.id.desc())
                .limit(limit)
            )
            return list(s.exec(stmt))

    def daily_top(self, day: datetime, limit: int = 10) -> list[TipRecord]:
        """Top tips by gross amount for a given day. Used by AI digest."""
        with Session(self.engine) as s:
            stmt = (
                select(TipRecord)
                .where(TipRecord.status == "sent")
                .order_by(TipRecord.gross_amount.desc())
                .limit(limit)
            )
            return list(s.exec(stmt))


_ledger: Optional[Ledger] = None


def get_ledger() -> Ledger:
    global _ledger
    if _ledger is None:
        _ledger = Ledger()
    return _ledger
