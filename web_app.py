#!/usr/bin/env python3
"""
Lightweight Flask web UI for the Binance Futures Testnet trading bot.

Run::

    python web_app.py                # http://127.0.0.1:5000
    python web_app.py --port 8080    # custom port

Environment variables (all optional — API keys loaded from ``.env``)::

    FLASK_DEBUG=0     Set to 1 for reloader + debugger (never in production)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request

# ── Bootstrap ──────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

from bot.logging_config import setup_logging          # noqa: E402
from bot.validators import validate_all               # noqa: E402
from bot.client import BinanceFuturesClient, BinanceAPIError  # noqa: E402
from bot.orders import place_order                     # noqa: E402

# ── App setup ──────────────────────────────────────────────────────────────
logger = setup_logging()
app = Flask(__name__, template_folder=os.path.join(SCRIPT_DIR, "templates"))

# ── Shared client (re-used across requests) ────────────────────────────────
_client: Optional[BinanceFuturesClient] = None

# In-memory order history (resets on restart — fine for a lightweight UI)
_MAX_HISTORY = 200
_order_history: List[Dict[str, Any]] = []


def _get_client() -> BinanceFuturesClient:
    """Return a shared client instance, creating it on first call.

    Raises
    ------
    RuntimeError
        If ``BINANCE_API_KEY`` or ``BINANCE_API_SECRET`` are not set.
    """
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        raise RuntimeError(
            "Missing API credentials. Set BINANCE_API_KEY and "
            "BINANCE_API_SECRET in .env or as environment variables."
        )
    _client = BinanceFuturesClient(api_key, api_secret)
    logger.info("Binance client initialised (shared instance)")
    return _client


def _ok(data: Any) -> Tuple[Response, int]:
    """Standard JSON success envelope."""
    return jsonify({"success": True, "data": data}), 200


def _error(exc: Exception, status: int = 500) -> Tuple[Response, int]:
    """Standard JSON error envelope."""
    return jsonify({"success": False, "error": str(exc)}), status


# ── Routes ─────────────────────────────────────────────────────────────────


@app.route("/")
def index() -> str:
    """Serve the single-page trading dashboard."""
    return render_template("index.html")


# ── Market data ────────────────────────────────────────────────────────────


@app.route("/api/ticker/<symbol>")
def api_ticker(symbol: str) -> Tuple[Response, int]:
    """24-hr ticker statistics for *symbol*."""
    try:
        data = _get_client().get_ticker_24hr(symbol.upper())
        return _ok(data)
    except BinanceAPIError as exc:
        return _error(exc, 502)
    except Exception as exc:
        logger.exception("Ticker error for %s", symbol)
        return _error(exc)


@app.route("/api/klines/<symbol>")
def api_klines(symbol: str) -> Tuple[Response, int]:
    """Candlestick data.  Query params: ``?interval=1h&limit=50``."""
    try:
        interval = request.args.get("interval", "1h")
        limit_str = request.args.get("limit", "50")
        try:
            limit = min(int(limit_str), 500)
        except ValueError:
            return _error(ValueError(f"Invalid limit: {limit_str!r}"), 400)

        raw = _get_client().get_klines(symbol.upper(), interval, limit)
        candles = [
            {"t": c[0], "o": c[1], "h": c[2], "l": c[3], "c": c[4], "v": c[5]}
            for c in raw
        ]
        return _ok(candles)
    except BinanceAPIError as exc:
        return _error(exc, 502)
    except Exception as exc:
        logger.exception("Klines error for %s", symbol)
        return _error(exc)


# ── Account data ───────────────────────────────────────────────────────────


@app.route("/api/account")
def api_account() -> Tuple[Response, int]:
    """Account balances and margin info."""
    try:
        data = _get_client().get_account()
        assets = [
            a for a in data.get("assets", [])
            if float(a.get("walletBalance", 0)) > 0
        ]
        summary = {
            "totalWalletBalance": data.get("totalWalletBalance"),
            "totalUnrealizedProfit": data.get("totalUnrealizedProfit"),
            "totalMarginBalance": data.get("totalMarginBalance"),
            "availableBalance": data.get("availableBalance"),
            "assets": assets,
        }
        return _ok(summary)
    except BinanceAPIError as exc:
        return _error(exc, 502)
    except Exception as exc:
        logger.exception("Account error")
        return _error(exc)


@app.route("/api/positions")
def api_positions() -> Tuple[Response, int]:
    """Open positions (non-zero amount only)."""
    try:
        all_pos = _get_client().get_positions()
        active = [p for p in all_pos if float(p.get("positionAmt", 0)) != 0]
        return _ok(active)
    except BinanceAPIError as exc:
        return _error(exc, 502)
    except Exception as exc:
        logger.exception("Positions error")
        return _error(exc)


# ── Orders ─────────────────────────────────────────────────────────────────


@app.route("/api/order", methods=["POST"])
def api_place_order() -> Tuple[Response, int]:
    """Place an order.  JSON body: ``{ symbol, side, order_type, quantity, price? }``."""
    body = request.get_json(silent=True) or {}

    symbol = body.get("symbol", "")
    side = body.get("side", "")
    order_type = body.get("order_type", "")
    quantity = body.get("quantity", "")
    price = body.get("price") or None

    # Validate
    try:
        params = validate_all(symbol, side, order_type, quantity, price)
    except ValueError as exc:
        logger.warning("Order validation failed: %s", exc)
        return _error(exc, 400)

    # Place order
    try:
        response = place_order(
            client=_get_client(),
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params["price"],
        )
    except BinanceAPIError as exc:
        logger.error("Binance API error: %s", exc)
        return _error(exc, 502)
    except RuntimeError as exc:
        logger.error("Client error: %s", exc)
        return _error(exc)
    except Exception as exc:
        logger.exception("Unexpected order error")
        return _error(exc)

    # Record in session history
    record: Dict[str, Any] = {
        "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "orderId": response.get("orderId"),
        "symbol": response.get("symbol"),
        "side": response.get("side"),
        "type": response.get("type"),
        "status": response.get("status"),
        "origQty": response.get("origQty"),
        "executedQty": response.get("executedQty"),
        "avgPrice": response.get("avgPrice", "N/A"),
        "price": response.get("price", "N/A"),
    }
    _order_history.insert(0, record)
    # Cap history to prevent unbounded memory growth
    if len(_order_history) > _MAX_HISTORY:
        del _order_history[_MAX_HISTORY:]

    return _ok(record)


@app.route("/api/open-orders")
def api_open_orders() -> Tuple[Response, int]:
    """All open orders, optionally filtered by ``?symbol=BTCUSDT``."""
    try:
        sym = request.args.get("symbol")
        data = _get_client().get_open_orders(sym.upper() if sym else None)
        return _ok(data)
    except BinanceAPIError as exc:
        return _error(exc, 502)
    except Exception as exc:
        logger.exception("Open orders error")
        return _error(exc)


@app.route("/api/cancel-order", methods=["POST"])
def api_cancel_order() -> Tuple[Response, int]:
    """Cancel an order.  JSON body: ``{ symbol, orderId }``."""
    body = request.get_json(silent=True) or {}
    symbol = body.get("symbol", "")
    order_id = body.get("orderId")

    if not symbol or order_id is None:
        return _error(ValueError("symbol and orderId are required"), 400)

    try:
        oid = int(order_id)
    except (TypeError, ValueError):
        return _error(ValueError(f"Invalid orderId: {order_id!r}"), 400)

    try:
        data = _get_client().cancel_order(symbol.upper(), oid)
        return _ok(data)
    except BinanceAPIError as exc:
        logger.error("Cancel error: %s", exc)
        return _error(exc, 502)
    except Exception as exc:
        logger.exception("Cancel error")
        return _error(exc)


@app.route("/api/orders")
def api_order_history() -> Tuple[Response, int]:
    """Return the in-memory order history (wrapped in the standard envelope)."""
    return _ok(_order_history)


@app.route("/api/status")
def api_status() -> Tuple[Response, int]:
    """Health check — pings Binance and returns connectivity status."""
    try:
        _get_client().ping()
        return jsonify({"success": True, "status": "connected"}), 200
    except Exception as exc:
        return jsonify({"success": False, "status": "disconnected", "error": str(exc)}), 200


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Trading Bot Web UI")
    parser.add_argument("--port", type=int, default=5000, help="Port (default 5000)")
    parser.add_argument("--host", default="127.0.0.1", help="Host (default 127.0.0.1)")
    cli_args = parser.parse_args()

    # Fail fast if credentials are missing
    try:
        _get_client().ping()
        logger.info("Binance API reachable ✓")
    except RuntimeError as e:
        logger.error("%s", e)
        sys.exit(1)
    except Exception as e:
        logger.warning("Binance connectivity check failed: %s (starting anyway)", e)

    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"
    print(f"\n  🚀 Trading Bot UI → http://{cli_args.host}:{cli_args.port}")
    if debug_mode:
        print("     ⚠  Debug mode ON — do not expose to the internet\n")
    else:
        print()

    app.run(host=cli_args.host, port=cli_args.port, debug=debug_mode)
