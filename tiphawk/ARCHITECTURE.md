# TIPHAWK — Architecture

## Sub-engines

| Module | Responsibility |
|---|---|
| `twitter_listener.py` | X API v2 filtered_stream subscriber + handle resolver |
| `tip_engine.py` | Parse tip command → resolve addrs → split fee → submit XRPL Payment |
| `fee_engine.py` | 2% skim math (Decimal-safe) |
| `ledger.py` | SQLite persistence (sqlmodel + WAL mode) |
| `ai_digest.py` | Anthropic-powered daily digest (SUPERPOWER) |
| `main.py` | FastAPI app + lifespan management |
| `dashboard.html` | Beastmode terminal-aesthetic ops console |

## Flow diagram

```mermaid
sequenceDiagram
    autonumber
    participant U as Tweeter
    participant X as X API v2 stream
    participant L as twitter_listener
    participant T as tip_engine
    participant F as fee_engine
    participant XRPL as XRP Ledger
    participant D as Discord
    participant DB as ledger.db

    U->>X: posts "@tiphawk_bot tip @sam 5 XRP"
    X-->>L: streamed tweet (filtered_stream rule)
    L->>L: parse author + text
    L->>T: parse_tip() → TipCommand
    T->>T: resolve_address(@sam) from registry
    T->>F: calc_tip_split(5 XRP) → (4.90, 0.10)
    T->>DB: record(status=pending)
    T->>XRPL: send_xrp(operator_wallet → @sam, 4.90)
    XRPL-->>T: tx_hash, validated
    T->>DB: update_status(sent, tx_hash)
    T->>D: send_rich(embed) + send_compact(text)
    D-->>U: alert in Discord channel
```

## Math

```
gross           = parsed amount (Decimal)
fee_bps         = 200
fee_amount      = gross × 200 / 10_000
net_amount      = gross − fee_amount

XRP rounding:   Decimal.quantize(Decimal('0.000001'), HALF_UP)   # 6dp = drops
RLUSD rounding: Decimal.quantize(Decimal('0.01'),     HALF_UP)   # 2dp = cents
```

## Resource budget

| Resource | Idle | Burst (10 tips/sec) |
|---|---|---|
| RAM | 80 MB | 130 MB |
| CPU | 0.02 vCPU | 0.4 vCPU |
| XRPL submissions | 0 | ~10/s (well under rippled limits) |
| Twitter quota | streaming connection | filtered_stream (no quota beyond rules) |

## Bugs found during build

| # | Bug | Fix |
|---|---|---|
| 1 | `Money` accepted floats which leaked binary precision | Convert via `str()` before Decimal |
| 2 | `submit_and_wait` blocked event loop in tweepy callback | Used `asyncio.run_coroutine_threadsafe` to dispatch |
| 3 | Trustline not pre-flighted on RLUSD tips | Added `has_rlusd_trustline()` check, raises `TrustlineMissingError` |
| 4 | Twitter rate limit on rapid mentions could 429 | `wait_on_rate_limit=True` on tweepy client |

## Verified-clean

- [x] `decimal.Decimal` for all currency math
- [x] Async-safe tweepy ↔ asyncio bridge
- [x] Trustline pre-flight on every RLUSD tip
- [x] Both alert formats sent on every event
- [x] Unregistered handles gracefully fail with logged record
- [x] No proprietary indicator math
- [x] No mock data anywhere

## Roadmap

- v1.1: Telegram mirror (same grammar)
- v1.1: User self-registration via DM ("register YOUR_XRPL_ADDR")
- v1.2: Non-custodial signing flow (Xumm deeplink)
- v1.2: Auto-tweet receipt with xrpscan link
- v2.0: Tip leaderboards / season system
