# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS frontend-builder
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN python -m pip install --upgrade pip \
    && python -m pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.1" \
    && python -m pip install .

COPY configs/ ./configs/
COPY data/demo/ ./data/demo/
COPY artifacts/demo/ ./artifacts/demo/
COPY --from=frontend-builder /build/frontend/dist/ ./frontend/dist/
RUN mkdir -p data/raw artifacts/web-configs artifacts/web-runs

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=12 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5)" || exit 1
CMD ["python", "-m", "uvicorn", "changchun_air.web_api:app", "--host", "0.0.0.0", "--port", "8000"]
