# ── Base: shared deps ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY train.py app.py ./

# ── Trainer: run once to produce artifacts ─────────────────────────────────────
FROM base AS trainer
ENV ARTIFACTS_DIR=artifacts
CMD ["python", "train.py"]

# ── Server: serve the trained model via API ────────────────────────────────────
FROM base AS server
ENV ARTIFACTS_DIR=artifacts
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
