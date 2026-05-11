"""TIPHAWK unit tests — pure logic, no network."""

from decimal import Decimal
import pytest

from shared.rlusd import Money, split_fee
from tiphawk.fee_engine import calc_tip_split
from tiphawk.tip_engine import parse_tip, TIP_RE


# -----------------------------------------------------------------------------
# Money
# -----------------------------------------------------------------------------
def test_money_xrp_quantizes_to_6dp():
    m = Money("5.123456789", "XRP")
    assert m.amount == Decimal("5.123457")  # rounded HALF_UP

def test_money_rlusd_quantizes_to_2dp():
    m = Money("10.555", "RLUSD")
    assert m.amount == Decimal("10.56")

def test_money_rejects_unknown_currency():
    with pytest.raises(ValueError):
        Money(1, "USDT")

def test_money_arithmetic():
    a = Money("10.00", "RLUSD")
    b = Money("0.20", "RLUSD")
    assert (a - b).amount == Decimal("9.80")
    assert (a + b).amount == Decimal("10.20")
    assert (a * Decimal("0.5")).amount == Decimal("5.00")

def test_money_cross_currency_arithmetic_fails():
    a = Money("10", "XRP")
    b = Money("10", "RLUSD")
    with pytest.raises(TypeError):
        a + b


# -----------------------------------------------------------------------------
# Fee math
# -----------------------------------------------------------------------------
def test_split_fee_2pct():
    gross = Money("10.00", "RLUSD")
    net, fee = split_fee(gross, 200)
    assert fee.amount == Decimal("0.20")
    assert net.amount == Decimal("9.80")

def test_split_fee_zero():
    gross = Money("100", "XRP")
    net, fee = split_fee(gross, 0)
    assert fee.amount == Decimal("0.000000")
    assert net.amount == Decimal("100.000000")

def test_calc_tip_split_uses_env(monkeypatch):
    monkeypatch.setenv("TIPHAWK_FEE_BPS", "150")
    gross = Money("100", "RLUSD")
    net, fee = calc_tip_split(gross)
    assert fee.amount == Decimal("1.50")
    assert net.amount == Decimal("98.50")


# -----------------------------------------------------------------------------
# Tip parsing
# -----------------------------------------------------------------------------
def test_parse_xrp_tip():
    cmd = parse_tip("@tiphawk_bot tip @sam 5 XRP", "alice", "tweet123")
    assert cmd is not None
    assert cmd.recipient_handle == "sam"
    assert cmd.amount == Decimal("5")
    assert cmd.currency == "XRP"

def test_parse_rlusd_tip():
    cmd = parse_tip("@tiphawk_bot tip @sam 10.50 RLUSD", "alice", "tweet123")
    assert cmd is not None
    assert cmd.amount == Decimal("10.50")
    assert cmd.currency == "RLUSD"

def test_parse_case_insensitive():
    cmd = parse_tip("@TipHawk_Bot TIP @sam 5 xrp", "alice", "t1")
    assert cmd is not None
    assert cmd.currency == "XRP"

def test_parse_rejects_garbage():
    assert parse_tip("just a normal tweet", "alice", "t1") is None
    assert parse_tip("@tiphawk_bot please tip me", "alice", "t1") is None
    assert parse_tip("@tiphawk_bot tip @sam free XRP", "alice", "t1") is None
