"""Shared test fixtures for frontend tests.

Provides mock httpx clients and Streamlit session state stubs
so that api_client.py functions can be tested without a running API server
or a Streamlit runtime.
"""

import pytest
from unittest.mock import MagicMock, patch

import httpx


def _make_response(
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


@pytest.fixture
def mock_client():
    """A MagicMock httpx.Client with configurable .get/.post/.delete returns.

    Usage in tests:
        def test_something(mock_client):
            mock_client.get.return_value = _make_response(200, {"key": "value"})
            # ... call api_client function ...
    """
    client = MagicMock(spec=httpx.Client)
    # Default: all methods return 200 with empty JSON
    client.get.return_value = _make_response(200, {})
    client.post.return_value = _make_response(200, {})
    client.delete.return_value = _make_response(200, {})
    return client


@pytest.fixture(autouse=True)
def patch_get_client(mock_client):
    """Automatically patch _get_client() in api_client to return the mock.

    This runs for every test automatically (autouse=True), so no test
    needs to manually set up the client mock. Tests can customize
    behavior by configuring mock_client's return values.
    """
    with patch("api_client._get_client", return_value=mock_client):
        yield mock_client
