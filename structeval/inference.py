from __future__ import annotations

import asyncio
from typing import Any, Sequence

from .model_client import LiteLLMClient, LiteLLMSettings


PROMPT_SUFFIX = (
    "\n\nIMPORTANT: Only output the required output format. You must start the "
    "format/code with <|BEGIN_CODE|> and end the format/code with <|END_CODE|>. "
    "No other text output (explanation, comments, etc.) are allowed. Do not use "
    "markdown code fences."
)


def build_prompt(query: str) -> str:
    return f"{query}{PROMPT_SUFFIX}"


async def run_inference_async(
    model_name: str,
    queries: Sequence[str],
    *,
    concurrency: int = 8,
    temperature: float = 1.0,
    max_tokens: int | None = None,
    timeout: float | None = None,
    max_retries: int = 2,
    api_base: str | None = None,
    api_key_env: str | None = None,
    litellm_params: dict[str, Any] | None = None,
) -> list[str]:
    client = LiteLLMClient(
        LiteLLMSettings(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            api_base=api_base,
            api_key_env=api_key_env,
            litellm_params=litellm_params or {},
        )
    )
    prompts = [build_prompt(query) for query in queries]
    return await client.complete_text_batch(
        prompts,
        concurrency=concurrency,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def run_inference(model_name: str, queries: Sequence[str], **kwargs: Any) -> list[str]:
    return asyncio.run(run_inference_async(model_name, queries, **kwargs))
