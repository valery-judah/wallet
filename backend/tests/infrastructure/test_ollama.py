from __future__ import annotations

import json
import logging
from io import BytesIO
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

import wallet.infrastructure.ollama as ollama_module
from wallet.ai.llm import StructuredChatResponseError, StructuredChatTransportError
from wallet.infrastructure.ollama import OllamaStructuredChatModel


class FakeResponse:
    def __init__(self, body: object) -> None:
        self._body = json.dumps(body).encode("utf-8")

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_complete_sends_non_streaming_schema_constrained_chat_request(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    requests: list[tuple[Request, float]] = []

    def fake_urlopen(request: Request, *, timeout: float) -> FakeResponse:
        requests.append((request, timeout))
        return FakeResponse(
            {
                "message": {"role": "assistant", "content": '{"value":1}'},
                "prompt_eval_count": 321,
                "eval_count": 12,
                "prompt_eval_duration": 1_200_000,
                "eval_duration": 3_400_000,
                "load_duration": 5_600_000,
                "total_duration": 10_200_000,
            }
        )

    monkeypatch.setattr(ollama_module, "urlopen", fake_urlopen)
    model = OllamaStructuredChatModel(
        base_url="http://localhost:11434/",
        model="qwen3.5:9b",
        timeout_seconds=12.5,
        context_length=32768,
    )
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"value": {"type": "integer"}},
    }
    caplog.set_level(logging.INFO, logger="wallet.infrastructure.ollama")

    content = model.complete(
        system_prompt="private system marker 7f34b6",
        user_prompt="private user marker 8a45c7",
        output_schema=schema,
    )

    assert content == '{"value":1}'
    request, timeout = requests[0]
    assert request.full_url == "http://localhost:11434/api/chat"
    assert timeout == 12.5
    assert json.loads(request.data or b"") == {
        "model": "qwen3.5:9b",
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "seed": 0, "num_ctx": 32768, "num_predict": 512},
        "format": schema,
        "messages": [
            {"role": "system", "content": "private system marker 7f34b6"},
            {"role": "user", "content": "private user marker 8a45c7"},
        ],
    }
    completed = next(
        record
        for record in caplog.records
        if getattr(record, "event", None) == "ollama.request.completed"
    )
    assert completed.event_data["endpoint"] == "/api/chat"
    assert completed.event_data["prompt_eval_count"] == 321
    assert completed.event_data["eval_count"] == 12
    assert completed.event_data["total_duration"] == 10_200_000
    assert "private system marker" not in caplog.text
    assert "private user marker" not in caplog.text


def test_list_models_reads_available_ollama_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: Request, *, timeout: float) -> FakeResponse:
        assert request.full_url.endswith("/api/tags")
        return FakeResponse(
            {
                "models": [
                    {"name": "qwen3.5:9b"},
                    {"name": "qwen3.5:4b"},
                ]
            }
        )

    monkeypatch.setattr(ollama_module, "urlopen", fake_urlopen)

    assert OllamaStructuredChatModel().list_models() == {
        "qwen3.5:9b",
        "qwen3.5:4b",
    }


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"message": None},
        {"message": {}},
        {"message": {"content": "  "}},
    ],
)
def test_complete_rejects_missing_message_content(
    response: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ollama_module,
        "urlopen",
        lambda request, timeout: FakeResponse(response),
    )

    with pytest.raises(StructuredChatResponseError, match="message"):
        OllamaStructuredChatModel().complete(
            system_prompt="system",
            user_prompt="user",
            output_schema={},
        )


def test_complete_wraps_http_and_network_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    error = HTTPError(
        url="http://localhost:11434/api/chat",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=BytesIO(b'{"error":"model not found"}'),
    )
    monkeypatch.setattr(
        ollama_module,
        "urlopen",
        lambda request, timeout: (_ for _ in ()).throw(error),
    )

    with pytest.raises(StructuredChatTransportError, match="model not found"):
        OllamaStructuredChatModel().complete(
            system_prompt="system",
            user_prompt="user",
            output_schema={},
        )

    monkeypatch.setattr(
        ollama_module,
        "urlopen",
        lambda request, timeout: (_ for _ in ()).throw(URLError("offline")),
    )
    with pytest.raises(StructuredChatTransportError, match="offline"):
        OllamaStructuredChatModel().complete(
            system_prompt="system",
            user_prompt="user",
            output_schema={},
        )
