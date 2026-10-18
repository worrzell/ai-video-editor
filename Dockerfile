# Multi-stage Dockerfile for AI Video Editor Backend
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies: FFmpeg and PostgreSQL client libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency requirements
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt psycopg[binary]

# Copy application source code
COPY backend ./backend
COPY pyproject.toml .

# Create data directories
RUN mkdir -p data/clips data/transcripts data/outputs

EXPOSE 8000

ENV HOST=0.0.0.0
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "backend.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
