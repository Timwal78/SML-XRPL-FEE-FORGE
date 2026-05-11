#!/usr/bin/env python3
"""
SML XRPL FEE FORGE — RLUSD trustline verifier.

Checks that the operator wallet has an active RLUSD trustline on the configured
network. If missing on testnet, offers to create it via TrustSet tx.

Usage:
    python scripts/verify_rlusd_trustline.py
    python scripts/verify_rlusd_trustline.py --create
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from xrpl.asyncio.transaction import autofill_and_sign, submit_and_wait
from xrpl.models.transactions import TrustSet
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.wallet import Wallet

from shared.xrpl_client import get_client
from shared.rlusd import RLUSD_ISSUER, RLUSD_CURRENCY_HEX, NETWORK


async def main(create: bool = False, limit: str = "1000000") -> None:
    seed = os.environ.get("OPERATOR_WALLET_SEED")
    addr = os.environ.get("OPERATOR_WALLET_ADDRESS")
    if not seed or not addr:
        print("ERROR: OPERATOR_WALLET_SEED / OPERATOR_WALLET_ADDRESS not set in .env")
        print("Run: python scripts/init_testnet_wallet.py")
        sys.exit(1)

    client = get_client()
    print(f"network:  {NETWORK}")
    print(f"operator: {addr}")
    print(f"issuer:   {RLUSD_ISSUER}")
    print()

    has = await client.has_rlusd_trustline(addr)
    if has:
        bal = await client.get_rlusd_balance(addr)
        print(f"[OK] RLUSD trustline active. Balance: {bal} RLUSD")
        return

    print("[X] no RLUSD trustline on operator wallet")
    if not create:
        print()
        print("To create a trustline, re-run with --create:")
        print(f"    python scripts/verify_rlusd_trustline.py --create --limit {limit}")
        if NETWORK == "mainnet":
            print()
            print("[!] MAINNET — creating a trustline costs ~0.2 XRP reserve. Review before proceeding.")
        sys.exit(2)

    if NETWORK == "mainnet":
        confirm = input("[!] Creating trustline on MAINNET. Type 'yes' to confirm: ")
        if confirm.strip().lower() != "yes":
            print("aborted")
            sys.exit(3)

    print(f"creating TrustSet tx with limit {limit} RLUSD…")
    wallet = Wallet.from_seed(seed)
    tx = TrustSet(
        account=wallet.address,
        limit_amount=IssuedCurrencyAmount(
            currency=RLUSD_CURRENCY_HEX,
            issuer=RLUSD_ISSUER,
            value=str(limit),
        ),
    )
    signed = await autofill_and_sign(tx, client.rpc, wallet)
    res = await submit_and_wait(signed, client.rpc, wallet)
    h = res.result.get("hash") or res.result.get("tx_json", {}).get("hash", "")
    engine = res.result.get("meta", {}).get("TransactionResult", "?")
    print(f"  result:  {engine}")
    print(f"  tx hash: {h}")
    if NETWORK == "mainnet":
        print(f"  view:    https://xrpscan.com/tx/{h}")
    else:
        print(f"  view:    https://test.bithomp.com/explorer/{h}")

    has = await client.has_rlusd_trustline(addr)
    print()
    print(f"[OK] trustline active: {has}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", action="store_true", help="create trustline if missing")
    parser.add_argument("--limit", default="1000000", help="trustline limit (default: 1,000,000 RLUSD)")
    args = parser.parse_args()
    asyncio.run(main(create=args.create, limit=args.limit))
