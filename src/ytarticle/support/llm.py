"""Unified LLM client — call any OpenAI-compatible API."""
from __future__ import annotations
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ytarticle.llm")

_CLIENTS: dict[str, object] = {}


def _get_client(api_key: str, base_url: str, timeout: int = 120):
    cache_key = f"{api_key[:8]}::{base_url}"
    if cache_key not in _CLIENTS:
        from openai import OpenAI
        _CLIENTS[cache_key] = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
    return _CLIENTS[cache_key]


def call_llm(system_prompt: str, user_prompt: str,
             max_tokens: int = 8192, temperature: float = 0.8) -> str:
    """Call any OpenAI-compatible API.

    Configure via .env or environment:
      LLM_API_KEY   — API key (required)
      LLM_BASE_URL  — API base URL (default: https://api.deepseek.com)
      LLM_MODEL     — Model name (default: deepseek-chat)

    Examples:
      DeepSeek:   LLM_BASE_URL=https://api.deepseek.com        LLM_MODEL=deepseek-chat
      OpenAI:     LLM_BASE_URL=https://api.openai.com/v1       LLM_MODEL=gpt-4o
      Anthropic:  LLM_BASE_URL=https://api.anthropic.com/v1    LLM_MODEL=claude-sonnet-4
      vLLM:       LLM_BASE_URL=http://localhost:8000/v1        LLM_MODEL=my-model
    """
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("LLM_MODEL", "deepseek-chat")

    if not api_key:
        raise RuntimeError(
            "LLM_API_KEY not set. Configure in .env:\n"
            "  LLM_API_KEY=sk-xxx\n"
            "  LLM_BASE_URL=https://api.deepseek.com\n"
            "  LLM_MODEL=deepseek-chat"
        )

    try:
        client = _get_client(api_key, base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"LLM call failed: {e}") from e
