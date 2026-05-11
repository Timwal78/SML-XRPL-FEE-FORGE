"""
RLUSD RAILS — fee engine.

Computes the operator skim on every invoice. 0.5% = 50 bps default.
"""

from __future__ import annotations

import os

from shared.rlusd import Money, split_fee


def get_fee_bps() -> int:
    return int(os.environ.get("RAILS_FEE_BPS", "50"))


def calc_invoice_split(gross: Money) -> tuple[Money, Money]:
    """
    Returns (merchant_payout, operator_fee).

    Example: 100.00 RLUSD invoice @ 50 bps → (99.50, 0.50)
    """
    return split_fee(gross, get_fee_bps())
