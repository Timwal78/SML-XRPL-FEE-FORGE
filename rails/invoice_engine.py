"""
RLUSD RAILS — invoice engine.

Creates invoices, derives unique uint32 destination tags, persists to ledger.
Each invoice = customer pays operator hot wallet → operator splits → merchant
gets `merchant_payout`, operator keeps `fee_amount`.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select

from shared.rlusd import Money
from rails.fee_engine import calc_invoice_split


DEST_TAG_MASK = 0x7FFFFFFF  # 31-bit clamp for safety margin


class Invoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    merchant_id: str = Field(index=True)
    merchant_addr: str
    customer_addr: Optional[str] = None
    amount: str  # Decimal string
    currency: str  # XRP or RLUSD
    fee_amount: str
    merchant_payout: str
    destination_tag: int = Field(index=True)
    status: str = Field(default="pending", index=True)  # pending|paid|expired|cancelled
    payment_tx_hash: Optional[str] = None
    payout_tx_hash: Optional[str] = None
    description: Optional[str] = None
    ai_headline: Optional[str] = None
    ai_blurb: Optional[str] = None


class InvoiceLedger:
    def __init__(self, db_url: Optional[str] = None):
        url = db_url or os.environ.get("RAILS_DB_URL", "sqlite:///./rails.db")
        self.engine = create_engine(url, echo=False)
        if url.startswith("sqlite"):
            from sqlalchemy import text
            with self.engine.connect() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.commit()
        SQLModel.metadata.create_all(self.engine)

    def _derive_tag(self, invoice_id: str) -> int:
        """SHA256-derive a 31-bit destination tag, collision-checked."""
        for salt in range(0, 64):
            base = f"{invoice_id}:{salt}".encode()
            digest = hashlib.sha256(base).digest()
            tag = int.from_bytes(digest[:4], "big") & DEST_TAG_MASK
            if not self.tag_exists_active(tag):
                return tag
        raise RuntimeError("could not derive collision-free dest tag in 64 attempts")

    def tag_exists_active(self, tag: int) -> bool:
        with Session(self.engine) as s:
            stmt = select(Invoice).where(
                Invoice.destination_tag == tag,
                Invoice.status == "pending",
            )
            return s.exec(stmt).first() is not None

    def create(
        self,
        merchant_id: str,
        merchant_addr: str,
        amount: Decimal,
        currency: str,
        ttl_seconds: int = 3600,
        description: Optional[str] = None,
        ai_headline: Optional[str] = None,
        ai_blurb: Optional[str] = None,
    ) -> Invoice:
        invoice_id = uuid.uuid4().hex[:16]
        gross = Money(amount, currency)
        merchant_payout, fee = calc_invoice_split(gross)
        tag = self._derive_tag(invoice_id)

        inv = Invoice(
            invoice_id=invoice_id,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
            merchant_id=merchant_id,
            merchant_addr=merchant_addr,
            amount=str(gross.amount),
            currency=currency,
            fee_amount=str(fee.amount),
            merchant_payout=str(merchant_payout.amount),
            destination_tag=tag,
            description=description,
            ai_headline=ai_headline,
            ai_blurb=ai_blurb,
        )
        with Session(self.engine) as s:
            s.add(inv)
            s.commit()
            s.refresh(inv)
            return inv

    def get_by_tag(self, tag: int) -> Optional[Invoice]:
        with Session(self.engine) as s:
            stmt = select(Invoice).where(
                Invoice.destination_tag == tag, Invoice.status == "pending"
            )
            return s.exec(stmt).first()

    def get(self, invoice_id: str) -> Optional[Invoice]:
        with Session(self.engine) as s:
            stmt = select(Invoice).where(Invoice.invoice_id == invoice_id)
            return s.exec(stmt).first()

    def mark_paid(
        self,
        invoice_id: str,
        customer_addr: str,
        payment_tx_hash: str,
        payout_tx_hash: Optional[str] = None,
    ) -> None:
        with Session(self.engine) as s:
            stmt = select(Invoice).where(Invoice.invoice_id == invoice_id)
            row = s.exec(stmt).first()
            if not row:
                return
            row.status = "paid"
            row.customer_addr = customer_addr
            row.payment_tx_hash = payment_tx_hash
            if payout_tx_hash:
                row.payout_tx_hash = payout_tx_hash
            s.add(row)
            s.commit()

    def expire_due(self) -> int:
        """Marks all overdue pending invoices as expired. Returns count."""
        now = datetime.now(timezone.utc)
        count = 0
        with Session(self.engine) as s:
            stmt = select(Invoice).where(
                Invoice.status == "pending",
                Invoice.expires_at < now,
            )
            for row in s.exec(stmt):
                row.status = "expired"
                s.add(row)
                count += 1
            s.commit()
        return count

    def recent(self, limit: int = 50) -> list[Invoice]:
        with Session(self.engine) as s:
            stmt = select(Invoice).order_by(Invoice.id.desc()).limit(limit)
            return list(s.exec(stmt))


_inv_ledger: Optional[InvoiceLedger] = None


def get_invoice_ledger() -> InvoiceLedger:
    global _inv_ledger
    if _inv_ledger is None:
        _inv_ledger = InvoiceLedger()
    return _inv_ledger
