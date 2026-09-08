"""Client for Kalshi's demo trading API.

Reuses the RSA request-signing approach from the project's original
authentication.py (PSS padding, SHA-256, base64-encoded signature sent as
KALSHI-ACCESS-KEY/SIGNATURE/TIMESTAMP headers), adapted to load key material
from Settings/environment variables instead of a hardcoded file path.

Only general events/markets endpoints are used here (not the cricket-specific
/milestones endpoint from the old code), and pagination follows Kalshi's
cursor-based "cursor" query parameter / response field.
"""
from __future__ import annotations

import base64
import datetime as dt
import logging
from typing import Any, Dict, Iterator, Optional

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import Settings, get_settings

DEFAULT_TIMEOUT = (10, 10)  # (connect timeout, read timeout) seconds

logger = logging.getLogger("etl.kalshi_client")


class KalshiClient:
    """Thin, retrying, request-signing HTTP client for the Kalshi API."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.base_url = self.settings.kalshi_base_url.rstrip("/")
        self._private_key = self._load_private_key()
        self.session = self._build_session()

    # -- key / signing -----------------------------------------------------

    def _load_private_key(self):
        pem_bytes: bytes
        if self.settings.kalshi_private_key_pem:
            pem_bytes = self.settings.kalshi_private_key_pem.encode("utf-8")
        elif self.settings.kalshi_private_key_path:
            with open(self.settings.kalshi_private_key_path, "rb") as key_file:
                pem_bytes = key_file.read()
        else:
            raise ValueError(
                "No Kalshi private key configured: set KALSHI_PRIVATE_KEY_PATH "
                "or KALSHI_PRIVATE_KEY_PEM in the environment."
            )
        return serialization.load_pem_private_key(pem_bytes, password=None, backend=default_backend())

    def sign_request(self, method: str, path: str) -> Dict[str, str]:
        timestamp = str(int(dt.datetime.now().timestamp() * 1000))
        message = timestamp + method + path

        signature = self._private_key.sign(
            message.encode("utf-8"),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
            hashes.SHA256(),
        )

        return {
            "KALSHI-ACCESS-KEY": self.settings.kalshi_key_id,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode("utf-8"),
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json",
        }

    # -- HTTP session --------------------------------------------------------

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        headers = self.sign_request("GET", path)
        response = self.session.get(
            f"{self.base_url}{path}",
            headers=headers,
            params=params,
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    # -- pagination -----------------------------------------------------------

    def paginate(
        self,
        path: str,
        result_key: str,
        params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
        max_pages: Optional[int] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Yield one raw page (full JSON response dict) at a time, following
        Kalshi's cursor-based pagination until the cursor is exhausted or
        `max_pages` is reached (Kalshi's demo environment can have a very
        large backlog, so an unbounded pull can run for a long time).
        """
        query: Dict[str, Any] = dict(params or {})
        query["limit"] = page_size
        cursor: Optional[str] = None
        page_number = 0

        while True:
            if cursor:
                query["cursor"] = cursor
            page = self.get(path, params=query)
            page_number += 1
            logger.info(
                "event=page_fetched path=%s page=%d items=%d",
                path,
                page_number,
                len(page.get(result_key, [])),
            )
            yield page

            cursor = page.get("cursor") or None
            if not cursor:
                break
            if max_pages is not None and page_number >= max_pages:
                logger.info("event=page_cap_reached path=%s max_pages=%d", path, max_pages)
                break

    def get_events_pages(
        self, params: Optional[Dict[str, Any]] = None, max_pages: Optional[int] = None
    ) -> Iterator[Dict[str, Any]]:
        """Pages of GET /trade-api/v2/events, with each event's markets
        embedded inline (`with_nested_markets=true`). Kalshi paginates events
        and markets independently, so pulling markets via a second,
        separately-paginated call can return markets whose event falls
        outside this run's event page window; nesting markets under their
        event avoids that mismatch entirely.
        """
        query: Dict[str, Any] = dict(params or {})
        query.setdefault("with_nested_markets", True)
        return self.paginate("/trade-api/v2/events", result_key="events", params=query, max_pages=max_pages)

    def get_markets_pages(
        self, params: Optional[Dict[str, Any]] = None, max_pages: Optional[int] = None
    ) -> Iterator[Dict[str, Any]]:
        return self.paginate("/trade-api/v2/markets", result_key="markets", params=params, max_pages=max_pages)
