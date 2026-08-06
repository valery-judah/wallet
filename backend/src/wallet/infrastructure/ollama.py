from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from wallet.ai.llm import (
    StructuredChatResponseError,
    StructuredChatTransportError,
)
from wallet.domain._validation import normalize_nonblank


class OllamaStructuredChatModel:
    """Synchronous Ollama adapter for schema-constrained chat responses.

    Construction is local; network calls occur only when completing or listing models.
    """

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen3.5:9b",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url = normalize_nonblank(base_url, field_name="Ollama base URL").rstrip("/")
        self.model = normalize_nonblank(model, field_name="Ollama model")
        if timeout_seconds <= 0:
            raise ValueError("Ollama timeout must be positive")
        self.timeout_seconds = timeout_seconds

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> str:
        response = self._request_json(
            method="POST",
            path="/api/chat",
            payload={
                "model": self.model,
                "stream": False,
                "think": False,
                "options": {"temperature": 0},
                "format": output_schema,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        message = response.get("message")
        if not isinstance(message, dict):
            raise StructuredChatResponseError("Ollama response has no message object")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise StructuredChatResponseError("Ollama response has no message content")
        return content

    def list_models(self) -> set[str]:
        response = self._request_json(method="GET", path="/api/tags")
        models = response.get("models")
        if not isinstance(models, list):
            raise StructuredChatResponseError("Ollama tags response has no models list")

        names: set[str] = set()
        for model in models:
            if not isinstance(model, dict):
                raise StructuredChatResponseError("Ollama tags response contains an invalid model")
            name = model.get("name")
            if isinstance(name, str) and name:
                names.add(name)
        return names

    def _request_json(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"accept": "application/json", "content-type": "application/json"},
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = _read_http_error(exc)
            raise StructuredChatTransportError(
                f"Ollama request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise StructuredChatTransportError(f"Ollama request failed: {exc}") from exc

        try:
            decoded = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise StructuredChatResponseError("Ollama returned invalid JSON") from exc
        if not isinstance(decoded, dict):
            raise StructuredChatResponseError("Ollama returned a non-object response")
        error = decoded.get("error")
        if isinstance(error, str) and error:
            raise StructuredChatResponseError(f"Ollama returned an error: {error}")
        return decoded


def _read_http_error(error: HTTPError) -> str:
    try:
        raw_body = error.read().decode("utf-8")
        decoded = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return error.reason or "request failed"
    if isinstance(decoded, dict):
        message = decoded.get("error")
        if isinstance(message, str):
            return message
    return raw_body or error.reason or "request failed"
