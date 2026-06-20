from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    body: Any
    url: str


class SmokeFailure(AssertionError):
    def __init__(self, message: str, *, response: HttpResponse | None = None) -> None:
        super().__init__(message)
        self.response = response


class HttpClient:
    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> HttpResponse:
        request_body: bytes | None = None
        headers: dict[str, str] = {"accept": "application/json"}
        if payload is not None:
            request_body = json.dumps(payload).encode("utf-8")
            headers["content-type"] = "application/json"

        url = f"{self.base_url}{path}"
        request = Request(url, data=request_body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
                return HttpResponse(
                    status_code=response.status,
                    body=_decode_json(raw_body),
                    url=url,
                )
        except HTTPError as exc:
            raw_body = exc.read().decode("utf-8")
            return HttpResponse(
                status_code=exc.code,
                body=_decode_json(raw_body),
                url=url,
            )
        except URLError as exc:
            raise SmokeFailure(f"request failed: {exc.reason}") from exc


def assert_status(response: HttpResponse, expected_status: int) -> None:
    if response.status_code != expected_status:
        raise SmokeFailure(
            f"expected HTTP {expected_status}, got {response.status_code}",
            response=response,
        )


def assert_json_object(response: HttpResponse) -> dict[str, Any]:
    if not isinstance(response.body, dict):
        raise SmokeFailure(
            f"expected JSON object body, got {type(response.body).__name__}",
            response=response,
        )
    return response.body


def unique_card_name(prefix: str) -> str:
    return f"{prefix} {uuid.uuid4().hex[:8]}"


def _decode_json(raw_body: str) -> Any:
    if raw_body == "":
        return None
    try:
        return json.loads(raw_body)
    except json.JSONDecodeError:
        return raw_body
