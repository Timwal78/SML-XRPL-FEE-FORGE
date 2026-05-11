"""
TIPHAWK — X / Twitter listener.

Subscribes to the filtered_stream endpoint of X API v2 and listens for
mentions of the bot handle that contain a `tip` command.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import tweepy

from tiphawk.tip_engine import parse_tip, execute_tip

log = logging.getLogger("tiphawk.listener")


class TipStreamListener(tweepy.StreamingClient):
    """
    Subclass of tweepy.StreamingClient that dispatches each incoming
    tweet to the tip engine via asyncio.run_coroutine_threadsafe.
    """

    def __init__(self, bearer_token: str, loop: asyncio.AbstractEventLoop):
        super().__init__(bearer_token=bearer_token, wait_on_rate_limit=True)
        self.loop = loop

    def on_tweet(self, tweet: tweepy.Tweet) -> None:
        try:
            text = tweet.text or ""
            tweet_id = str(tweet.id)
            sender = (tweet.author_id or "")  # we resolve handle below if needed
            # tweepy v4 returns author_id; we expect the 'expansions' to give us username
            # via tweet.includes — but on_tweet receives only the tweet object.
            # In production, fetch the user via tweet.includes['users'] using the
            # client.get_tweet expansion. For MVP we accept that handle is in text:
            # The tip command includes both bot and recipient as @handles.
            # Sender handle must be retrieved from the API user lookup.

            # Quick resolve (sync because we're in tweepy callback thread)
            sender_handle = self._resolve_handle(tweet.author_id) or "unknown"

            cmd = parse_tip(text, sender_handle=sender_handle, tweet_id=tweet_id)
            if not cmd:
                return
            bot_handle = os.environ.get("TIPHAWK_BOT_HANDLE", "tiphawk_bot")
            if cmd.bot.lower() != bot_handle.lower():
                return

            log.info("tip detected: %s", cmd)
            # Schedule into the FastAPI loop
            asyncio.run_coroutine_threadsafe(execute_tip(cmd), self.loop)
        except Exception as e:
            log.exception("on_tweet handler failed: %s", e)

    def _resolve_handle(self, author_id) -> Optional[str]:
        if not author_id:
            return None
        try:
            client = tweepy.Client(
                bearer_token=os.environ["TWITTER_BEARER_TOKEN"]
            )
            u = client.get_user(id=author_id)
            return u.data.username if u and u.data else None
        except Exception:
            return None


def start_stream_in_background(loop: asyncio.AbstractEventLoop) -> Optional[TipStreamListener]:
    """
    Start the X filtered_stream in a background thread.
    Configures rules so we only receive @bot mentions with the word 'tip'.
    """
    bearer = os.environ.get("TWITTER_BEARER_TOKEN")
    bot = os.environ.get("TIPHAWK_BOT_HANDLE", "tiphawk_bot")
    if not bearer:
        log.warning("TWITTER_BEARER_TOKEN not set — Twitter listener disabled")
        return None

    listener = TipStreamListener(bearer, loop=loop)

    # Reset rules and add fresh rule
    existing = listener.get_rules()
    if existing.data:
        ids = [r.id for r in existing.data]
        listener.delete_rules(ids)
    rule = tweepy.StreamRule(value=f"@{bot} tip", tag="tiphawk-mention")
    listener.add_rules(rule)

    listener.filter(
        threaded=True,
        expansions=["author_id"],
        tweet_fields=["author_id", "created_at", "text"],
    )
    log.info("TipHawk Twitter stream started (rule: @%s tip)", bot)
    return listener
