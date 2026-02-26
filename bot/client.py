"""
Low-level Binance Futures Testnet REST client.

Handles authentication (HMAC-SHA256 signing), request dispatch, and
raw response parsing.  All public methods return parsed JSON dicts
or raise ``BinanceAPIError`` / ``requests`` exceptions.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

import requests

logger = logging.getLogger("trading_bot")

BASE_URL = "https://demo-fapi.binance.com"

# ── Custom exceptions ──────────────────────────────────────────────────────


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response."""

    def __init__(self, status_code: int, code: int, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"[HTTP {status_code}] Binance error {code}: {message}")


# ── Client ─────────────────────────────────────────────────────────────────


class BinanceFuturesClient:
    """Thin wrapper around the Binance USDT-M Futures Testnet API."""

    def __init__(self, api_key: str, api_secret: str, base_url: str = BASE_URL):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": self.api_key})

    # ── context-manager support ────────────────────────────────────────

    def __enter__(self) -> "BinanceFuturesClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    # ── internal helpers ───────────────────────────────────────────────

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add ``timestamp`` and ``signature`` to *params* (in-place)."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Union[Dict[str, Any], List[Any]]:
        """
        Send an HTTP request to the Binance API.

        Parameters
        ----------
        method : str
            HTTP verb (``GET``, ``POST``, ``DELETE``, …).
        path : str
            API path, e.g. ``/fapi/v1/order``.
        params : dict, optional
            Query / body parameters.
        signed : bool
            If ``True``, add HMAC-SHA256 signature.

        Returns
        -------
        dict
            Parsed JSON response body.

        Raises
        ------
        BinanceAPIError
            On any non-2xx response from Binance.
        requests.RequestException
            On network-level failures (timeout, DNS, etc.).
        """
        url = f"{self.base_url}{path}"
        params = dict(params or {})

        if signed:
            self._sign(params)

        logger.debug(
            "API request  -> %s %s params=%s",
            method,
            url,
            {k: v for k, v in params.items() if k != "signature"},
        )

        response = self._session.request(method, url, params=params, timeout=10)

        logger.debug(
            "API response <- %s (%.1f KB)",
            response.status_code,
            len(response.content) / 1024,
        )

        if not response.ok:
            try:
                body = response.json()
                code = body.get("code", -1)
                msg = body.get("msg", response.text)
            except ValueError:
                code = -1
                msg = response.text
            raise BinanceAPIError(response.status_code, code, msg)

        return response.json()

    # ── public API methods ─────────────────────────────────────────────

    def ping(self) -> Dict[str, Any]:
        """Test connectivity to the API (``GET /fapi/v1/ping``)."""
        return self._request("GET", "/fapi/v1/ping")

    def server_time(self) -> Dict[str, Any]:
        """Get Binance server time (``GET /fapi/v1/time``)."""
        return self._request("GET", "/fapi/v1/time")

    def place_order(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Place a new order (``POST /fapi/v1/order``).

        All keyword arguments are forwarded as query parameters to the API.
        Common keys: ``symbol``, ``side``, ``type``, ``quantity``,
        ``price``, ``timeInForce``.

        Returns
        -------
        dict
            Order acknowledgement from Binance.
        """
        return self._request("POST", "/fapi/v1/order", params=kwargs, signed=True)

    def get_account(self) -> Dict[str, Any]:
        """Fetch account information (``GET /fapi/v2/account``)."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    def get_ticker_price(self, symbol: str) -> Dict[str, Any]:
        """Get latest price for a symbol (``GET /fapi/v1/ticker/price``)."""
        return self._request("GET", "/fapi/v1/ticker/price", params={"symbol": symbol})

    def get_ticker_24hr(self, symbol: str) -> Dict[str, Any]:
        """Get 24hr price change stats (``GET /fapi/v1/ticker/24hr``)."""
        return self._request("GET", "/fapi/v1/ticker/24hr", params={"symbol": symbol})

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get current open orders (``GET /fapi/v1/openOrders``)."""
        params: Dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order (``DELETE /fapi/v1/order``)."""
        return self._request(
            "DELETE", "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get position information (``GET /fapi/v2/positionRisk``)."""
        return self._request("GET", "/fapi/v2/positionRisk", signed=True)

    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 24) -> List[List[Any]]:
        """Get candlestick/kline data (``GET /fapi/v1/klines``)."""
        return self._request("GET", "/fapi/v1/klines", params={
            "symbol": symbol, "interval": interval, "limit": limit,
        })

    def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get exchange trading rules (``GET /fapi/v1/exchangeInfo``)."""
        params: Dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/exchangeInfo", params=params)
