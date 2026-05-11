import asyncio
import os
from dotenv import load_dotenv
from shared.xrpl_client import get_client
from xrpl.wallet import Wallet
from xrpl.models.transactions import AccountSet
from xrpl.asyncio.transaction import autofill_and_sign, submit_and_wait

load_dotenv()

async def fix():
    c = get_client()
    seed = os.getenv('OPERATOR_WALLET_SEED')
    if not seed:
        print("No seed found.")
        return
    w = Wallet.from_seed(seed)
    print(f"Hardening account {w.address}...")
    tx = AccountSet(
        account=w.address,
        set_flag=8 # ASF_DEFAULT_RIPPLE
    )
    signed = await autofill_and_sign(tx, c.rpc, w)
    res = await submit_and_wait(signed, c.rpc, w)
    print(f"Result: {res.result.get('meta', {}).get('TransactionResult')}")

if __name__ == "__main__":
    asyncio.run(fix())
