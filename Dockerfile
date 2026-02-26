# ── Stage 1: build dependencies ───────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime image ────────────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="swagatchand98"
LABEL description="Binance Futures Testnet Trading Bot"

# Non-root user for security
RUN groupadd -r botuser && useradd -r -g botuser -d /app -s /sbin/nologin botuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY bot/ bot/
COPY templates/ templates/
COPY cli.py web_app.py requirements.txt ./

# Create logs directory owned by botuser
RUN mkdir -p /app/logs && chown -R botuser:botuser /app

USER botuser

# Web UI port
EXPOSE 5000

# Health check — pings the /api/status endpoint every 30 s
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/status')" || exit 1

# Default: start the web UI (override with CLI args if needed)
ENTRYPOINT ["python", "web_app.py"]
CMD ["--host", "0.0.0.0", "--port", "5000"]
