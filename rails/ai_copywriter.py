"""
RLUSD RAILS — AI copywriter (SUPERPOWER).

When a merchant creates a new invoice, this module calls Anthropic's API
to generate a punchy checkout headline + 2-line description, automatically.

Uses claude-haiku for low latency (< 1s typically).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from anthropic import AsyncAnthropic

log = logging.getLogger("rails.copy")


COPY_SYSTEM = """You write checkout copy for crypto/RLUSD payment widgets.
Voice: clean, modern, confident, zero buzzwords. Output STRICT JSON only — no
prose, no code fences. Schema: {"headline": "<6-10 words>", "blurb": "<2 short
sentences, ~30 words total>"}. The headline goes above the pay button. The
blurb explains what the customer is paying for in plain language. Never use
'!', emojis, or marketing speak."""


async def generate_checkout_copy(
    description: str,
    merchant_name: str,
    amount: str,
    currency: str,
) -> Optional[dict]:
    """
    Returns {"headline": ..., "blurb": ...} or None on failure.

    Failure is non-fatal — the invoice still ships without AI copy.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    model = os.environ.get("ANTHROPIC_COPY_MODEL", "claude-haiku-4-5-20251001")
    user = (
        f"Merchant: {merchant_name}\n"
        f"Amount: {amount} {currency}\n"
        f"Item description: {description}\n\n"
        f"Generate checkout copy. Output JSON only."
    )

    try:
        client = AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model=model,
            max_tokens=300,
            system=COPY_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0]
        text = text.strip()
        return json.loads(text)
    except Exception as e:
        log.warning("AI copy generation failed: %s", e)
        return None
