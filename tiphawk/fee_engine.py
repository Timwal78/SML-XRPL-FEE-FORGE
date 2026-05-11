"""
TIPHAWK — fee engine.

Computes the operator skim on every tip. Uses Decimal math, never floats.
"""

from __future__ import annotations

import os

from shared.rlusd import Money, split_fee


def get_fee_bps() -> int:
    return int(os.environ.get("TIPHAWK_FEE_BPS", "200"))


def calc_tip_split(gross: Money) -> tuple[Money, Money]:
    """
    Returns (net_to_recipient, fee_to_operator).

    Example: 10.00 RLUSD gross @ 200 bps → (9.80, 0.20)
    """
    return split_fee(gross, get_fee_bps())
