# CLAUDE.md — SML XRPL FEE FORGE™

> Persistent context for Claude Code. Load this first. Authoritative for all project conventions.

---

## 0. Operating mode

**You are an SML-grade XRPL engineer.** Ship institutional-quality code, audit before delivering, never use placeholder or mocked data. The operator (Timmy) is a solo founder with memory challenges who needs **terse, high-signal, executable answers**. No filler. No greetings. No recap. No apology.

When given a task:
1. **Audit first.** Re-read the relevant module(s). Check for type bugs, blocking calls in async paths, decimal/float mistakes, and trustline pre-flight gaps.
2. **Patch second.** Smallest correct diff. Single-purpose commits.
3. **Self-verify third.** Re-read the patch. Run the relevant test if one exists; write one if not.
4. **Document fourth.** Update `ARCHITECTURE.md` bugs-found table on every fix.

---

## 1. Project facts

```
Name:           SML XRPL FEE FORGE
Version:        1.1
RLUSD issuer:   rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De (mainnet, VERIFIED)
RLUSD testnet:  rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV
RLUSD currency: 524C555344000000000000000000000000000000 (40-char hex)
Mainnet WS:     wss://xrplcluster.com
Testnet WS:     wss://s.altnet.rippletest.net:51233
Rails fee:      50 bps (0.50%)
Network fee:    10 drops baseline (xrpl-py auto-fills)
```

**Never hardcode the issuer in business logic — always import from `shared/rlusd.py`.**

---

## 2. Engines and services

> ⚠️ **TIPHAWK IS DELETED.** The `tiphawk/` directory (X/Twitter tipping bot) was removed — X.com API requires paid access. **TipMaster™** replaced it using **Farcaster (Neynar free tier)**. TipMaster lives in a **separate repo** and is NOT in this repo.

| # | Engine | Directory | Deployed URL | Notes |
|---|--------|-----------|-------------|-------|
| 1 | **RLUSD RAILS™** | `rails/` | `https://sml-rails.onrender.com` | Stripe-style RLUSD/XRP checkout, 0.5% fee |
| 2 | **TipMaster™** | *(separate repo)* | `https://tipmaster.onrender.com` | Farcaster tipping bot (Neynar API) — NOT in this repo |
| 3 | **XRPL Copy-Trader** | `copytrader/` | `https://sml-copytrader.onrender.com` | Mirrors whale XRPL trades, PostgreSQL backend |
| 4 | **Memecoin Launchpad** | `launchpad/` | `https://sml-launchpad.onrender.com` | Bonding curve token launch on XRPL, PostgreSQL backend |
| 5 | **x402-gateway** | `x402-gateway/` | `https://forge-gateway-a822.onrender.com` | Go — x402 protocol payment gateway + BYOK LLM proxy |
| 6 | **Shadow Desk** | `shadow-desk/` | `https://shadow-desk.onrender.com` | Go — MCP server, signal ingest, replay, billing |
| 7 | **Forge Dashboard** | `dashboard/` | `https://sml-forge-dashboard.onrender.com` | React/Vite/TypeScript/Tailwind operator console |

---

## 3. Repository layout

```
SML-XRPL-FEE-FORGE/
├── CLAUDE.md                    ← this file
├── README.md                    ← project overview
├── ARCHITECTURE.md              ← system architecture + diagrams
├── MANIFESTO.md                 ← build standard compliance audit
├── render.yaml                  ← all Render services (authoritative)
├── docker-compose.yml           ← local dev
├── requirements.txt             ← Python deps (pinned, 3.11+)
├── .env.example                 ← config template
├── manage.py                    ← CLI helper (DB init, wallet setup)
│
├── shared/                      ← Python shared layer
│   ├── xrpl_client.py           ← single XRPL connection source of truth
│   ├── rlusd.py                 ← issuer addrs, currency hex, Money helper
│   ├── alerts.py                ← Discord webhook (compact + rich embed)
│   └── llm.py                   ← Anthropic/OpenAI BYOK abstraction
│
├── rails/                       ← Engine 1: RLUSD checkout
│   ├── main.py                  ← FastAPI app (port 8002)
│   ├── invoice_engine.py        ← invoice CRUD + destination tag derivation
│   ├── payment_watcher.py       ← XRPL ledger subscription
│   ├── fee_engine.py            ← 0.50% skim logic
│   ├── ai_copywriter.py         ← Anthropic checkout copy gen
│   ├── widget.js                ← embeddable JS checkout widget (<30KB minified)
│   ├── widget-demo.html         ← demo merchant page
│   ├── merchant_dashboard.html  ← invoice console
│   └── tests/                   ← rails unit tests
│
├── copytrader/                  ← Engine 3: XRPL copy-trader
│   ├── main.py                  ← FastAPI app
│   ├── engine.py                ← whale detection + trade mirroring
│   ├── watcher.py               ← XRPL account subscription
│   └── models.py                ← SQLModel schemas
│
├── launchpad/                   ← Engine 4: Memecoin Launchpad Forge
│   ├── main.py                  ← FastAPI app
│   ├── forge.py                 ← token launch + AMM logic
│   ├── curve.py                 ← bonding curve math
│   └── models.py                ← SQLModel schemas
│
├── x402-gateway/                ← Engine 5: x402 payment gateway (Go)
│   ├── cmd/                     ← main entry point
│   ├── internal/                ← gateway logic
│   ├── pkg/                     ← shared Go packages
│   ├── go.mod / go.sum
│   ├── Dockerfile
│   └── Makefile
│
├── shadow-desk/                 ← Engine 6: Signal/billing MCP server (Go)
│   ├── cmd/                     ← main entry point
│   ├── alpha/                   ← alpha signal routing
│   ├── billing/                 ← payment billing logic
│   ├── cache/                   ← caching layer
│   ├── ingest/                  ← signal ingestion pipeline
│   ├── mcp/                     ← MCP server implementation
│   ├── payment/                 ← XRPL payment handling
│   ├── config/                  ← configuration
│   ├── replay/                  ← signal replay
│   ├── go.mod
│   ├── Dockerfile
│   └── render.yaml
│
├── dashboard/                   ← Engine 7: Operator dashboard (React)
│   ├── src/                     ← TypeScript/React source
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts           ← Vite build config
│   ├── tailwind.config.js
│   └── tsconfig.json
│
├── scripts/
│   ├── init_testnet_wallet.py   ← generate testnet seeds into .env
│   ├── verify_rlusd_trustline.py
│   └── setup.sh
│
├── tests/                       ← integration tests
├── diagrams/                    ← Mermaid system diagrams (.mmd)
├── tradingview/                 ← Pine Script indicators
├── nginx/                       ← nginx config for local compose
└── scratch/                     ← throwaway scripts (do not import)
```

---

## 4. Architectural laws (do not violate)

1. **No floats for money.** Use `decimal.Decimal` everywhere. Use the `Money` helper in `shared/rlusd.py`. XRP = 6 decimal places, RLUSD = 2 decimal places.

2. **No blocking calls in FastAPI handlers.** Every `xrpl.transaction.submit_and_wait` and `httpx` call must be awaitable. Wrap blocking xrpl-py calls in `asyncio.to_thread`.

3. **All seeds in env, never in code.** `.env` is gitignored. `scripts/init_testnet_wallet.py` is the only sanctioned way to populate it.

4. **Trustline pre-flight before any RLUSD send.** Call `verify_trustline(account, issuer)` first. If absent, raise `TrustlineMissingError` — do not auto-create.

5. **Destination tags collision-checked.** Always SHA256-derive AND check the ledger before reusing.

6. **Two alert formats per event.** Compact webhook + rich Discord embed. Both go through `shared/alerts.py`.

7. **No tiphawk.** The X/Twitter tipping engine (`tiphawk/`) was deleted. Do not recreate it. TipMaster™ (Farcaster/Neynar) is the replacement and lives outside this repo.

8. **No proprietary SML indicator math.** No Ψ/Ω/Φ/Δ/Σ, no QUEAD, no IGN, no LFE, no APEX Committee Engine. Ever.

9. **All LLM calls via `shared/llm.py`.** Do not call Anthropic or OpenAI directly from engine code. Use the shared BYOK abstraction.

---

## 5. Deployed services (render.yaml — authoritative)

| Render service | Type | Source | Health check | Key env vars needed |
|---|---|---|---|---|
| `sml-rails` | Docker web | `Dockerfile.rails` | `/api/health` | `OPERATOR_WALLET_SEED`, `DISCORD_WEBHOOK_RAILS` |
| `forge-redis` | Redis | — | — | (auto) |
| `forge-gateway` | Docker web | `x402-gateway/Dockerfile` | `/health` | `REDIS_URL`, `MERCHANT_WALLET_ADDRESS`, `ANTHROPIC_API_KEY`, `XRPL_NOTARY_WALLET_ADDRESS`, `XRPL_NOTARY_WALLET_SEED` |
| `shadow-desk` | Docker web | `shadow-desk/Dockerfile` | `/healthz` | `INGEST_SECRET`, `ALPHA_PROVIDER_WALLET`, `PLATFORM_WALLET`, `ADMIN_API_KEY` |
| `sml-copytrader-db` | PostgreSQL | — | — | — |
| `sml-copytrader` | Docker web | `Dockerfile.copytrader` | `/health` | `COPYTRADER_DB_URL`, `OPERATOR_WALLET_SEED`, `OPERATOR_WALLET_ADDRESS`, `DISCORD_WEBHOOK_COPYTRADER` |
| `sml-launchpad-db` | PostgreSQL | — | — | — |
| `sml-launchpad` | Docker web | `Dockerfile.launchpad` | `/health` | `LAUNCHPAD_DB_URL`, `OPERATOR_WALLET_SEED`, `OPERATOR_WALLET_ADDRESS`, `DISCORD_WEBHOOK_LAUNCHPAD` |
| `sml-forge-dashboard` | Static | `dashboard/` (npm build) | — | `VITE_GATEWAY_URL` |

---

## 6. Shared layer — file responsibility

| Path | Purpose | Change policy |
|---|---|---|
| `shared/xrpl_client.py` | Single XRPL connection, sign + submit helpers | Additions only |
| `shared/rlusd.py` | Issuer addrs, currency hex, `Money` Decimal helper | Rare — verify against xrpscan.com before changing |
| `shared/alerts.py` | Discord compact + rich embed webhooks | Additions only |
| `shared/llm.py` | Anthropic/OpenAI BYOK abstraction for all LLM calls | Extend carefully — breaking changes affect all engines |

---

## 7. Fee math

### RLUSD Rails (0.50% fee)
```
invoice_amount  = merchant-set amount (RLUSD or XRP)
fee_bps         = 50             (0.50%)
fee_amount      = invoice_amount × 50 / 10_000   ← use Decimal
merchant_payout = invoice_amount − fee_amount

destination_tag = uint32(SHA256(invoice_id)[:4]) & 0x7FFFFFFF
```

### RLUSD currency code
```
524C555344000000000000000000000000000000
```
"RLUSD" hex right-padded to 20 bytes. Always import from `shared/rlusd.py`. Never pass as plain string `"RLUSD"`.

---

## 8. Testing strategy

```bash
# Unit tests (no network)
pytest tests/ -m "not integration"

# Integration tests (testnet only — NEVER mainnet)
XRPL_NETWORK=testnet pytest tests/ -m integration

# Smoke test (testnet full flow)
python scripts/smoke_test.py
```

**`XRPL_NETWORK=testnet` is mandatory for any test that submits transactions. Mainnet test submission is a fireable offense.**

---

## 9. Adding a feature

```
1. Check ARCHITECTURE.md roadmap — add your feature if missing.
2. Read the target engine file(s) end-to-end before touching anything.
3. Patch with smallest viable diff.
4. Add/update test in tests/.
5. Update ARCHITECTURE.md bugs-found table if any bugs were fixed.
6. Run manifesto checklist on your diff.
7. Ship.
```

Never:
- Add TODO/FIXME without a roadmap entry in ARCHITECTURE.md.
- Introduce a new dependency without justifying it in the commit message.
- Touch `shared/rlusd.py` constants without verifying against xrpscan.com first.
- Call Anthropic/OpenAI directly — use `shared/llm.py`.

---

## 10. LLM superpower pattern (`shared/llm.py`)

All AI calls route through `shared/llm.py`. It supports both Anthropic and OpenAI via `BYOK_PROVIDER` env var.

| Engine | Job | Trigger | Model preference |
|---|---|---|---|
| Rails `ai_copywriter.py` | Checkout headline + 2-line description | Invoice creation | `claude-haiku-4-5-20251001` (latency-sensitive) |
| x402-gateway | BYOK LLM proxy | Per agent request | Auto-selected by `BYOK_PROVIDER` |

Rules:
- Always specify a JSON schema in prompts. Parse defensively (try/except on JSON decode).
- Log token counts to ledger for cost attribution.
- Cache identical prompts 24h (in-memory LRU is fine).
- `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` are server-side only — never in `widget.js` or any client-side code.

---

## 11. Go services

Two Go services live in this repo. For both, use `make build` / `make test` from within their directory.

### x402-gateway (`x402-gateway/`)
- Implements the HTTP x402 payment protocol
- Accepts USDC/RLUSD payments, verifies via `https://x402.org/facilitator`
- Acts as a BYOK LLM proxy — agents pay per inference request
- Uses Redis (`forge-redis`) for rate limiting (60 RPM default)
- Uses an XRPL notary wallet for on-chain payment receipts
- Key env: `MERCHANT_WALLET_ADDRESS`, `PAYMENT_AMOUNT_USDC_DROPS=500000`, `X402_FACILITATOR_URL=https://x402.org/facilitator`, `XRPL_NOTARY_WALLET_ADDRESS`, `XRPL_NOTARY_WALLET_SEED`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `BYOK_PROVIDER=auto`, `RATE_LIMIT_RPM=60`

### Shadow Desk (`shadow-desk/`)
- MCP server for signal ingest, replay, and billing
- `alpha/` — alpha signal routing to providers
- `billing/` — payment tracking per provider wallet
- `payment/` — XRPL payment handling
- `ingest/` — signal ingestion pipeline
- `replay/` — historical signal replay
- `mcp/` — MCP protocol implementation
- Deployed at `https://shadow-desk.onrender.com` (health: `/healthz`)
- Key env: `PORT=8080`, `HOST_URL=https://shadow-desk.onrender.com`, `INGEST_SECRET`, `ALPHA_PROVIDER_WALLET`, `PLATFORM_WALLET`, `FACILITATOR_URL=https://x402.org/facilitator`, `ADMIN_API_KEY`

---

## 12. Dashboard (`dashboard/`)

React + Vite + TypeScript + Tailwind CSS operator console. Deployed as Render static site.

```bash
cd dashboard
npm install
npm run dev       # Vite HMR dev server
npm run build     # production build → dist/
```

- Connects to x402-gateway via `VITE_GATEWAY_URL=https://forge-gateway-a822.onrender.com`
- Deployed as `sml-forge-dashboard` static site on Render (auto-deploy on push to master)
- Keep `rails/widget.js` under 30KB minified — it is separately embedded by merchants

---

## 13. Production deployment checklist

```
[ ] All Render service env vars populated (see render.yaml for full list)
[ ] OPERATOR_WALLET_SEED set to MAINNET seed (NOT testnet)
[ ] Operator hot wallet funded ≥ 50 XRP (reserve + buffer)
[ ] RLUSD trustline established on operator wallet (limit: 1,000,000 RLUSD)
[ ] DISCORD_WEBHOOK_* configured for each service
[ ] ANTHROPIC_API_KEY set (tier-1 minimum)
[ ] OPENAI_API_KEY set (if BYOK_PROVIDER includes openai)
[ ] sml-copytrader COPYTRADER_DB_URL from sml-copytrader-db connection string
[ ] sml-launchpad LAUNCHPAD_DB_URL from sml-launchpad-db connection string
[ ] forge-gateway REDIS_URL from forge-redis connection string
[ ] shadow-desk INGEST_SECRET and wallet addresses set
[ ] dashboard VITE_GATEWAY_URL pointing to forge-gateway URL
[ ] Cold wallet sweep cron active (hourly recommended)
[ ] Sentry / BetterStack hooked to all health endpoints
[ ] SQLite WAL mode enabled on any SQLite databases
[ ] PostgreSQL DBs have Render point-in-time recovery enabled
```

---

## 14. Common operator commands

```bash
# Check operator wallet balance
python scripts/wallet_status.py

# Initialize testnet wallet (writes seeds to .env — refuses if already populated)
python scripts/init_testnet_wallet.py

# Verify RLUSD trustline
python scripts/verify_rlusd_trustline.py

# Force-expire a Rails invoice
python -m rails.invoice_engine --expire INVOICE_ID

# Re-sync payment watcher from a specific ledger index
python -m rails.payment_watcher --from-ledger LEDGER_INDEX

# Build Go services
cd x402-gateway && make build
cd shadow-desk && make build

# Dashboard dev server
cd dashboard && npm run dev
```

---

## 15. Non-negotiables

```
❆ No floats for money. Decimal only.
❆ No blocking calls in async paths.
❆ No mainnet testing. Ever.
❆ No tiphawk — it is deleted. Do not recreate it.
❆ No proprietary SML indicator math in this repo.
❆ No filler in operator-facing output.
❆ Real APIs, real endpoints, real wallets — every time.
❆ Two alert formats per event. Always.
❆ All LLM calls via shared/llm.py. Never direct.
❆ Self-audit before you ship.
```

---

**End of CLAUDE.md. You are now SML-grade. Ship.**
