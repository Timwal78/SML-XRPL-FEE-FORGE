import asyncio
import logging
import json
from typing import List
from xrpl.asyncio.clients import AsyncWebsocketClient
from xrpl.models.requests import Subscribe, AccountTx
from shared.xrpl_client import get_client
from .engine import ExecutionEngine
from .models import Leader

logger = logging.getLogger("copytrader.watcher")

class LeaderWatcher:
    def __init__(self, db_engine):
        self.db_engine = db_engine
        self.engine = ExecutionEngine(db_engine)
        self.client = get_client()

    async def start(self, leader_addresses: List[str]):
        """
        Starts the WebSocket listener for the given leader addresses.
        """
        async with self.client.ws_client() as ws_client:
            # 1. Subscribe to account streams
            # Note: account_tx doesn't support multiple accounts in one subscribe call easily for streams
            # so we use 'subscribe' with 'accounts' filter if the node supports it, or individual subscriptions.
            
            # For simplicity and robustness, we use the 'accounts' filter in subscribe
            subscribe_req = Subscribe(accounts=leader_addresses)
            await ws_client.send(subscribe_req)
            
            logger.info(f"Subscribed to {len(leader_addresses)} leaders: {leader_addresses}")

            async for message in ws_client:
                # logger.debug(f"RAW MSG: {message}") # Too noisy for prod, good for stress
                await self._handle_message(message)

    async def _handle_message(self, message: dict):
        msg_type = message.get("type")
        if msg_type != "transaction":
            return

        # Handle various stream formats (validated vs non-validated)
        tx = message.get("tx_json") or message.get("transaction")
        if not tx:
            logger.warning(f"Received transaction message without tx_json or transaction field: {message.keys()}")
            return
            
        # Ensure hash is present (often at top level in stream, but in tx_json in account_tx)
        tx_hash = tx.get("hash") or message.get("hash")
        if not tx_hash:
            logger.warning(f"Transaction missing hash: {tx}")
            return
        
        tx["hash"] = tx_hash

        leader_addr = tx.get("Account")
        if not leader_addr:
            return

        # Check if this is a leader we are watching
        from .models import select, Session
        with Session(self.db_engine) as session:
            leader = session.exec(select(Leader).where(Leader.address == leader_addr)).first()
            
            if not leader:
                # This can happen if the subscription includes other accounts or is a global stream
                return

            logger.info(f"DETECTED leader trade [{leader_addr}] hash: {tx_hash}")
            
            # Pass to execution engine
            try:
                await self.engine.mirror_tx(leader, tx)
            except Exception as e:
                logger.error(f"Error in engine.mirror_tx for {tx_hash}: {e}", exc_info=True)
