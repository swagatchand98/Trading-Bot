#!/usr/bin/env python3
"""
CLI entry point for the Binance Futures Testnet trading bot.

Usage examples
--------------
Market order::

    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

Limit order::

    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 50000
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

# ── Bootstrap ──────────────────────────────────────────────────────────────
# Ensure the package root is on sys.path so ``bot`` can be imported when this
# script is executed directly (``python cli.py …``).
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from bot.logging_config import setup_logging
from bot.validators import validate_all
from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.orders import place_order, format_order_response

# ── Argument parser ────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Place orders on Binance Futures Testnet (USDT-M).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python cli.py --symbol BTCUSDT --side BUY  --type MARKET --quantity 0.01\n"
            "  python cli.py --symbol ETHUSDT --side SELL --type LIMIT  --quantity 0.1 --price 3000\n"
        ),
    )
    parser.add_argument("--symbol", required=True, help="Trading pair (e.g. BTCUSDT)")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"], help="Order side")
    parser.add_argument("--type", required=True, dest="order_type", choices=["MARKET", "LIMIT", "market", "limit"], help="Order type")
    parser.add_argument("--quantity", required=True, help="Order quantity")
    parser.add_argument("--price", default=None, help="Limit price (required for LIMIT orders)")
    return parser


# ── Main ───────────────────────────────────────────────────────────────────


def main() -> None:
    # Load .env for API keys
    load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

    logger = setup_logging()

    parser = build_parser()
    args = parser.parse_args()

    # --- Read credentials ---------------------------------------------------
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        logger.error(
            "Missing API credentials. Set BINANCE_API_KEY and BINANCE_API_SECRET "
            "in a .env file or as environment variables."
        )
        sys.exit(1)

    # --- Validate inputs ----------------------------------------------------
    try:
        params = validate_all(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
        )
    except ValueError as exc:
        logger.error("Validation error: %s", exc)
        sys.exit(1)

    # --- Print request summary ----------------------------------------------
    print()
    print("─── Order Request Summary ────────────────────")
    print(f"  Symbol   : {params['symbol']}")
    print(f"  Side     : {params['side']}")
    print(f"  Type     : {params['order_type']}")
    print(f"  Quantity : {params['quantity']}")
    if params["price"] is not None:
        print(f"  Price    : {params['price']}")
    print("───────────────────────────────────────────────")
    print()

    # --- Place order --------------------------------------------------------
    client = BinanceFuturesClient(api_key, api_secret)

    try:
        response = place_order(
            client=client,
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params["price"],
        )
    except BinanceAPIError as exc:
        logger.error("Binance API error: %s", exc)
        print(f"\n✗ Order FAILED – {exc}")
        sys.exit(1)
    except Exception as exc:
        logger.exception("Unexpected error while placing order")
        print(f"\n✗ Order FAILED – {exc}")
        sys.exit(1)

    # --- Print response -----------------------------------------------------
    print(format_order_response(response))
    print("✓ Order placed successfully!\n")


if __name__ == "__main__":
    main()
