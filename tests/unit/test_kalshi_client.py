"""Unit tests for etl/kalshi_client.py -- signing and pagination logic only.
No network calls; requests.Session.get is monkeypatched.
"""
import base64

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding


def test_sign_request_headers_shape(mock_kalshi_client):
    headers = mock_kalshi_client.sign_request("GET", "/trade-api/v2/events")

    assert headers["KALSHI-ACCESS-KEY"] == "test-key-id"
    assert headers["Content-Type"] == "application/json"
    assert headers["KALSHI-ACCESS-TIMESTAMP"].isdigit()
    # signature should be valid base64
    base64.b64decode(headers["KALSHI-ACCESS-SIGNATURE"])


def test_sign_request_signature_is_verifiable(mock_kalshi_client):
    method, path = "GET", "/trade-api/v2/markets"
    headers = mock_kalshi_client.sign_request(method, path)

    timestamp = headers["KALSHI-ACCESS-TIMESTAMP"]
    message = (timestamp + method + path).encode("utf-8")
    signature = base64.b64decode(headers["KALSHI-ACCESS-SIGNATURE"])

    public_key = mock_kalshi_client._private_key.public_key()
    # Should not raise if the signature is valid for this message.
    public_key.verify(
        signature,
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )


def test_paginate_follows_cursor_until_empty(mock_kalshi_client, monkeypatch):
    pages = [
        {"events": [{"event_ticker": "A"}], "cursor": "page-2"},
        {"events": [{"event_ticker": "B"}], "cursor": ""},
    ]
    calls = []

    def fake_get(path, params=None):
        calls.append(dict(params or {}))
        return pages[len(calls) - 1]

    monkeypatch.setattr(mock_kalshi_client, "get", fake_get)

    collected = list(mock_kalshi_client.get_events_pages())

    assert collected == pages
    assert len(calls) == 2
    # second call should carry the cursor returned by the first page
    assert calls[1]["cursor"] == "page-2"
    assert "cursor" not in calls[0]


def test_paginate_stops_on_single_page(mock_kalshi_client, monkeypatch):
    monkeypatch.setattr(mock_kalshi_client, "get", lambda path, params=None: {"markets": [], "cursor": ""})

    collected = list(mock_kalshi_client.get_markets_pages())

    assert len(collected) == 1
