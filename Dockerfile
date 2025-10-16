# Multi-stage build for optimal security and size
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code only (NO credentials!)
COPY server.py config.py youtube_client.py ./
COPY utils/ ./utils/
COPY auth/ ./auth/
COPY playlist/ ./playlist/
COPY captions/ ./captions/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /app/cache /app/logs && \
    chown -R appuser:appuser /app/cache /app/logs

# Switch to non-root user
USER appuser

# Environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MCP_TRANSPORT=http \
    PORT=8080 \
    PATH=/root/.local/bin:$PATH \
    CACHE_ENABLED=true \
    RATE_LIMIT_ENABLED=true

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()" || exit 1

# Expose port
EXPOSE 8080

# Run server
CMD ["python", "server.py"]
