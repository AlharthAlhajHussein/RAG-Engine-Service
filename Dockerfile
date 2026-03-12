# Use a lightweight, official Python image
FROM python:3.13-slim

# Prevent Python from writing .pyc files and buffer outputs for real-time logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install OS-level dependencies required for building psycopg2 and processing PDFs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

# Copy requirements first to leverage Docker layer caching
COPY ./src/requirements.txt .

# 5. Use uv to install dependencies directly into the system Python
RUN uv pip install --system --no-cache -r requirements.txt

# 6. Copy your application source code into the container
COPY src/ .

# Create a non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose the port your FastAPI server runs on
EXPOSE 8000