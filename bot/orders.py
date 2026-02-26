"""
Order-placement logic.

Bridges validated user input and the low-level ``BinanceFuturesClient``.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from .client import BinanceFuturesClient

logger = logging.getLogger("trading_bot")


def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal] = None,
) -> Dict[str, Any]:
    """
    Build the parameter dict and forward to ``client.place_order``.

    Parameters
    ----------
    client : BinanceFuturesClient
        Authenticated API client.
    symbol, side, order_type, quantity, price
        Already-validated trading parameters.

    Returns
    -------
    dict
        Raw order response from Binance.
    """
    params: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": str(quantity),
    }

    if order_type == "LIMIT":
        params["price"] = str(price)
        params["timeInForce"] = "GTC"  # Good-Til-Cancelled

    logger.info(
        "Placing %s %s order: %s %s @ %s",
        side,
        order_type,
        quantity,
        symbol,
        price if price else "MARKET",
    )

    response = client.place_order(**params)

    logger.info("Order placed  – orderId=%s status=%s", response.get("orderId"), response.get("status"))
    logger.debug("Full order response: %s", response)

    return response


def format_order_response(response: Dict[str, Any]) -> str:
    """
    Return a human-friendly multi-line summary of an order response.

    Extracts the most useful fields and formats them for CLI output.
    """
    lines = [
        "─── Order Response ───────────────────────────",
        f"  Order ID      : {response.get('orderId')}",
        f"  Symbol        : {response.get('symbol')}",
        f"  Side          : {response.get('side')}",
        f"  Type          : {response.get('type')}",
        f"  Status        : {response.get('status')}",
        f"  Orig Qty      : {response.get('origQty')}",
        f"  Executed Qty  : {response.get('executedQty')}",
        f"  Avg Price     : {response.get('avgPrice', 'N/A')}",
        f"  Price         : {response.get('price', 'N/A')}",
        f"  Time In Force : {response.get('timeInForce', 'N/A')}",
        "───────────────────────────────────────────────",
    ]
    return "\n".join(lines)
