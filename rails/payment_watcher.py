"""
RLUSD RAILS — payment watcher.

Subscribes to the operator hot wallet via XRPL WebSocket and dispatches
incoming payments to the invoice ledger by destination tag.

When a payment matches an active invoice:
  1. Mark invoice paid
  2. Forward `merchant_payout` to merchant_addr (single Payment tx)
  3. Operator retains `fee_amount` automatically
  4. Fire Discord alert (compact + rich)
"""

from __future__ import annotations

import asyncio
import logging
import os
from decimal import Decimal
from typing import Optional

from xrpl.models.requests import Subscribe, StreamParameter
from xrpl.wallet import Wallet

from shared.xrpl_client import get_client
from shared.rlusd import Money, RLUSD_CURRENCY_HEX, RLUSD_ISSUER
from shared.alerts import (
    get_rails_channel,
    make_invoice_alert_fields,
    COLOR_SUCCESS,
    COLOR_ERROR,
)
from rails.invoice_engine import get_invoice_ledger

log = logging.getLogger("rails.watcher")


def _extract_amount(amount_field) -> tuple[Decimal, str]:
    """
    XRPL Amount can be a drops string (XRP) or {currency, issuer, value} (token).
    Returns (Decimal, currency_label).
    """
    if isinstance(amount_field, str):
        return Decimal(amount_field) / Decimal(1_000_000), "XRP"
    if isinstance(amount_field, dict):
        cur = amount_field.get("currency", "")
        iss = amount_field.get("issuer", "")
        val = Decimal(amount_field.get("value", "0"))
        if cur == RLUSD_CURRENCY_HEX and iss == RLUSD_ISSUER:
            return val, "RLUSD"
        return val, cur
    return Decimal(0), "?"


async def handle_payment_tx(tx: dict) -> None:
    """Dispatched on every Payment landing on the operator wallet."""
    operator_addr = os.environ["OPERATOR_WALLET_ADDRESS"]
    payment = tx.get("transaction", tx)
    if payment.get("TransactionType") != "Payment":
        return
    if payment.get("Destination") != operator_addr:
        return

    dest_tag = payment.get("DestinationTag")
    if dest_tag is None:
        log.info("payment to operator without destination tag — ignoring")
        return

    ledger = get_invoice_ledger()
    invoice = ledger.get_by_tag(int(dest_tag))
    if not invoice:
        log.info("no active invoice for dest_tag=%s", dest_tag)
        return

    delivered = payment.get("DeliveredAmount", payment.get("Amount"))
    paid_amt, paid_cur = _extract_amount(delivered)
    expected_amt = Decimal(invoice.amount)

    if paid_cur != invoice.currency or paid_amt < expected_amt:
        log.warning(
            "underpayment for invoice %s: paid=%s %s, expected=%s %s",
            invoice.invoice_id, paid_amt, paid_cur, expected_amt, invoice.currency,
        )
        await get_rails_channel().send_compact(
            f"UNDERPAYMENT inv={invoice.invoice_id} "
            f"got={paid_amt} {paid_cur} need={expected_amt} {invoice.currency}"
        )
        return

    customer_addr = payment.get("Account", "")
    payment_hash = tx.get("hash") or payment.get("hash", "")

    # Forward merchant_payout to merchant
    operator_seed = os.environ["OPERATOR_WALLET_SEED"]
    op_wallet = Wallet.from_seed(operator_seed)
    client = get_client()
    payout_amount = Money(Decimal(invoice.merchant_payout), invoice.currency)

    try:
        if invoice.currency == "XRP":
            res = await client.send_xrp(
                op_wallet,
                invoice.merchant_addr,
                payout_amount.amount,
                memo=f"inv:{invoice.invoice_id}",
            )
        else:
            res = await client.send_rlusd(
                op_wallet, invoice.merchant_addr, payout_amount.amount
            )
        payout_hash = res.get("hash") or res.get("tx_json", {}).get("hash", "")

        ledger.mark_paid(
            invoice.invoice_id,
            customer_addr=customer_addr,
            payment_tx_hash=payment_hash,
            payout_tx_hash=payout_hash,
        )

        alerts = get_rails_channel()
        await alerts.send_rich(
            title="✅ INVOICE PAID — RLUSD RAILS",
            color=COLOR_SUCCESS,
            fields=make_invoice_alert_fields(
                invoice_id=invoice.invoice_id,
                merchant=invoice.merchant_id,
                amount=f"{invoice.amount} {invoice.currency}",
                fee=f"{invoice.fee_amount} {invoice.currency}",
                net=f"{invoice.merchant_payout} {invoice.currency}",
                customer_addr=customer_addr,
            ),
            tx_hash=payout_hash,
        )
        await alerts.send_compact(
            f"PAID inv={invoice.invoice_id} {invoice.amount} {invoice.currency} "
            f"merchant={invoice.merchant_id} fee={invoice.fee_amount}"
        )
        log.info("invoice %s paid + forwarded", invoice.invoice_id)
    except Exception as e:
        log.exception("payout failed for invoice %s", invoice.invoice_id)
        await get_rails_channel().send_rich(
            title="🔥 PAYOUT FAILED — RLUSD RAILS",
            color=COLOR_ERROR,
            fields=[
                {"name": "Invoice", "value": invoice.invoice_id, "inline": True},
                {"name": "Error", "value": repr(e)[:1000], "inline": False},
            ],
        )


async def watch_forever() -> None:
    """Persistent WebSocket subscribe loop. Reconnects on drop."""
    operator_addr = os.environ["OPERATOR_WALLET_ADDRESS"]
    client = get_client()

    while True:
        try:
            async with client.ws_client() as ws:
                await ws.send(
                    Subscribe(
                        accounts=[operator_addr],
                        streams=[StreamParameter.TRANSACTIONS],
                    )
                )
                log.info("RAILS watcher subscribed to %s", operator_addr)
                async for msg in ws:
                    if msg.get("type") == "transaction":
                        if msg.get("validated"):
                            await handle_payment_tx(msg)
        except Exception as e:
            log.warning("watcher disconnected (%s) — reconnecting in 3s", e)
            await asyncio.sleep(3)
