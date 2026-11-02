# ── Stage 1: Build React / Vite Frontend ──────────────────────────────────────
FROM node:22-slim AS frontend-builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --registry=https://registry.npmmirror.com || npm ci

COPY index.html vite.config.js ./
COPY public/ ./public/
COPY src/ ./src/
RUN npm run build

# ── Stage 2: Python Runtime + Pre-compressed Cloud Server (0.0.0.0:7860) ──────
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=7860

WORKDIR /home/user/app

COPY backend/requirements-lock.txt ./backend/requirements-lock.txt
RUN pip install --no-cache-dir -r backend/requirements-lock.txt \
        -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com \
    || pip install --no-cache-dir -r backend/requirements-lock.txt

COPY backend/ ./backend/
COPY data/ ./data/
COPY app.py README.md DATA_SOURCES.md NOTICE.md ./
COPY --from=frontend-builder /app/dist ./dist

RUN mkdir -p /tmp/round-observatory-visitors && chmod -R 777 /tmp/round-observatory-visitors

EXPOSE 7860

CMD ["python", "-u", "app.py"]
