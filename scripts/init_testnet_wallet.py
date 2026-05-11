#!/usr/bin/env python3
"""
SML XRPL FEE FORGE — testnet wallet initializer.

Generates a fresh wallet via the XRPL testnet faucet and writes the seed +
address into .env (idempotent — refuses to overwrite without --force).

Usage:
    python scripts/init_testnet_wallet.py
    python scripts/init_testnet_wallet.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from xrpl.asyncio.clients import AsyncJsonRpcClient
from xrpl.asyncio.wallet import generate_faucet_wallet


TESTNET_RPC = "https://s.altnet.rippletest.net:51234"
ENV_PATH = ROOT / ".env"


def read_env() -> dict[str, str]:
    if not ENV_PATH.exists():
        # Bootstrap from .env.example
        example = ROOT / ".env.example"
        if example.exists():
            ENV_PATH.write_text(example.read_text())
            print(f"created {ENV_PATH} from .env.example")
        else:
            ENV_PATH.write_text("")
            print(f"created empty {ENV_PATH}")
    text = ENV_PATH.read_text()
    out = {}
    for line in text.splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def write_env(updates: dict[str, str]) -> None:
    text = ENV_PATH.read_text() if ENV_PATH.exists() else ""
    lines = text.splitlines()
    keys_seen = set()
    new_lines = []
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}")
                keys_seen.add(k)
                continue
        new_lines.append(line)
    for k, v in updates.items():
        if k not in keys_seen:
            new_lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(new_lines) + "\n")


async def main(force: bool = False) -> None:
    env = read_env()
    if env.get("OPERATOR_WALLET_SEED") and not force:
        print("OPERATOR_WALLET_SEED already set in .env. Refusing to overwrite.")
        print("Pass --force to regenerate. (You will lose the existing seed!)")
        sys.exit(1)

    print("requesting wallet from XRPL testnet faucet…")
    client = AsyncJsonRpcClient(TESTNET_RPC)
    wallet = await generate_faucet_wallet(client, debug=False)

    print(f"  address: {wallet.address}")
    print(f"  seed:    {wallet.seed}")

    write_env({
        "OPERATOR_WALLET_SEED": wallet.seed,
        "OPERATOR_WALLET_ADDRESS": wallet.address,
        "FEE_WALLET_ADDRESS": wallet.address,
        "XRPL_NETWORK": "testnet",
    })

    print(f"\n[OK] wrote seeds to {ENV_PATH}")
    print(f"[OK] funded with testnet XRP")
    print(f"\nView on testnet explorer:")
    print(f"  https://test.bithomp.com/explorer/{wallet.address}")
    print(f"\nNext: python scripts/verify_rlusd_trustline.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="overwrite existing seed")
    args = parser.parse_args()
    asyncio.run(main(force=args.force))
