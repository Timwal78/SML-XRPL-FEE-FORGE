# SML XRPL FEE FORGE™

> **Two fee-flywheel engines on the XRP Ledger. Built for solo operators who want to capture transaction fees without running a bank.**

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   ███████ ███    ███ ██          ██   ██ ██████  ██████  ██     ║
║   ██      ████  ████ ██           ██ ██  ██   ██ ██   ██ ██     ║
║   ███████ ██ ████ ██ ██            ███   ██████  ██████  ██     ║
║        ██ ██  ██  ██ ██           ██ ██  ██   ██ ██      ██     ║
║   ███████ ██      ██ ███████     ██   ██ ██   ██ ██      ███████║
║                                                                  ║
║              F E E   F O R G E   ·   v 1 . 0                     ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

## What's in the box

| # | Engine | Function | Fee Capture |
|---|--------|----------|-------------|
| 1 | **TIPHAWK™** | X/Twitter reply-tipping bot for XRP + RLUSD | 2.0% per tip |
| 2 | **RLUSD RAILS™** | Stripe-style checkout button for RLUSD/XRP merchants | 0.5% per invoice |

Both engines share a common XRPL client, alert layer, and ledger persistence. Both ship with real `xrpl-py` integration against mainnet or testnet — **no mocks, no simulated data, no placeholder fees**.

---

## The flywheel

```
   Viral surface (X replies / merchant checkouts)
                    │
                    ▼
         User signs & broadcasts XRPL tx
                    │
                    ▼
         FEE FORGE skims fee → operator wallet
                    │
                    ▼
            Discord alert + ledger row
                    │
                    ▼
   AI digest tweet / merchant dashboard insight
                    │
                    └────► Drives next viral surface
```

Every transaction is a billboard. Every billboard recruits the next user.

---

## Why this exists

XRPL has the lowest transaction fees of any major chain (10 drops ≈ $0.000022) and 3-second finality. The void: **no operator-grade tooling layered on top**. Every Solana memecoin tipping/checkout bot prints fees because the chain has fee throughput. XRPL has the throughput and the institutional rails (RLUSD) — but the bots haven't been built yet.

This kit is the first move.

---

## Quick start (60 seconds)

```bash
# 1. Clone & install
cd SML-XRPL-FEE-FORGE
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure (real testnet wallet generated for you)
cp .env.example .env
python scripts/init_testnet_wallet.py    # writes seeds into .env

# 3. Verify RLUSD trustline
python scripts/verify_rlusd_trustline.py

# 4. Run TIPHAWK
uvicorn tiphawk.main:app --reload --port 8001

# 5. Run RLUSD RAILS (separate terminal)
uvicorn rails.main:app --reload --port 8002
```

Open `http://localhost:8001` for the TipHawk command center, `http://localhost:8002` for the Rails merchant console, and `http://localhost:8002/widget-demo` for the embeddable checkout demo.

---

## Production deploy

Both engines are stateless FastAPI services backed by SQLite (default) or Postgres (set `DATABASE_URL`). Deploy on:

- **Render** (recommended — Timmy already uses it)
- **Fly.io** (low-latency global edge)
- **Railway** (single-click)

`docker-compose.yml` runs both engines + a shared Caddy reverse proxy locally. See `ARCHITECTURE.md` for the full deployment matrix.

---

## File map

```
SML-XRPL-FEE-FORGE/
├── README.md                    ← you are here
├── ARCHITECTURE.md              ← full system architecture + diagrams
├── MANIFESTO.md                 ← build standard compliance audit
├── CLAUDE.md                    ← expert prompt for Claude Code orchestration
├── .env.example                 ← config template (RLUSD addrs prefilled)
├── docker-compose.yml           ← prod deployment
├── requirements.txt             ← pinned deps
├── diagrams/                    ← Mermaid system diagrams
├── shared/                      ← XRPL client, RLUSD constants, alerts
├── tiphawk/                     ← Engine 1: X/Twitter tipping bot
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── main.py                  ← FastAPI app
│   ├── twitter_listener.py      ← X API v2 stream
│   ├── tip_engine.py            ← XRPL payment construction
│   ├── fee_engine.py            ← 2% skim logic
│   ├── ledger.py                ← SQLite persistence
│   ├── ai_digest.py             ← Anthropic API daily-digest (superpower)
│   └── dashboard.html           ← live ops console
├── rails/                       ← Engine 2: RLUSD checkout
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── main.py                  ← FastAPI app
│   ├── invoice_engine.py        ← invoice issuance + destination tags
│   ├── payment_watcher.py       ← XRPL ledger subscription
│   ├── ai_copywriter.py         ← Anthropic API checkout copy gen (superpower)
│   ├── widget.js                ← embeddable JS widget
│   ├── widget-demo.html         ← demo merchant page
│   └── merchant_dashboard.html  ← invoice console
└── scripts/
    ├── setup.sh
    ├── init_testnet_wallet.py
    └── verify_rlusd_trustline.py
```

---

## Brand standard

This package conforms to the **SML Build Manifesto**: real APIs only, real-time self-audit before delivery, every engine ships with its own architecture document, every alert ships in two formats (`alertcondition()`-equivalent webhook + rich JSON Discord payload), and every dashboard hits institutional-grade aesthetic standards. See `MANIFESTO.md` for the full audit.

---

## License

Proprietary — ScriptMasterLabs™. APEX Committee Engine logic is **not present** in this package. Tipping fee math and RLUSD invoice logic are open-derivation. Discord alert formats are SML brand-standard.

---

**Ship the rails. Skim the fees. Let the volume be the marketing.**
