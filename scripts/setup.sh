#!/usr/bin/env bash
# SML XRPL FEE FORGE — one-shot setup
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "▌ SML XRPL FEE FORGE — setup"
echo

# 1. Python venv
if [ ! -d ".venv" ]; then
  echo "[1/4] creating venv…"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# 2. Deps
echo "[2/4] installing deps…"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# 3. .env
if [ ! -f ".env" ]; then
  echo "[3/4] bootstrapping .env from .env.example…"
  cp .env.example .env
else
  echo "[3/4] .env exists — skipping"
fi

# 4. Testnet wallet
if ! grep -q "^OPERATOR_WALLET_SEED=s" .env 2>/dev/null; then
  echo "[4/4] generating testnet wallet…"
  python scripts/init_testnet_wallet.py
else
  echo "[4/4] wallet already configured — skipping"
fi

echo
echo "✓ setup complete"
echo
echo "next steps:"
echo "  1. python scripts/verify_rlusd_trustline.py --create   (testnet)"
echo "  2. uvicorn tiphawk.main:app --reload --port 8001       (terminal A)"
echo "  3. uvicorn rails.main:app   --reload --port 8002       (terminal B)"
echo "  4. open http://localhost:8001  +  http://localhost:8002/widget-demo"
