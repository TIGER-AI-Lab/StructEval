from __future__ import annotations

import asyncio
import base64
import mimetypes
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import litellm


Message = dict[str, Any]
ENV_FALLBACKS = {
    "OPENROUTER_API_KEY": ("OPEN_ROUTER_API_KEY",),
}


@dataclass
class LiteLLMSettings:
    model: str
    temperature: float = 1.0
    max_tokens: int | None = None
    timeout: float | None = None
    max_retries: int = 2
    api_base: str | None = None
    api_key_env: str | None = None
    litellm_params: dict[str, Any] = field(default_factory=dict)


class LiteLLMClient:
    def __init__(self, settings: LiteLLMSettings):
        self.settings = settings

    async def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        params = self._request_params(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )

        last_error: Exception | None = None
        attempts = max(0, self.settings.max_retries) + 1
        for attempt in range(attempts):
            try:
                response = await litellm.acompletion(**params)
                return response_to_text(response)
            except Exception as exc:  # pragma: no cover - concrete type depends on provider
                last_error = exc
                if attempt == attempts - 1:
                    break
                await asyncio.sleep(min(2**attempt, 8))

        raise RuntimeError(f"LiteLLM request failed after {attempts} attempts") from last_error

    async def complete_text_batch(
        self,
        prompts: Sequence[str],
        *,
        concurrency: int = 8,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> list[str]:
        semaphore = asyncio.Semaphore(max(1, concurrency))
        results: list[str | None] = [None] * len(prompts)

        async def run_one(index: int, prompt: str) -> None:
            async with semaphore:
                results[index] = await self.complete(
                    [{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

        await asyncio.gather(*(run_one(index, prompt) for index, prompt in enumerate(prompts)))
        return [result if result is not None else "" for result in results]

    def _request_params(
        self,
        *,
        messages: Sequence[Message],
        temperature: float | None,
        max_tokens: int | None,
        response_format: dict[str, Any] | None,
    ) -> dict[str, Any]:
        params = dict(self.settings.litellm_params)
        params.update(
            {
                "model": self.settings.model,
                "messages": list(messages),
                "temperature": self.settings.temperature
                if temperature is None
                else temperature,
            }
        )

        token_limit = self.settings.max_tokens if max_tokens is None else max_tokens
        if token_limit is not None:
            params["max_tokens"] = token_limit
        if self.settings.timeout is not None:
            params["timeout"] = self.settings.timeout
        if self.settings.api_base:
            params["api_base"] = self.settings.api_base
        if self.settings.api_key_env:
            api_key = get_env_with_fallback(self.settings.api_key_env)
            if not api_key:
                accepted_names = ", ".join(env_names_with_fallbacks(self.settings.api_key_env))
                raise RuntimeError(
                    f"Environment variable {accepted_names} is not set."
                )
            params["api_key"] = api_key
        if response_format is not None:
            params["response_format"] = response_format
        return params


def env_names_with_fallbacks(env_name: str) -> tuple[str, ...]:
    return (env_name, *ENV_FALLBACKS.get(env_name, ()))


def get_env_with_fallback(env_name: str) -> str | None:
    for candidate in env_names_with_fallbacks(env_name):
        value = os.environ.get(candidate)
        if value:
            return value
    return None


def response_to_text(response: Any) -> str:
    """Extract assistant text from LiteLLM/OpenAI-style responses."""
    try:
        content = response.choices[0].message.content
    except AttributeError:
        content = response["choices"][0]["message"]["content"]
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, Mapping) else str(part)
            for part in content
        )
    return str(content)


def image_to_data_url(path: str | Path) -> str:
    image_path = Path(path)
    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"
