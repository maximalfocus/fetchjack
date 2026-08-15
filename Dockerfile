# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install --no-cache-dir uv

WORKDIR /app

# Install dependencies first for better layer caching. hatchling reads README.md,
# so it is copied alongside the project metadata.
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv pip install --system --no-cache ".[dev]"

# Copy the remaining sources: tests, the fictional local fixture secret at
# /app/secrets/preview_worker.env, and the tooling configuration.
COPY . .
