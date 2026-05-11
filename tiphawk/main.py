"""
TIPHAWK — FastAPI application.

Endpoints:
  GET  /              dashboard
  GET  /api/health    liveness
  GET  /api/stats     aggregate stats
  GET  /api/recent    recent tips
  POST /api/manual    manual tip injection (admin debug)
  POST /api/digest    trigger digest (admin)
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("tiphawk.main")

from tiphawk.ledger import get_ledger
from tiphawk.tip_engine import TipCommand, execute_tip
from tiphawk.ai_digest import run_daily_digest
from tiphawk.twitter_listener import start_stream_in_background


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    listener = start_stream_in_background(loop)
    app.state.listener = listener
    log.info("TIPHAWK started (network=%s)", os.environ.get("XRPL_NETWORK", "testnet"))
    yield
    if listener:
        try:
            listener.disconnect()
        except Exception:
            pass


app = FastAPI(title="TIPHAWK", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html_path = Path(__file__).parent / "dashboard.html"
    return HTMLResponse(html_path.read_text())


@app.get("/api/health")
async def health():
    return {"ok": True, "engine": "tiphawk", "network": os.environ.get("XRPL_NETWORK", "testnet")}


@app.get("/api/stats")
async def stats():
    ledger = get_ledger()
    rows = ledger.recent(limit=10000)
    sent = [r for r in rows if r.status == "sent"]
    failed = [r for r in rows if r.status == "failed"]

    fee_xrp = Decimal(0)
    fee_rlusd = Decimal(0)
    vol_xrp = Decimal(0)
    vol_rlusd = Decimal(0)
    for r in sent:
        if r.currency == "XRP":
            fee_xrp += Decimal(r.fee_amount)
            vol_xrp += Decimal(r.gross_amount)
        else:
            fee_rlusd += Decimal(r.fee_amount)
            vol_rlusd += Decimal(r.gross_amount)

    return {
        "total_tips": len(sent),
        "failed_tips": len(failed),
        "volume_xrp": str(vol_xrp),
        "volume_rlusd": str(vol_rlusd),
        "fees_collected_xrp": str(fee_xrp),
        "fees_collected_rlusd": str(fee_rlusd),
    }


@app.get("/api/recent")
async def recent(limit: int = 50):
    ledger = get_ledger()
    rows = ledger.recent(limit=limit)
    return [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat(),
            "sender": r.sender_handle,
            "recipient": r.recipient_handle,
            "currency": r.currency,
            "gross": r.gross_amount,
            "fee": r.fee_amount,
            "net": r.net_amount,
            "status": r.status,
            "tx_hash": r.tx_hash,
        }
        for r in rows
    ]


@app.post("/api/manual")
async def manual_tip(
    sender_handle: str,
    recipient_handle: str,
    amount: float,
    currency: str,
    tweet_id: str = "manual",
    x_admin_token: str = Header(default=""),
):
    """Manual tip injection — for debugging only."""
    expected = os.environ.get("TIPHAWK_ADMIN_TOKEN", "")
    if not expected or x_admin_token != expected:
        raise HTTPException(401, "admin token required")

    cmd = TipCommand(
        bot=os.environ.get("TIPHAWK_BOT_HANDLE", "tiphawk_bot"),
        sender_handle=sender_handle,
        recipient_handle=recipient_handle,
        amount=Decimal(str(amount)),
        currency=currency.upper(),
        tweet_id=tweet_id,
        tweet_text=f"[manual injection by admin]",
    )
    result = await execute_tip(cmd)
    return result


@app.post("/api/digest")
async def trigger_digest(x_admin_token: str = Header(default="")):
    expected = os.environ.get("TIPHAWK_ADMIN_TOKEN", "")
    if not expected or x_admin_token != expected:
        raise HTTPException(401, "admin token required")
    digest = await run_daily_digest()
    return digest or {"ok": True, "note": "no tips yesterday"}
