# Binance Futures Testnet — Trading Bot

A Python trading bot for placing **Market** and **Limit** orders on the
[Binance Futures Testnet (USDT-M)](https://testnet.binancefuture.com).
Includes both a **CLI** and a **browser-based dashboard**.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Project Structure](#project-structure)
3. [Prerequisites](#prerequisites)
4. [Setup](#setup)
5. [Running — CLI](#running--cli)
6. [Running — Web UI](#running--web-ui)
7. [Running — Docker](#running--docker)
8. [API Reference (Web)](#api-reference-web)
9. [Logging](#logging)
10. [Testing & Validation](#testing--validation)
11. [Troubleshooting](#troubleshooting)
12. [Design Decisions & Assumptions](#design-decisions--assumptions)

---

## Architecture

```
┌───────────┐      ┌───────────────┐
│  CLI      │─────▶│               │
│ (cli.py)  │      │  bot/         │      ┌─────────────────────┐
└───────────┘      │  ├ validators │─────▶│  Binance Futures    │
                   │  ├ orders     │      │  Testnet REST API   │
┌───────────┐      │  └ client     │◀────▶│  (demo-fapi)        │
│  Web UI   │─────▶│               │      └─────────────────────┘
│(web_app)  │      │  logging_     │
└───────────┘      │  config       │──▶  logs/trading_bot.log
                   └───────────────┘
```

| Layer | File | Responsibility |
|-------|------|----------------|
| **Client** | `bot/client.py` | HMAC-SHA256 auth, HTTP dispatch, error mapping |
| **Validators** | `bot/validators.py` | Input sanitisation (`symbol`, `side`, `type`, `qty`, `price`) |
| **Orders** | `bot/orders.py` | Builds order params, delegates to client, formats response |
| **Logging** | `bot/logging_config.py` | Rotating file handler (5 MB × 5 backups) + console |
| **CLI** | `cli.py` | `argparse` entry point, human-readable output |
| **Web** | `web_app.py` + `templates/index.html` | Flask API + single-page dashboard |

All layers are **independently importable**. The web UI and CLI both
reuse the same `bot/` package — zero code duplication.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py           # Package exports (BinanceFuturesClient, etc.)
│   ├── client.py             # Low-level Binance REST client (HMAC-SHA256 auth)
│   ├── orders.py             # Order-placement logic & response formatting
│   ├── validators.py         # Input validation (raises ValueError)
│   └── logging_config.py     # Dual logging (console + rotating file)
├── templates/
│   └── index.html            # Single-page Binance-style trading dashboard
├── cli.py                    # CLI entry point (argparse)
├── web_app.py                # Flask web UI entry point
├── logs/                     # Auto-created; rotating log files
├── .env.example              # Template for API credentials
├── .gitignore
├── .dockerignore             # Files excluded from Docker build context
├── Dockerfile                # Multi-stage production image
├── docker-compose.yml        # One-command container orchestration
├── requirements.txt
└── README.md                 # ← you are here
```

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python      | 3.8 +   | Not needed if using Docker |
| pip         | any     | Not needed if using Docker |
| Docker      | 20.10+  | Optional — for containerised deployment |
| Docker Compose | v2+  | Optional — bundled with Docker Desktop |

You also need a **Binance Futures Testnet** API key:

1. Register at <https://testnet.binancefuture.com>
2. Generate an API key + secret from the dashboard

---

## Setup

```bash
# 1 — Clone / unzip the project

# 2 — Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# 3 — Install dependencies
pip install -r requirements.txt

# 4 — Configure API credentials
cp .env.example .env
# Open .env and paste your testnet API key & secret
```

---

## Running — CLI

### Market order (BUY)

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Limit order (SELL)

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 90000
```

### Full CLI help

```bash
python cli.py --help
```

**Example output:**

```
─── Order Request Summary ────────────────────
  Symbol   : BTCUSDT
  Side     : BUY
  Type     : MARKET
  Quantity : 0.01
───────────────────────────────────────────────

INFO     | Placing BUY MARKET order: 0.01 BTCUSDT @ MARKET
INFO     | Order placed  – orderId=123456789 status=FILLED

─── Order Response ───────────────────────────
  Order ID      : 123456789
  Symbol        : BTCUSDT
  Side          : BUY
  Type          : MARKET
  Status        : FILLED
  Orig Qty      : 0.010
  Executed Qty  : 0.010
  Avg Price     : 68241.50000
  Price         : 0
  Time In Force : GTC
───────────────────────────────────────────────
✓ Order placed successfully!
```

---

## Running — Web UI

```bash
python web_app.py                # default: http://127.0.0.1:5000
python web_app.py --port 8080    # custom port
python web_app.py --host 0.0.0.0 # listen on all interfaces
```

Set `FLASK_DEBUG=1` in `.env` (or as an env var) to enable the Flask
reloader during development — **never use this on a public network**.

### Dashboard features

- **Live ticker bar** — price, 24 h change, high / low, volume
- **Order form** — buy/sell tabs, market/limit toggle, quantity % buttons
- **Inline field validation** with animated feedback
- **Confirmation modal** before every order
- **Account strip** — wallet balance, unrealised PnL, margin, available
- **Tabbed panels** — Positions (with PnL), Open Orders (with cancel),
  Order History (with status badges)
- **Toast notifications** — success / error / info
- Auto-refresh every 5 s

---

## Running — Docker

The project includes a multi-stage `Dockerfile` and a `docker-compose.yml`
for one-command setup.

### Quick start (Docker Compose)

```bash
# 1 — Configure credentials
cp .env.example .env
# Edit .env with your testnet API key & secret

# 2 — Build and start
docker compose up --build

# Dashboard is now at http://localhost:5000
```

### Docker Compose commands

```bash
docker compose up -d            # start in background
docker compose logs -f          # follow logs
docker compose down             # stop and remove container
docker compose down -v          # also remove log volume
```

### Standalone Docker (without Compose)

```bash
# Build
docker build -t trading-bot .

# Run
docker run -d --name trading-bot \
  -p 5000:5000 \
  --env-file .env \
  trading-bot

# CLI mode (one-off order)
docker run --rm --env-file .env trading-bot \
  python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Customise the port

Set `FLASK_PORT` in `.env` to expose a different host port:

```dotenv
FLASK_PORT=8080
```

Then `docker compose up` will map `localhost:8080 → container:5000`.

### Image details

- **Base:** `python:3.11-slim` (multi-stage — build deps stay out of final image)
- **Runs as:** non-root `botuser`
- **Health check:** `GET /api/status` every 30 s
- **Logs:** persisted via a Docker volume (`bot-logs`)

---

## API Reference (Web)

All JSON responses use the envelope `{ "success": bool, "data": ... }`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/status` | Health check (pings Binance) |
| `GET` | `/api/ticker/<symbol>` | 24 h ticker stats |
| `GET` | `/api/klines/<symbol>?interval=1h&limit=50` | Candlestick data |
| `GET` | `/api/account` | Wallet balances & margin |
| `GET` | `/api/positions` | Non-zero positions |
| `GET` | `/api/open-orders` | Open orders (optional `?symbol=`) |
| `GET` | `/api/orders` | In-memory order history (session) |
| `POST` | `/api/order` | Place order `{ symbol, side, order_type, quantity, price? }` |
| `POST` | `/api/cancel-order` | Cancel order `{ symbol, orderId }` |

**Error codes:**

| HTTP | Meaning |
|------|---------|
| 200 | Success |
| 400 | Validation error (bad input) |
| 502 | Binance API returned an error |
| 500 | Unexpected server error |

---

## Logging

Log output goes to **two destinations**:

| Destination | Level | Detail |
|-------------|-------|--------|
| **Console** (`stderr`) | INFO | One-line summaries |
| **File** (`logs/trading_bot.log`) | DEBUG | Full timestamps, module + line numbers |

Files rotate automatically at **5 MB** and keep **5 backups**, so the
`logs/` directory stays bounded.

**What is logged:**

- `DEBUG` — API request paths and parameters (signatures redacted)
- `INFO` — Order summaries, client initialisation
- `WARNING` — Validation failures from the web UI
- `ERROR` — Binance API errors, network failures (with traceback)

---

## Testing & Validation

### Quick smoke test (CLI)

```bash
# Should print help and exit 0
python cli.py --help

# Should fail with a clear validation error (no API call made)
python cli.py --symbol btcusdt --side BUY --type LIMIT --quantity 0.01
# → "Validation error: Price is required for LIMIT orders."
```

### Quick smoke test (Web)

```bash
python web_app.py --port 5001 &

# Health check
curl -s http://127.0.0.1:5001/api/status

# Ticker
curl -s http://127.0.0.1:5001/api/ticker/BTCUSDT

# Account
curl -s http://127.0.0.1:5001/api/account
```

### Validator unit tests (manual)

The validators are pure functions with no side effects, easy to test:

```python
from bot.validators import validate_all

# Valid market order
params = validate_all("btcusdt", "buy", "market", "0.01", None)
assert params["symbol"] == "BTCUSDT"
assert params["price"] is None

# Missing price for limit order → raises ValueError
try:
    validate_all("BTCUSDT", "BUY", "LIMIT", "0.01", None)
except ValueError as e:
    assert "required" in str(e).lower()
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `Missing API credentials` | `.env` not found or keys empty | Run `cp .env.example .env` and fill in keys |
| `Binance error -1121: Invalid symbol` | Symbol doesn't exist on testnet | Use an active pair like `BTCUSDT`, `ETHUSDT` |
| `Binance error -4131: … PERCENT_PRICE` | Limit price too far from market | Adjust the price closer to the current market price |
| `Binance error -1111: … LOT_SIZE` | Quantity violates `stepSize` filter | Check the symbol's `stepSize` at `/fapi/v1/exchangeInfo` |
| `Connection refused` on web UI | Server not running or wrong port | Ensure `python web_app.py --port <PORT>` is running |
| `ModuleNotFoundError: No module named 'flask'` | Dependencies not installed | Run `pip install -r requirements.txt` |

```