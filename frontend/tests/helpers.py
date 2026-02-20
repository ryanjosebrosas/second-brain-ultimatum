"""Shared test utilities for frontend tests."""

import httpx


def make_response(
    status_code: int = 200,
    json_data: dict | list | None = None,
) -> httpx.Response:
    """Create a mock httpx.Response with the given status and JSON body."""
    if json_data is None:
        json_data = {}
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "http://test"),
    )
