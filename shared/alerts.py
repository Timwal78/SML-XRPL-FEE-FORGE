"""
SML XRPL FEE FORGE — alert system.

Per SML manifesto, every event ships TWO alert formats:
  1. Compact webhook (const-string equivalent) — for generic webhook consumers
  2. Rich Discord embed JSON — for Discord channel display

Both are sent through this module.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

import httpx

XRPSCAN_TX_BASE = "https://xrpscan.com/tx/"


class AlertChannel:
    """
    Wraps a Discord webhook URL with the dual-format SML alert standard.
    """

    def __init__(self, webhook_url: Optional[str] = None, brand: str = "SML XRPL FEE FORGE"):
        self.webhook_url = webhook_url
        self.brand = brand

    async def send_compact(self, message: str) -> bool:
        """Plain-text webhook (const-string equivalent). Returns True on success."""
        if not self.webhook_url:
            return False
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                r = await client.post(
                    self.webhook_url,
                    json={"content": f"`[{self.brand}]` {message}"},
                )
                return r.status_code in (200, 204)
            except httpx.HTTPError:
                return False

    async def send_rich(
        self,
        title: str,
        color: int,
        fields: list[dict],
        tx_hash: Optional[str] = None,
    ) -> bool:
        """Rich Discord embed. Returns True on success."""
        if not self.webhook_url:
            return False

        embed = {
            "title": title,
            "color": color,
            "fields": fields,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": self.brand},
        }
        if tx_hash:
            embed["fields"] = list(embed["fields"]) + [
                {
                    "name": "TX",
                    "value": f"[xrpscan]({XRPSCAN_TX_BASE}{tx_hash})",
                    "inline": False,
                }
            ]

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                r = await client.post(self.webhook_url, json={"embeds": [embed]})
                return r.status_code in (200, 204)
            except httpx.HTTPError:
                return False


# Color palette
COLOR_SUCCESS = 0x3FB950   # green
COLOR_INFO = 0x58A6FF      # blue
COLOR_WARN = 0xFFA657      # orange
COLOR_ERROR = 0xF85149     # red
COLOR_FEE = 0xFFD700       # gold


# -----------------------------------------------------------------------------
# Pre-built alerts
# -----------------------------------------------------------------------------

def make_tip_alert_fields(
    sender: str,
    recipient: str,
    gross: str,
    fee: str,
    net: str,
) -> list[dict]:
    return [
        {"name": "From", "value": sender, "inline": True},
        {"name": "To", "value": recipient, "inline": True},
        {"name": "​", "value": "​", "inline": True},  # spacer
        {"name": "Gross", "value": gross, "inline": True},
        {"name": "Fee (2%)", "value": fee, "inline": True},
        {"name": "Net", "value": net, "inline": True},
    ]


def make_invoice_alert_fields(
    invoice_id: str,
    merchant: str,
    amount: str,
    fee: str,
    net: str,
    customer_addr: Optional[str] = None,
) -> list[dict]:
    fields = [
        {"name": "Invoice", "value": f"`{invoice_id}`", "inline": False},
        {"name": "Merchant", "value": merchant, "inline": True},
        {"name": "Amount", "value": amount, "inline": True},
        {"name": "​", "value": "​", "inline": True},
        {"name": "Fee (0.5%)", "value": fee, "inline": True},
        {"name": "Merchant payout", "value": net, "inline": True},
    ]
    if customer_addr:
        fields.append({"name": "Customer", "value": f"`{customer_addr}`", "inline": False})
    return fields


def get_tiphawk_channel() -> AlertChannel:
    return AlertChannel(
        os.environ.get("DISCORD_WEBHOOK_TIPHAWK"),
        brand="TIPHAWK • SML",
    )


def get_rails_channel() -> AlertChannel:
    return AlertChannel(
        os.environ.get("DISCORD_WEBHOOK_RAILS"),
        brand="RLUSD RAILS • SML",
    )


def make_mirror_alert_fields(
    leader: str,
    follower: str,
    pair: str,
    side: str,
    amount: str,
) -> list[dict]:
    return [
        {"name": "Leader", "value": f"`{leader}`", "inline": False},
        {"name": "Follower", "value": f"`{follower}`", "inline": False},
        {"name": "Pair", "value": pair, "inline": True},
        {"name": "Side", "value": side.upper(), "inline": True},
        {"name": "Amount", "value": f"{amount} XRP", "inline": True},
    ]


def make_launchpad_alert_fields(
    token: str,
    symbol: str,
    action: str,
    amount: str,
    price: str,
) -> list[dict]:
    return [
        {"name": "Token", "value": f"{token} ({symbol})", "inline": False},
        {"name": "Action", "value": action.upper(), "inline": True},
        {"name": "Amount", "value": amount, "inline": True},
        {"name": "Price", "value": f"{price} XRP", "inline": True},
    ]


def get_copytrader_channel() -> AlertChannel:
    return AlertChannel(
        os.environ.get("DISCORD_WEBHOOK_COPYTRADER"),
        brand="COPY-TRADER • SML",
    )


def get_launchpad_channel() -> AlertChannel:
    return AlertChannel(
        os.environ.get("DISCORD_WEBHOOK_LAUNCHPAD"),
        brand="MEME-LAUNCH • SML",
    )
