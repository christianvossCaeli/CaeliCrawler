# =============================================================================
# Backend Dockerfile - Multi-Stage Build for Performance
# =============================================================================
# This Dockerfile uses multi-stage builds to:
# - Reduce final image size by excluding build dependencies
# - Improve security by minimizing attack surface
# - Speed up deployments with smaller images
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies and build wheels
# -----------------------------------------------------------------------------
FROM python:3.13-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install Python dependencies and create wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# -----------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

# OCI Image Labels (https://github.com/opencontainers/image-spec/blob/main/annotations.md)
LABEL org.opencontainers.image.title="CaeliCrawler Backend"
LABEL org.opencontainers.image.description="FastAPI backend for CaeliCrawler municipal data platform"
LABEL org.opencontainers.image.vendor="CaeliCrawler"
LABEL org.opencontainers.image.licenses="Proprietary"
LABEL org.opencontainers.image.source="https://github.com/caelichrawler/caelichrawler"
LABEL org.opencontainers.image.base.name="python:3.13-slim"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install only runtime dependencies (no build tools)
# Note: WeasyPrint requires pango, fontconfig, and related libraries for PDF generation
# Note: Playwright requires additional browser dependencies for map screenshots in PDF export
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu-core \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Set Playwright browser path to shared location
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

WORKDIR /app

# Install Python packages from pre-built wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Install Playwright browsers in shared location accessible to appuser
RUN pip install --no-cache-dir playwright && \
    playwright install chromium && \
    chmod -R 755 /opt/playwright

# Copy application code
COPY --chown=appuser:appuser . .

# Create storage directory
RUN mkdir -p /app/storage/documents && \
    chown -R appuser:appuser /app/storage

# Expose port
EXPOSE 8000

# Switch to non-root user
USER appuser

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# -----------------------------------------------------------------------------
# Stage 3: Crawler - Runtime image with Playwright for crawling
# -----------------------------------------------------------------------------
FROM runtime AS crawler

# Switch back to root for installing Playwright
USER root

# Install Playwright dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright and browsers
RUN pip install --no-cache-dir playwright && \
    playwright install chromium

# Switch back to non-root user
USER appuser

# Default command for crawler worker
CMD ["celery", "-A", "workers.celery_app", "worker", "--loglevel=info", "-Q", "crawl"]
