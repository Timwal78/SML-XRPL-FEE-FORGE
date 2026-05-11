# TIPHAWK™

> X/Twitter reply-tipping bot for XRP and RLUSD on the XRP Ledger. Skims 2% per tip to operator wallet.

## How it works

```
1. User tweets:    "@tiphawk_bot tip @someone 5 XRP"
2. TipHawk parses, validates handle registry, computes split:
        gross  = 5.000000 XRP
        fee    = 0.100000 XRP   (2.00%)
        net    = 4.900000 XRP
3. Submits Payment tx to recipient → confirms in 3-5s on XRPL
4. Logs to ledger, fires Discord alert (compact + rich embed)
5. Daily 9am ET: Anthropic-powered digest tweets the top 3 tipped takes
```

## Tip command grammar

```
@tiphawk_bot tip @recipient AMOUNT CURRENCY
```

Examples:
- `@tiphawk_bot tip @sam 5 XRP`
- `@tiphawk_bot tip @sam 10.50 RLUSD`

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Live operations dashboard |
| GET | `/api/health` | Liveness check |
| GET | `/api/stats` | Aggregate stats |
| GET | `/api/recent?limit=N` | Recent tips |
| POST | `/api/manual` | Manual tip injection (admin) |
| POST | `/api/digest` | Force-trigger AI digest (admin) |

## Run

```bash
uvicorn tiphawk.main:app --reload --port 8001
```

Open `http://localhost:8001`.

## Required env

```
TWITTER_BEARER_TOKEN=...
OPERATOR_WALLET_SEED=...
ANTHROPIC_API_KEY=...
DISCORD_WEBHOOK_TIPHAWK=...
TIPHAWK_REGISTRY=alice:rAlice...,bob:rBob...
```

## Architecture

See `ARCHITECTURE.md`.
