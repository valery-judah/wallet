from __future__ import annotations

from scripts.devex.smoke.common import HttpClient, assert_json_object, assert_status

name = "health"


def run(client: HttpClient) -> None:
    response = client.request("GET", "/api/v1/health")
    assert_status(response, 200)

    body = assert_json_object(response)
    if body.get("status") != "ok":
        raise AssertionError(f"unexpected health payload: {body!r}")
