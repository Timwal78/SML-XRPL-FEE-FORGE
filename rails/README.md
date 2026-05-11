# RLUSD RAILS™

> Stripe-style checkout button for accepting RLUSD/XRP on the XRP Ledger. Skims 0.5% per invoice to operator wallet.

## How it works

```
1. Merchant calls POST /api/invoice with amount + their XRPL address
2. RAILS derives a unique 31-bit destination tag (SHA256 + collision-checked)
3. Returns invoice_id, operator_addr, dest_tag, AI-generated checkout copy
4. Customer scans QR / clicks xrpl: deeplink → signs in their wallet
5. Payment lands on operator hot wallet — payment_watcher detects it
6. RAILS instantly forwards merchant_payout → merchant_addr (0.5% retained)
7. Discord alert fires (compact + rich), invoice marked paid, TX hashes recorded
```

## Embed snippet

```html
<script src="https://your-rails.com/widget.js"></script>
<div data-rlusd-rails
     data-merchant-id="acme"
     data-merchant-addr="rYourMerchantAddr..."
     data-amount="99.00"
     data-currency="RLUSD"
     data-description="Pro plan, monthly"
     data-api="https://your-rails.com">
</div>
```

That's it. No SDK install, no PCI scope, no card networks.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Merchant operations dashboard |
| GET | `/widget-demo` | Live demo merchant page |
| GET | `/widget.js` | Embeddable JS widget (<30KB) |
| GET | `/api/health` | Liveness check |
| POST | `/api/invoice` | Create invoice |
| GET | `/api/invoice/{id}` | Invoice status (widget polls this) |
| GET | `/api/invoices?limit=N` | List recent invoices |
| POST | `/api/expire` | Sweep expired invoices |

## Run

```bash
uvicorn rails.main:app --reload --port 8002
```

Open `http://localhost:8002` for the merchant console, `/widget-demo` for the widget in action.

## Required env

```
OPERATOR_WALLET_SEED=...
OPERATOR_WALLET_ADDRESS=...
ANTHROPIC_API_KEY=...
DISCORD_WEBHOOK_RAILS=...
RAILS_PUBLIC_URL=https://your-rails.com
```

The operator wallet must hold a RLUSD trustline before accepting RLUSD invoices. Run `python scripts/verify_rlusd_trustline.py` to check.

## Architecture

See `ARCHITECTURE.md`.
