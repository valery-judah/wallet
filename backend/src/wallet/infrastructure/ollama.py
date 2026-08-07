from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from wallet.ai.llm import (
    StructuredChatResponseError,
    StructuredChatTransportError,
)
from wallet.domain._validation import normalize_nonblank
from wallet.observability import error_details, log_event

logger = logging.getLogger(__name__)


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
        context_length: int = 8192,
    ) -> None:
        self.base_url = normalize_nonblank(base_url, field_name="Ollama base URL").rstrip("/")
        self.model = normalize_nonblank(model, field_name="Ollama model")
        if timeout_seconds <= 0:
            raise ValueError("Ollama timeout must be positive")
        self.timeout_seconds = timeout_seconds
        if context_length <= 0:
            raise ValueError("Ollama context length must be positive")
        self.context_length = context_length

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
                "options": {
                    "temperature": 0,
                    "seed": 0,
                    "num_ctx": self.context_length,
                    "num_predict": 512,
                },
                "format": output_schema,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        message = response.get("message")
        if not isinstance(message, dict):
            error = StructuredChatResponseError("Ollama response has no message object")
            self._log_response_failure(method="POST", path="/api/chat", error=error)
            raise error
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            error = StructuredChatResponseError("Ollama response has no message content")
            self._log_response_failure(method="POST", path="/api/chat", error=error)
            raise error
        return content

    def list_models(self) -> set[str]:
        response = self._request_json(method="GET", path="/api/tags")
        models = response.get("models")
        if not isinstance(models, list):
            error = StructuredChatResponseError("Ollama tags response has no models list")
            self._log_response_failure(method="GET", path="/api/tags", error=error)
            raise error

        names: set[str] = set()
        for model in models:
            if not isinstance(model, dict):
                error = StructuredChatResponseError(
                    "Ollama tags response contains an invalid model"
                )
                self._log_response_failure(method="GET", path="/api/tags", error=error)
                raise error
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
        started_at = perf_counter()
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
            log_event(
                logger,
                logging.WARNING,
                "ollama.request.failed",
                data={
                    "method": method,
                    "endpoint": path,
                    "model": self.model,
                    "status_code": exc.code,
                    "duration_ms": round(_duration_ms(started_at), 2),
                },
                error=error_details(exc, code="ollama_http_error", retryable=True),
            )
            detail = _read_http_error(exc)
            raise StructuredChatTransportError(
                f"Ollama request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            log_event(
                logger,
                logging.WARNING,
                "ollama.request.failed",
                data={
                    "method": method,
                    "endpoint": path,
                    "model": self.model,
                    "status_code": None,
                    "duration_ms": round(_duration_ms(started_at), 2),
                },
                error=error_details(exc, code="ollama_transport_error", retryable=True),
            )
            raise StructuredChatTransportError(f"Ollama request failed: {exc}") from exc

        try:
            decoded = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            log_event(
                logger,
                logging.WARNING,
                "ollama.request.failed",
                data={
                    "method": method,
                    "endpoint": path,
                    "model": self.model,
                    "status_code": None,
                    "duration_ms": round(_duration_ms(started_at), 2),
                    "stage": "decode_response",
                },
                error=error_details(exc, code="ollama_invalid_json", retryable=True),
            )
            raise StructuredChatResponseError("Ollama returned invalid JSON") from exc
        if not isinstance(decoded, dict):
            response_shape_error = StructuredChatResponseError(
                "Ollama returned a non-object response"
            )
            self._log_response_failure(
                method=method,
                path=path,
                error=response_shape_error,
            )
            raise response_shape_error
        error_value = decoded.get("error")
        if isinstance(error_value, str) and error_value:
            response_error = StructuredChatResponseError(f"Ollama returned an error: {error_value}")
            self._log_response_failure(method=method, path=path, error=response_error)
            raise response_error
        completion_metrics = {
            key: value
            for key in (
                "prompt_eval_count",
                "eval_count",
                "prompt_eval_duration",
                "eval_duration",
                "load_duration",
                "total_duration",
            )
            if isinstance((value := decoded.get(key)), int)
        }
        log_event(
            logger,
            logging.INFO,
            "ollama.request.completed",
            data={
                "method": method,
                "endpoint": path,
                "model": self.model,
                "duration_ms": round(_duration_ms(started_at), 2),
                **completion_metrics,
            },
        )
        return decoded

    def _log_response_failure(
        self,
        *,
        method: str,
        path: str,
        error: StructuredChatResponseError,
    ) -> None:
        log_event(
            logger,
            logging.WARNING,
            "ollama.request.failed",
            data={
                "method": method,
                "endpoint": path,
                "model": self.model,
                "status_code": None,
                "stage": "validate_response",
            },
            error=error_details(error, code="ollama_invalid_response", retryable=True),
        )


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


def _duration_ms(started_at: float) -> float:
    return (perf_counter() - started_at) * 1_000
