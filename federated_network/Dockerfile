# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# System deps for cryptography wheel
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root user for security
RUN useradd --create-home --shell /bin/bash fednet
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . /app/services/federated_network

# Secrets dir — mounted at runtime via Kubernetes secret or Docker secret
RUN mkdir -p /run/secrets && chown fednet:fednet /run/secrets

USER fednet

# Health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8100/fednet/v1/health')"

EXPOSE 8100

CMD ["uvicorn", "services.federated_network.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8100", \
     "--workers", "2", \
     "--log-level", "info", \
     "--no-access-log"]
