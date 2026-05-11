"""
SML XRPL FEE FORGE — shared XRPL client.

Single source of truth for connecting to the XRP Ledger. Used by both
TIPHAWK and RAILS engines.
"""

from __future__ import annotations

import asyncio
import os
from decimal import Decimal
from typing import Optional

from xrpl.asyncio.clients import AsyncJsonRpcClient, AsyncWebsocketClient
from xrpl.asyncio.transaction import autofill_and_sign, submit_and_wait
from xrpl.asyncio.account import get_balance
from xrpl.models.requests import AccountLines
from xrpl.models.transactions import Payment, Transaction
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.wallet import Wallet
from xrpl.utils import xrp_to_drops

from shared.rlusd import RLUSD_ISSUER, RLUSD_CURRENCY_HEX, NETWORK


class TrustlineMissingError(Exception):
    """Raised when a required RLUSD trustline is not present."""


class XRPLClient:
    """
    Async XRPL client wrapping xrpl-py.

    Network is selected from env (XRPL_NETWORK=testnet|mainnet).
    All money values use Decimal — never float.
    """

    def __init__(self) -> None:
        if NETWORK == "mainnet":
            self.rpc_url = os.environ.get(
                "XRPL_RPC_MAINNET", "https://xrplcluster.com"
            )
            self.ws_url = os.environ.get(
                "XRPL_WS_MAINNET", "wss://xrplcluster.com"
            )
        else:
            self.rpc_url = os.environ.get(
                "XRPL_RPC_TESTNET", "https://s.altnet.rippletest.net:51234"
            )
            self.ws_url = os.environ.get(
                "XRPL_WS_TESTNET", "wss://s.altnet.rippletest.net:51233"
            )

        self._rpc: Optional[AsyncJsonRpcClient] = None

    @property
    def rpc(self) -> AsyncJsonRpcClient:
        if self._rpc is None:
            self._rpc = AsyncJsonRpcClient(self.rpc_url)
        return self._rpc

    # -------------------------------------------------------------------
    # Balance + trustline checks
    # -------------------------------------------------------------------
    async def get_xrp_balance(self, address: str) -> Decimal:
        """Returns XRP balance as Decimal (in XRP, not drops)."""
        drops = await get_balance(address, self.rpc)
        return Decimal(drops) / Decimal(1_000_000)

    async def get_rlusd_balance(self, address: str) -> Decimal:
        """Returns RLUSD balance as Decimal. Returns 0 if no trustline."""
        req = AccountLines(account=address, peer=RLUSD_ISSUER)
        resp = await self.rpc.request(req)
        for line in resp.result.get("lines", []):
            if (
                line.get("currency") == RLUSD_CURRENCY_HEX
                or line.get("currency") == "RLUSD"
            ) and line.get("account") == RLUSD_ISSUER:
                return Decimal(line["balance"])
        return Decimal(0)

    async def has_rlusd_trustline(self, address: str) -> bool:
        """Pre-flight check: does this account have a RLUSD trustline?"""
        req = AccountLines(account=address, peer=RLUSD_ISSUER)
        resp = await self.rpc.request(req)
        for line in resp.result.get("lines", []):
            currency = line.get("currency", "")
            account = line.get("account", "")
            if (
                currency in (RLUSD_CURRENCY_HEX, "RLUSD")
                and account == RLUSD_ISSUER
            ):
                return True
        return False

    # -------------------------------------------------------------------
    # Payment construction
    # -------------------------------------------------------------------
    async def send_xrp(
        self,
        wallet: Wallet,
        destination: str,
        amount_xrp: Decimal,
        destination_tag: Optional[int] = None,
        memo: Optional[str] = None,
    ) -> dict:
        """Send native XRP. amount_xrp is Decimal in XRP units."""
        drops = xrp_to_drops(str(amount_xrp))
        tx = Payment(
            account=wallet.address,
            destination=destination,
            amount=drops,
            destination_tag=destination_tag,
        )
        signed = await autofill_and_sign(tx, self.rpc, wallet)
        result = await submit_and_wait(signed, self.rpc, wallet)
        return result.result

    async def send_rlusd(
        self,
        wallet: Wallet,
        destination: str,
        amount_rlusd: Decimal,
        destination_tag: Optional[int] = None,
    ) -> dict:
        """
        Send RLUSD. Pre-flights both sender AND receiver trustlines.

        Raises TrustlineMissingError if either side lacks a trustline.
        """
        if not await self.has_rlusd_trustline(wallet.address):
            raise TrustlineMissingError(
                f"Sender {wallet.address} has no RLUSD trustline"
            )
        if not await self.has_rlusd_trustline(destination):
            raise TrustlineMissingError(
                f"Recipient {destination} has no RLUSD trustline"
            )

        amount = IssuedCurrencyAmount(
            currency=RLUSD_CURRENCY_HEX,
            issuer=RLUSD_ISSUER,
            value=str(amount_rlusd.quantize(Decimal("0.01"))),
        )
        tx = Payment(
            account=wallet.address,
            destination=destination,
            amount=amount,
            destination_tag=destination_tag,
        )
        signed = await autofill_and_sign(tx, self.rpc, wallet)
        result = await submit_and_wait(signed, self.rpc, wallet)
        return result.result

    # -------------------------------------------------------------------
    # Generic Transaction Submission
    # -------------------------------------------------------------------
    async def submit_transaction(self, tx: dict | Transaction, wallet: Wallet) -> dict:
        """Signs and submits an arbitrary transaction to the ledger."""
        signed = await autofill_and_sign(tx, self.rpc, wallet)
        result = await submit_and_wait(signed, self.rpc, wallet)
        return result.result

    # -------------------------------------------------------------------
    # WebSocket streaming (used by rails/payment_watcher.py)
    # -------------------------------------------------------------------
    def ws_client(self) -> AsyncWebsocketClient:
        return AsyncWebsocketClient(self.ws_url)


# Module-level singleton
_client: Optional[XRPLClient] = None


def get_client() -> XRPLClient:
    global _client
    if _client is None:
        _client = XRPLClient()
    return _client
