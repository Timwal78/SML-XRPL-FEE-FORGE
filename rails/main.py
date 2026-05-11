"""
RLUSD RAILS — FastAPI application.

Endpoints:
  GET  /                        merchant dashboard
  GET  /widget-demo             demo embed page
  GET  /widget.js               embeddable JS widget
  GET  /api/health              liveness
  POST /api/invoice             create invoice (merchant API)
  GET  /api/invoice/{id}        invoice status (widget polls this)
  GET  /api/invoices            list invoices (dashboard)
  POST /api/expire              run expiration sweep (cron)
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("rails.main")

from rails.invoice_engine import get_invoice_ledger
from rails.payment_watcher import watch_forever
from rails.ai_copywriter import generate_checkout_copy
from shared.alerts import get_rails_channel, make_invoice_alert_fields, COLOR_INFO


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(watch_forever())
    log.info("RAILS started (network=%s)", os.environ.get("XRPL_NETWORK", "testnet"))
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="RLUSD RAILS", lifespan=lifespan)

origins = os.environ.get("RAILS_ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
class InvoiceCreate(BaseModel):
    merchant_id: str
    merchant_addr: str
    amount: float
    currency: str
    description: Optional[str] = None
    ttl_seconds: int = 3600


# -----------------------------------------------------------------------------
# Static routes
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def merchant_dashboard():
    p = Path(__file__).parent / "merchant_dashboard.html"
    return HTMLResponse(p.read_text())


@app.get("/widget-demo", response_class=HTMLResponse)
async def widget_demo():
    p = Path(__file__).parent / "widget-demo.html"
    return HTMLResponse(p.read_text())


@app.get("/widget.js", response_class=PlainTextResponse)
async def widget_js():
    p = Path(__file__).parent / "widget.js"
    return PlainTextResponse(p.read_text(), media_type="application/javascript")


# -----------------------------------------------------------------------------
# API
# -----------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {"ok": True, "engine": "rails", "network": os.environ.get("XRPL_NETWORK", "testnet")}


@app.post("/api/invoice")
async def create_invoice(payload: InvoiceCreate):
    if payload.amount <= 0:
        raise HTTPException(400, "amount must be > 0")
    if payload.currency.upper() not in ("XRP", "RLUSD"):
        raise HTTPException(400, "currency must be XRP or RLUSD")

    ledger = get_invoice_ledger()

    # AI copywriter (superpower) — runs in parallel, non-blocking
    copy_task = asyncio.create_task(
        generate_checkout_copy(
            description=payload.description or "Payment",
            merchant_name=payload.merchant_id,
            amount=str(payload.amount),
            currency=payload.currency.upper(),
        )
    )

    inv = ledger.create(
        merchant_id=payload.merchant_id,
        merchant_addr=payload.merchant_addr,
        amount=Decimal(str(payload.amount)),
        currency=payload.currency.upper(),
        ttl_seconds=payload.ttl_seconds,
        description=payload.description,
    )

    # Wait briefly for AI copy (max 2s); proceed without if slow
    try:
        ai_copy = await asyncio.wait_for(copy_task, timeout=2.0)
    except asyncio.TimeoutError:
        ai_copy = None

    if ai_copy:
        from sqlmodel import Session, select
        with Session(ledger.engine) as s:
            from rails.invoice_engine import Invoice
            stmt = select(Invoice).where(Invoice.invoice_id == inv.invoice_id)
            row = s.exec(stmt).first()
            if row:
                row.ai_headline = ai_copy.get("headline")
                row.ai_blurb = ai_copy.get("blurb")
                s.add(row)
                s.commit()
                inv = row

    operator_addr = os.environ["OPERATOR_WALLET_ADDRESS"]

    # Fire alert
    alerts = get_rails_channel()
    await alerts.send_rich(
        title="🧾 INVOICE CREATED — RLUSD RAILS",
        color=COLOR_INFO,
        fields=make_invoice_alert_fields(
            invoice_id=inv.invoice_id,
            merchant=inv.merchant_id,
            amount=f"{inv.amount} {inv.currency}",
            fee=f"{inv.fee_amount} {inv.currency}",
            net=f"{inv.merchant_payout} {inv.currency}",
        ),
    )

    return {
        "invoice_id": inv.invoice_id,
        "amount": inv.amount,
        "currency": inv.currency,
        "destination": operator_addr,
        "destination_tag": inv.destination_tag,
        "expires_at": inv.expires_at.isoformat(),
        "headline": inv.ai_headline,
        "blurb": inv.ai_blurb,
        "pay_url": f"{os.environ.get('RAILS_PUBLIC_URL', '')}/widget-demo?inv={inv.invoice_id}",
    }


@app.get("/api/invoice/{invoice_id}")
async def invoice_status(invoice_id: str):
    ledger = get_invoice_ledger()
    inv = ledger.get(invoice_id)
    if not inv:
        raise HTTPException(404, "invoice not found")
    return {
        "invoice_id": inv.invoice_id,
        "status": inv.status,
        "amount": inv.amount,
        "currency": inv.currency,
        "destination": os.environ.get("OPERATOR_WALLET_ADDRESS", ""),
        "destination_tag": inv.destination_tag,
        "expires_at": inv.expires_at.isoformat(),
        "headline": inv.ai_headline,
        "blurb": inv.ai_blurb,
        "payment_tx_hash": inv.payment_tx_hash,
        "payout_tx_hash": inv.payout_tx_hash,
    }


@app.get("/api/invoices")
async def list_invoices(limit: int = 100):
    ledger = get_invoice_ledger()
    rows = ledger.recent(limit=limit)
    return [
        {
            "invoice_id": r.invoice_id,
            "created_at": r.created_at.isoformat(),
            "merchant_id": r.merchant_id,
            "amount": r.amount,
            "currency": r.currency,
            "fee_amount": r.fee_amount,
            "merchant_payout": r.merchant_payout,
            "status": r.status,
            "destination_tag": r.destination_tag,
            "tx_hash": r.payment_tx_hash,
            "headline": r.ai_headline,
        }
        for r in rows
    ]


@app.post("/api/expire")
async def expire_due():
    n = get_invoice_ledger().expire_due()
    return {"expired": n}
