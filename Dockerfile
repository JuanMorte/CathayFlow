# Backend image: FastAPI + the built frontend (AGENTS.md §8.5). Built for linux/arm64.
FROM python:3.12-slim

ENV FLOW_REPO_ROOT=/app \
    FLOW_SKIP_DOTENV=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Exact versions from uv.lock (`make lock-backend` writes this file).
COPY backend/requirements.lock ./requirements.lock
RUN pip install -r requirements.lock

COPY flowcore ./flowcore
RUN pip install --no-deps ./flowcore

# app/ includes static/ when `make build-web` has run.
COPY backend/app ./app
COPY config ./config
COPY data ./data

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
