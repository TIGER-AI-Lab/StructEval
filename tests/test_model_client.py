import asyncio
from types import SimpleNamespace

from structeval.model_client import LiteLLMClient, LiteLLMSettings, image_to_data_url


def make_response(text):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
    )


def test_batch_completion_preserves_order(monkeypatch):
    async def fake_acompletion(**params):
        prompt = params["messages"][0]["content"]
        if prompt == "slow":
            await asyncio.sleep(0.01)
        return make_response(f"response:{prompt}")

    monkeypatch.setattr("structeval.model_client.litellm.acompletion", fake_acompletion)
    client = LiteLLMClient(LiteLLMSettings(model="openai/test"))

    result = asyncio.run(client.complete_text_batch(["slow", "fast"], concurrency=2))

    assert result == ["response:slow", "response:fast"]


def test_completion_retries(monkeypatch):
    calls = 0

    async def fake_acompletion(**params):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("transient")
        return make_response("ok")

    monkeypatch.setattr("structeval.model_client.litellm.acompletion", fake_acompletion)
    client = LiteLLMClient(LiteLLMSettings(model="openai/test", max_retries=1))

    assert asyncio.run(client.complete([{"role": "user", "content": "hi"}])) == "ok"
    assert calls == 2


def test_image_to_data_url(tmp_path):
    image_path = tmp_path / "image.png"
    image_path.write_bytes(b"png-bytes")

    data_url = image_to_data_url(image_path)

    assert data_url.startswith("data:image/png;base64,")
    assert data_url.endswith("cG5nLWJ5dGVz")
