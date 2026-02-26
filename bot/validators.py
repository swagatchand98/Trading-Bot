"""
Input validators for trading-bot CLI parameters.

Every public function raises ``ValueError`` with a human-readable message
when validation fails.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional, Union

# Binance Futures symbols are uppercase alphanumeric (e.g. BTCUSDT, ETHUSDT).
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,20}$")

VALID_SIDES = ("BUY", "SELL")
VALID_ORDER_TYPES = ("MARKET", "LIMIT")


def validate_symbol(symbol: str) -> str:
    """Return the uppercased symbol or raise on invalid format."""
    symbol = symbol.strip().upper()
    if not _SYMBOL_RE.match(symbol):
        raise ValueError(
            f"Invalid symbol '{symbol}'. "
            "Expected uppercase alphanumeric (e.g. BTCUSDT)."
        )
    return symbol


def validate_side(side: str) -> str:
    """Return the uppercased side or raise if not BUY/SELL."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(VALID_SIDES)}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Return the uppercased order type or raise if unsupported."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(VALID_ORDER_TYPES)}."
        )
    return order_type


def validate_quantity(quantity: Union[str, float]) -> Decimal:
    """
    Return a positive ``Decimal`` quantity or raise.

    Raises
    ------
    ValueError
        If *quantity* is not a valid positive number.
    """
    try:
        qty = Decimal(str(quantity))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid quantity '{quantity}'. Must be a positive number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be positive, got {qty}.")
    return qty


def validate_price(price: Union[str, float, None], order_type: str) -> Optional[Decimal]:
    """
    Validate *price* given an *order_type*.

    - For LIMIT orders, price is **required** and must be positive.
    - For MARKET orders, price is ignored (returns ``None``).

    Raises
    ------
    ValueError
        If *price* is missing or invalid for a LIMIT order.
    """
    if order_type == "MARKET":
        return None

    if price is None:
        raise ValueError("Price is required for LIMIT orders.")

    try:
        p = Decimal(str(price))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid price '{price}'. Must be a positive number.")
    if p <= 0:
        raise ValueError(f"Price must be positive, got {p}.")
    return p


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: Union[str, float],
    price: Union[str, float, None],
) -> dict:
    """
    Run every validator and return a clean parameter dict.

    Returns
    -------
    dict
        Keys: ``symbol``, ``side``, ``order_type``, ``quantity``, ``price``.

    Raises
    ------
    ValueError
        If any individual parameter is invalid.
    """
    v_symbol = validate_symbol(symbol)
    v_side = validate_side(side)
    v_type = validate_order_type(order_type)
    v_qty = validate_quantity(quantity)
    v_price = validate_price(price, v_type)

    return {
        "symbol": v_symbol,
        "side": v_side,
        "order_type": v_type,
        "quantity": v_qty,
        "price": v_price,
    }
