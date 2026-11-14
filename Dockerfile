# Chatbook: one image that serves the API and the built frontend on port 8000.
# This file has not been built in the environment it was written in; see README "Docker".

# ---- 1. build the frontend ----
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- 2. backend runtime ----
# The Playwright image already contains Chromium. Its version must match playwright in requirements.txt.
FROM mcr.microsoft.com/playwright/python:v1.56.0-noble
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg fonts-noto-core fonts-noto-color-emoji \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt "playwright==1.56.0"
COPY backend/app ./app
COPY --from=web /web/dist /app/frontend/dist

# Chromium runs as root here, so it needs --no-sandbox. Only upload files you trust.
ENV CHATBOOK_DATA_DIR=/data \
    CHATBOOK_STATIC_DIR=/app/frontend/dist \
    CHATBOOK_CHROMIUM_NO_SANDBOX=1 \
    PYTHONUNBUFFERED=1
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').status==200 else 1)"

# One worker on purpose: exports run one at a time in this process.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
