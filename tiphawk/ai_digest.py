"""
TIPHAWK — AI digest (SUPERPOWER).

Daily 9am ET cron generates a digest of top-tipped tweets via Anthropic's API
and posts it as a tweet thread + Substack section.

Uses claude-sonnet-4-5 for the long-form digest (high quality narrative).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from tiphawk.ledger import get_ledger, TipRecord

log = logging.getLogger("tiphawk.digest")

DIGEST_SYSTEM = """You are TIPHAWK's daily editor. You write a punchy, signal-only
digest of yesterday's most-tipped takes on X. Voice: terse, observational, no
filler, no marketing copy. You highlight the 3 strongest takes, attribute them
to the @handle of the author, and end with one line of your own pattern
recognition. Never editorialize beyond that one closing line. Output STRICT JSON
matching the schema provided. No prose outside JSON."""

DIGEST_SCHEMA = {
    "tweet_thread": [
        "string (max 280 chars per item, 4-7 items)",
    ],
    "substack_html": "string (HTML for Substack post body)",
    "tags": ["array of strings"],
}


from shared.llm import generate_completion

async def generate_digest(top_tips: list[TipRecord]) -> dict:
    """
    Calls configured LLM to compose the daily digest.
    """
    # Compose source material
    source_lines = []
    for r in top_tips:
        source_lines.append(
            f"- @{r.sender_handle} → @{r.recipient_handle}: "
            f"{r.gross_amount} {r.currency}\n  \"{r.tweet_text[:200]}\""
        )
    source_block = "\n".join(source_lines)

    user_msg = f"""Yesterday's top-tipped tweets via TIPHAWK:

{source_block}

Compose the daily digest. Output STRICT JSON matching this schema:
{json.dumps(DIGEST_SCHEMA, indent=2)}

The tweet_thread should be a 4-7 item thread. The first tweet should hook with
"Yesterday on TIPHAWK ⚡". Subsequent tweets each cover one of the top 3 takes
with the @handle credit. Final tweet is your own one-line pattern observation.

substack_html should be a clean HTML fragment (h2, p, blockquote allowed).

tags: 3-5 lowercase hashtag-friendly strings."""

    text = await generate_completion(system=DIGEST_SYSTEM, user_msg=user_msg)
    text = text.strip()
    if text.startswith("```"):
        # Strip code fences if present
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    parsed = json.loads(text)
    return parsed


async def run_daily_digest() -> Optional[dict]:
    """
    Top-level: fetches yesterday's top tips, generates digest, returns dict.

    Caller is responsible for actually posting to X / Substack.
    """
    ledger = get_ledger()
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    tops = ledger.daily_top(yesterday, limit=10)

    if not tops:
        log.info("no tips yesterday — skipping digest")
        return None

    return await generate_digest(tops)


if __name__ == "__main__":
    import asyncio

    result = asyncio.run(run_daily_digest())
    print(json.dumps(result, indent=2) if result else "no digest")
