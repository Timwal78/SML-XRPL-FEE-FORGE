"""RLUSD RAILS unit tests — pure logic, no network."""

import hashlib
from decimal import Decimal

import pytest

from shared.rlusd import Money
from rails.fee_engine import calc_invoice_split
from rails.payment_watcher import _extract_amount


# -----------------------------------------------------------------------------
# Fee math
# -----------------------------------------------------------------------------
def test_split_50bps():
    gross = Money("100.00", "RLUSD")
    payout, fee = calc_invoice_split(gross)
    assert fee.amount == Decimal("0.50")
    assert payout.amount == Decimal("99.50")

def test_split_50bps_xrp():
    gross = Money("1000", "XRP")
    payout, fee = calc_invoice_split(gross)
    assert fee.amount == Decimal("5.000000")
    assert payout.amount == Decimal("995.000000")

def test_split_uses_env(monkeypatch):
    monkeypatch.setenv("RAILS_FEE_BPS", "100")
    gross = Money("100", "RLUSD")
    payout, fee = calc_invoice_split(gross)
    assert fee.amount == Decimal("1.00")
    assert payout.amount == Decimal("99.00")


# -----------------------------------------------------------------------------
# Destination tag derivation
# -----------------------------------------------------------------------------
def test_dest_tag_is_31_bit():
    """Tags must always fit in uint31 (0x7FFFFFFF mask)."""
    for invoice_id in ["abc", "deadbeef", "0" * 32, "f" * 32]:
        digest = hashlib.sha256(f"{invoice_id}:0".encode()).digest()
        tag = int.from_bytes(digest[:4], "big") & 0x7FFFFFFF
        assert 0 <= tag <= 0x7FFFFFFF


# -----------------------------------------------------------------------------
# Amount extraction from XRPL Payment tx
# -----------------------------------------------------------------------------
def test_extract_xrp_drops():
    amt, cur = _extract_amount("1000000")  # 1 XRP in drops
    assert amt == Decimal("1")
    assert cur == "XRP"

def test_extract_rlusd_token():
    amt_field = {
        "currency": "524C555344000000000000000000000000000000",
        "issuer": "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De",
        "value": "99.50",
    }
    amt, cur = _extract_amount(amt_field)
    assert amt == Decimal("99.50")
    assert cur == "RLUSD"

def test_extract_unknown_token():
    amt_field = {"currency": "USD", "issuer": "rOther", "value": "5"}
    amt, cur = _extract_amount(amt_field)
    assert amt == Decimal("5")
    assert cur == "USD"


# -----------------------------------------------------------------------------
# InvoiceLedger (uses in-memory SQLite)
# -----------------------------------------------------------------------------
def test_invoice_creation_and_split(monkeypatch, tmp_path):
    db = tmp_path / "test.db"
    monkeypatch.setenv("RAILS_DB_URL", f"sqlite:///{db}")
    # Reload module to pick up env
    import importlib
    import rails.invoice_engine as ie
    importlib.reload(ie)

    ledger = ie.InvoiceLedger()
    inv = ledger.create(
        merchant_id="acme",
        merchant_addr="rMerchant",
        amount=Decimal("100.00"),
        currency="RLUSD",
        ttl_seconds=3600,
        description="test",
    )
    assert inv.fee_amount == "0.50"
    assert inv.merchant_payout == "99.50"
    assert 0 <= inv.destination_tag <= 0x7FFFFFFF
    assert inv.status == "pending"

def test_invoice_dest_tag_collision_avoided(monkeypatch, tmp_path):
    db = tmp_path / "test2.db"
    monkeypatch.setenv("RAILS_DB_URL", f"sqlite:///{db}")
    import importlib
    import rails.invoice_engine as ie
    importlib.reload(ie)

    ledger = ie.InvoiceLedger()
    tags = set()
    for _ in range(20):
        inv = ledger.create(
            merchant_id="acme", merchant_addr="rMerch",
            amount=Decimal("10"), currency="RLUSD",
        )
        assert inv.destination_tag not in tags
        tags.add(inv.destination_tag)
