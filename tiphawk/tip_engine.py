"""
TIPHAWK — tip engine.

Orchestrates: parse tip command → resolve XRPL addrs → split fee →
construct two payments (net to recipient, fee to operator) → submit → ledger.
"""

from __future__ import annotations

import os
import re
import asyncio
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from xrpl.wallet import Wallet

from shared.xrpl_client import get_client, TrustlineMissingError
from shared.rlusd import Money
from shared.alerts import (
    get_tiphawk_channel,
    make_tip_alert_fields,
    fire_payment_alert,
    COLOR_FEE,
    COLOR_ERROR,
)
from tiphawk.fee_engine import calc_tip_split
from tiphawk.ledger import get_ledger


# Tip command grammar:
#   "@tiphawk_bot tip @recipient 5 XRP"
#   "@tiphawk_bot tip @recipient 10.50 RLUSD"
TIP_RE = re.compile(
    r"@(?P<bot>\w+)\s+tip\s+@(?P<recipient>\w+)\s+"
    r"(?P<amount>\d+(?:\.\d+)?)\s+(?P<currency>XRP|RLUSD)",
    re.IGNORECASE,
)


@dataclass
class TipCommand:
    bot: str
    sender_handle: str
    recipient_handle: str
    amount: Decimal
    currency: str  # XRP or RLUSD
    tweet_id: str
    tweet_text: str


def parse_tip(text: str, sender_handle: str, tweet_id: str) -> Optional[TipCommand]:
    m = TIP_RE.search(text)
    if not m:
        return None
    return TipCommand(
        bot=m.group("bot"),
        sender_handle=sender_handle,
        recipient_handle=m.group("recipient"),
        amount=Decimal(m.group("amount")),
        currency=m.group("currency").upper(),
        tweet_id=tweet_id,
        tweet_text=text,
    )


# -----------------------------------------------------------------------------
# Handle → XRPL address resolution
# -----------------------------------------------------------------------------
# In production this would query a `handle_registry` table where users register
# their X handle ↔ XRPL address. For the MVP we use an env-loaded registry.

def _load_registry() -> dict[str, str]:
    """
    Loads handle→address mappings from TIPHAWK_REGISTRY env var.
    Format: handle1:rAddress1,handle2:rAddress2
    """
    raw = os.environ.get("TIPHAWK_REGISTRY", "")
    out = {}
    for entry in raw.split(","):
        if ":" in entry:
            h, a = entry.split(":", 1)
            out[h.strip().lower().lstrip("@")] = a.strip()
    return out


def resolve_address(handle: str) -> Optional[str]:
    return _load_registry().get(handle.lower().lstrip("@"))


# -----------------------------------------------------------------------------
# Tip execution
# -----------------------------------------------------------------------------
async def execute_tip(cmd: TipCommand) -> dict:
    """
    Executes a parsed tip. Returns dict with status, tx_hash, error.
    """
    ledger = get_ledger()
    alerts = get_tiphawk_channel()
    client = get_client()

    sender_addr = resolve_address(cmd.sender_handle)
    recipient_addr = resolve_address(cmd.recipient_handle)

    if not sender_addr or not recipient_addr:
        record = ledger.record(
            tweet_id=cmd.tweet_id,
            sender_handle=cmd.sender_handle,
            recipient_handle=cmd.recipient_handle,
            tweet_text=cmd.tweet_text,
            sender_addr=sender_addr or "",
            recipient_addr=recipient_addr or "",
            currency=cmd.currency,
            gross_amount=str(cmd.amount),
            fee_amount="0",
            net_amount="0",
            status="failed",
            error="unregistered_handle",
        )
        await alerts.send_compact(
            f"TIP FAILED — unregistered handle "
            f"({cmd.sender_handle}→{cmd.recipient_handle})"
        )
        return {"status": "failed", "error": "unregistered_handle", "id": record.id}

    gross = Money(cmd.amount, cmd.currency)
    net, fee = calc_tip_split(gross)

    # Fee wallet defaults to operator wallet
    operator_seed = os.environ["OPERATOR_WALLET_SEED"]
    operator_wallet = Wallet.from_seed(operator_seed)
    fee_wallet_addr = os.environ.get("FEE_WALLET_ADDRESS", operator_wallet.address)

    record = ledger.record(
        tweet_id=cmd.tweet_id,
        sender_handle=cmd.sender_handle,
        recipient_handle=cmd.recipient_handle,
        tweet_text=cmd.tweet_text,
        sender_addr=sender_addr,
        recipient_addr=recipient_addr,
        currency=cmd.currency,
        gross_amount=str(gross.amount),
        fee_amount=str(fee.amount),
        net_amount=str(net.amount),
        status="pending",
    )

    # NOTE on tipping model:
    # The tipping model assumes the operator wallet is funded by the sender
    # via a deposit address (or the bot is operating its own balance for
    # the sender as a custodial account). In a fully non-custodial flow,
    # the bot would only generate a signing link. We implement the
    # custodial flavor here for v1; a non-custodial flow is on the roadmap.

    try:
        if cmd.currency == "XRP":
            res = await client.send_xrp(
                operator_wallet, recipient_addr, net.amount
            )
        else:
            res = await client.send_rlusd(
                operator_wallet, recipient_addr, net.amount
            )

        tx_hash = res.get("hash") or res.get("tx_json", {}).get("hash", "")
        ledger.update_status(record.id, "sent", tx_hash=tx_hash)

        asyncio.create_task(fire_payment_alert(
            wallet=sender_addr,
            product="TipMaster",
            endpoint=f"tip @{cmd.sender_handle}→@{cmd.recipient_handle}",
            amount=str(gross),
        ))

        await alerts.send_rich(
            title="💰 TIP EXECUTED — TIPHAWK",
            color=COLOR_FEE,
            fields=make_tip_alert_fields(
                sender=f"@{cmd.sender_handle}",
                recipient=f"@{cmd.recipient_handle}",
                gross=str(gross),
                fee=str(fee),
                net=str(net),
            ),
            tx_hash=tx_hash,
        )
        await alerts.send_compact(
            f"TIP {cmd.sender_handle}→{cmd.recipient_handle} "
            f"{net} (fee {fee}) tx={tx_hash[:12]}…"
        )

        return {"status": "sent", "tx_hash": tx_hash, "id": record.id}

    except TrustlineMissingError as e:
        ledger.update_status(record.id, "failed", error=str(e))
        await alerts.send_rich(
            title="⚠️ TIP FAILED — TRUSTLINE MISSING",
            color=COLOR_ERROR,
            fields=[
                {"name": "Error", "value": str(e), "inline": False},
                {"name": "From", "value": f"@{cmd.sender_handle}", "inline": True},
                {"name": "To", "value": f"@{cmd.recipient_handle}", "inline": True},
            ],
        )
        return {"status": "failed", "error": str(e), "id": record.id}

    except Exception as e:
        ledger.update_status(record.id, "failed", error=repr(e))
        await alerts.send_rich(
            title="🔥 TIP FAILED — XRPL ERROR",
            color=COLOR_ERROR,
            fields=[
                {"name": "Error", "value": repr(e)[:1000], "inline": False},
                {"name": "From", "value": f"@{cmd.sender_handle}", "inline": True},
                {"name": "To", "value": f"@{cmd.recipient_handle}", "inline": True},
            ],
        )
        return {"status": "failed", "error": repr(e), "id": record.id}
