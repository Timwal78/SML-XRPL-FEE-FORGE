import os
import json
import logging
import httpx
from typing import Optional, Any, Dict, List
from anthropic import AsyncAnthropic

logger = logging.getLogger("shared.llm")

class LLMClient:
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or os.getenv("LLM_PROVIDER", "anthropic").lower()
        self.api_key = os.getenv(f"{self.provider.upper()}_API_KEY")
        self.model = os.getenv(f"{self.provider.upper()}_MODEL")
        
        # Defaults
        if self.provider == "anthropic":
            self.model = self.model or "claude-3-sonnet-20240229"
        elif self.provider == "ollama":
            self.model = self.model or "llama3"
            self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        elif self.provider == "openrouter":
            self.model = self.model or "meta-llama/llama-3-70b-instruct"
            self.base_url = "https://openrouter.ai/api/v1"

    async def generate(self, system: str, user_msg: str, max_tokens: int = 2000) -> str:
        if self.provider == "anthropic":
            return await self._generate_anthropic(system, user_msg, max_tokens)
        elif self.provider == "ollama":
            return await self._generate_ollama(system, user_msg)
        elif self.provider == "openrouter":
            return await self._generate_openrouter(system, user_msg, max_tokens)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    async def _generate_anthropic(self, system: str, user_msg: str, max_tokens: int) -> str:
        client = AsyncAnthropic(api_key=self.api_key)
        resp = await client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return "".join(b.text for b in resp.content if hasattr(b, "text"))

    async def _generate_ollama(self, system: str, user_msg: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": f"System: {system}\n\nUser: {user_msg}",
            "stream": False,
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "")

    async def _generate_openrouter(self, system: str, user_msg: str, max_tokens: int) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg}
            ],
            "max_tokens": max_tokens
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

async def generate_completion(system: str, user_msg: str, provider: Optional[str] = None) -> str:
    """
    Generates a completion with an automatic failover strategy.
    Order: Primary (from env) -> Anthropic -> OpenRouter -> Ollama (local fallback)
    """
    primary = provider or os.getenv("LLM_PROVIDER", "anthropic").lower()
    providers = [primary, "anthropic", "openrouter", "ollama"]
    
    # Deduplicate while preserving order
    seen = set()
    providers = [p for p in providers if not (p in seen or seen.add(p))]
    
    last_err = None
    for p in providers:
        try:
            logger.info(f"Attempting LLM generation with provider: {p}")
            client = LLMClient(provider=p)
            return await client.generate(system, user_msg)
        except Exception as e:
            logger.warning(f"LLM Provider {p} failed: {str(e)}")
            last_err = e
            continue
            
    raise last_err or RuntimeError("All LLM providers failed.")
