"""
SML XRPL FEE FORGE — RLUSD constants and currency math helpers.

VERIFIED against xrpscan.com 2026-05-09:
  Mainnet issuer: rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De
  Testnet issuer: rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV
  Currency hex:   524C555344000000000000000000000000000000

Do NOT modify constants without re-verification.
"""

from __future__ import annotations

import os
from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Literal

# Decimal precision: high enough for any XRPL math
getcontext().prec = 38

NETWORK: Literal["testnet", "mainnet"] = os.environ.get(
    "XRPL_NETWORK", "testnet"
)  # type: ignore

RLUSD_ISSUER_MAINNET = "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De"
RLUSD_ISSUER_TESTNET = "rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV"
RLUSD_CURRENCY_HEX = "524C555344000000000000000000000000000000"

RLUSD_ISSUER = (
    os.environ.get("RLUSD_ISSUER_MAINNET", RLUSD_ISSUER_MAINNET)
    if NETWORK == "mainnet"
    else os.environ.get("RLUSD_ISSUER_TESTNET", RLUSD_ISSUER_TESTNET)
)


# =============================================================================
# Money helper — enforces Decimal math and proper rounding per currency
# =============================================================================

XRP_DECIMALS = 6      # XRP has 6 decimal places (drops)
RLUSD_DECIMALS = 2    # We round RLUSD to cents for human-friendly UX


class Money:
    """
    Currency-safe value object.

    Always use this instead of raw float/int for tip/invoice amounts.
    """

    __slots__ = ("amount", "currency")

    def __init__(self, amount: Decimal | str | int | float, currency: str):
        if isinstance(amount, float):
            # Convert through string to avoid binary-float precision leakage
            amount = Decimal(str(amount))
        elif not isinstance(amount, Decimal):
            amount = Decimal(amount)

        currency = currency.upper()
        if currency not in ("XRP", "RLUSD"):
            raise ValueError(f"Unsupported currency: {currency}")

        decimals = XRP_DECIMALS if currency == "XRP" else RLUSD_DECIMALS
        quant = Decimal(10) ** -decimals
        self.amount: Decimal = amount.quantize(quant, rounding=ROUND_HALF_UP)
        self.currency: str = currency

    def __mul__(self, factor: Decimal | int | float) -> "Money":
        if isinstance(factor, float):
            factor = Decimal(str(factor))
        elif not isinstance(factor, Decimal):
            factor = Decimal(factor)
        return Money(self.amount * factor, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if not isinstance(other, Money) or other.currency != self.currency:
            raise TypeError("Cannot subtract different currencies")
        return Money(self.amount - other.amount, self.currency)

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money) or other.currency != self.currency:
            raise TypeError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

    def __repr__(self) -> str:
        return f"Money({self.amount} {self.currency})"

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"

    def to_dict(self) -> dict:
        return {"amount": str(self.amount), "currency": self.currency}


def split_fee(gross: Money, fee_bps: int) -> tuple[Money, Money]:
    """
    Split a gross amount into (net_to_recipient, fee_to_operator).

    fee_bps is basis points (200 = 2.00%, 50 = 0.50%).
    """
    if fee_bps < 0 or fee_bps > 10_000:
        raise ValueError("fee_bps must be 0..10000")
    fee_factor = Decimal(fee_bps) / Decimal(10_000)
    fee = gross * fee_factor
    net = gross - fee
    return net, fee
