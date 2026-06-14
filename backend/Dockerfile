# ===== Multi-Agent Data Platform — Backend Dockerfile =====
FROM python:3.12-slim

WORKDIR /app

# UTF-8 locale — prevents encoding issues in Docker
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUNBUFFERED=1

# Install system dependencies for matplotlib & cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories (mounted as volumes at runtime)
RUN mkdir -p /app/exports /app/session_data

# Create non-root user for security
RUN useradd -m -s /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
