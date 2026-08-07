from __future__ import annotations

import json
import logging
import os
import re
import sys
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, date, datetime
from enum import Enum
from types import TracebackType
from typing import Any

_SCHEMA_VERSION = 1
_SERVICE = "wallet-api"
_URL_PATTERN = re.compile(r"https?://\S+")
_environment = os.getenv("WALLET_ENVIRONMENT", "local")
_log_context: ContextVar[dict[str, object] | None] = ContextVar(
    "wallet_log_context",
    default=None,
)
_domain_success_events_enabled: ContextVar[bool] = ContextVar(
    "wallet_domain_success_events_enabled",
    default=True,
)


class JsonLogFormatter(logging.Formatter):
    """Render every Python log record as one stable, privacy-conscious JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        recorded_context = getattr(record, "event_context", None)
        context = _json_mapping(
            recorded_context if isinstance(recorded_context, Mapping) else _current_log_context()
        )
        trace_id = context.pop("trace_id", None)
        event = getattr(record, "event", None)
        data = getattr(record, "event_data", None)
        error = getattr(record, "event_error", None)
        if not isinstance(event, str):
            event = "runtime.log"
            data = {"message": _safe_runtime_message(record.getMessage())}
        formatted_error = _json_mapping(error) if isinstance(error, Mapping) else None
        if isinstance(record.exc_info, tuple) and record.exc_info[0] is not None:
            if formatted_error is None:
                formatted_error = {
                    "type": record.exc_info[0].__name__,
                    "code": "unexpected_error",
                    "retryable": False,
                }
            formatted_error["stacktrace"] = _safe_stacktrace(record.exc_info[2])

        envelope = {
            "schema_version": _SCHEMA_VERSION,
            "timestamp": _timestamp(record.created),
            "level": record.levelname,
            "service": _SERVICE,
            "environment": _environment,
            "event": event,
            "logger": record.name,
            "source": {
                "module": record.name,
                "function": record.funcName,
                "line": record.lineno,
            },
            "trace_id": trace_id,
            "context": context,
            "data": _json_mapping(data) if isinstance(data, Mapping) else {},
            "error": formatted_error,
        }
        return json.dumps(envelope, separators=(",", ":"), ensure_ascii=False)


def configure_logging(level: str, *, environment: str = "local") -> None:
    """Configure a single JSON stdout stream without discarding host handlers."""

    normalized = level.upper()
    resolved_level = logging.getLevelNamesMapping().get(normalized)
    if not isinstance(resolved_level, int):
        raise ValueError(f"unknown logging level: {level}")

    global _environment
    _environment = environment
    root = logging.getLogger()
    root.setLevel(resolved_level)
    formatter = JsonLogFormatter()
    if not root.handlers:
        stdout_handler = logging.StreamHandler(sys.stdout)
        root.addHandler(stdout_handler)
    for handler in root.handlers:
        handler.setFormatter(formatter)
    logging.getLogger("wallet").setLevel(resolved_level)
    logging.getLogger("uvicorn").setLevel(resolved_level)
    logging.getLogger("uvicorn.error").setLevel(resolved_level)
    logging.getLogger("uvicorn.access").disabled = True


@contextmanager
def bind_log_context(**values: object) -> Iterator[None]:
    """Temporarily merge correlation values into the current execution context."""

    merged = dict(_current_log_context())
    for key, value in values.items():
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    token = _log_context.set(merged)
    try:
        yield
    finally:
        _log_context.reset(token)


@contextmanager
def suppress_domain_success_events() -> Iterator[None]:
    token = _domain_success_events_enabled.set(False)
    try:
        yield
    finally:
        _domain_success_events_enabled.reset(token)


def domain_success_events_enabled() -> bool:
    return _domain_success_events_enabled.get()


def _current_log_context() -> dict[str, object]:
    return _log_context.get() or {}


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    data: Mapping[str, object] | None = None,
    error: Mapping[str, object] | None = None,
    exc_info: bool | BaseException = False,
) -> None:
    event_context = dict(_current_log_context())
    event_context.setdefault("origin", "internal")
    logger.log(
        level,
        event,
        extra={
            "event": event,
            "event_data": dict(data or {}),
            "event_error": None if error is None else dict(error),
            "event_context": event_context,
        },
        exc_info=exc_info,
        stacklevel=2,
    )


def error_details(
    error: BaseException,
    *,
    code: str,
    retryable: bool,
) -> dict[str, object]:
    return {
        "type": type(error).__name__,
        "code": code,
        "retryable": retryable,
    }


def _timestamp(created: float) -> str:
    return (
        datetime.fromtimestamp(created, tz=UTC)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _safe_runtime_message(message: str) -> str:
    return _URL_PATTERN.sub("<url>", message)


def _safe_stacktrace(traceback_value: TracebackType | None) -> list[dict[str, object]]:
    frames: list[dict[str, object]] = []
    current = traceback_value
    while current is not None:
        frame = current.tb_frame
        frames.append(
            {
                "module": frame.f_globals.get("__name__", "unknown"),
                "function": frame.f_code.co_name,
                "file": frame.f_code.co_filename.rsplit("/", maxsplit=1)[-1],
                "line": current.tb_lineno,
            }
        )
        current = current.tb_next
    return frames


def _json_mapping(value: Mapping[Any, Any]) -> dict[str, Any]:
    return {str(key): _json_safe(item) for key, item in value.items()}


def _json_safe(value: object) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Enum):
        return _json_safe(value.value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return _json_mapping(value)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_json_safe(item) for item in value]
    return f"<{type(value).__name__}>"
