# ============================================================================
# CPU-deploy (t.ex. Render). Multi-stage: Node bygger frontenden, Python kör
# backenden. Ingen GPU, ingen torch, ingen Kodytek – syntetiska warp-brädor i 3D.
# ============================================================================

# --- 1. bygg frontenden ---
FROM node:20-slim AS frontend
WORKDIR /app/web/frontend
COPY web/frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY web/frontend/ ./
RUN npm run build

# --- 2. python-runtime ---
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 WOODY_KODYTEK_ROOT="" WOODY_CKPT="seg_unet.pt"
COPY requirements-deploy.txt ./
RUN pip install --no-cache-dir -r requirements-deploy.txt
COPY src/ ./src/
COPY web/ ./web/
COPY --from=frontend /app/web/frontend/dist ./web/frontend/dist
EXPOSE 8000
# Render sätter $PORT
CMD ["sh", "-c", "uvicorn web.backend.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
