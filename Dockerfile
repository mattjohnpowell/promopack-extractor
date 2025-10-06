FROM python:3.12-slim

# Force cache invalidation (change this value to force rebuild)
ARG CACHEBUST=1

# Install system dependencies for PDF processing and OCR
RUN apt-get update && apt-get install -y \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && mkdir -p /app \
    && chown -R app:app /app

USER app
WORKDIR /app

# Copy requirements first for better caching
COPY --chown=app:app requirements.txt ./

# Install Python dependencies
# NOTE: Reverting to working version (commit 65c6246) without spacy
# spacy was causing build timeouts and is not needed for production deployment
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application code
COPY --chown=app:app . .

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Environment variables
ENV LOG_TO_FILE=false \
    ENV=prod \
    PATH="/home/app/.local/bin:$PATH"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]