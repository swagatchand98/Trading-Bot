"""
bot — Core modules for the Binance Futures Testnet trading bot.

Submodules
----------
client          Low-level REST client with HMAC-SHA256 authentication.
orders          Order-placement logic and response formatting.
validators      Input validation for CLI / web parameters.
logging_config  Dual-output logging (console + rotating file).
"""

from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.orders import place_order, format_order_response
from bot.validators import validate_all

__all__ = [
    "BinanceFuturesClient",
    "BinanceAPIError",
    "place_order",
    "format_order_response",
    "validate_all",
]
