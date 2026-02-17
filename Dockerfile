# Backend Dockerfile -- Python 3.12 slim
# Multi-purpose: FastAPI + uvicorn serving the agentic search API

FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required by PyMuPDF (fitz)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libmupdf-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml first for layer caching
COPY pyproject.toml ./

# Create minimal src/ stub so hatchling can build the wheel
# (hatchling requires the package directory listed in [tool.hatch.build.targets.wheel])
RUN mkdir -p src && touch src/__init__.py

# Install Python dependencies (hatchling build system)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy real source code (overwrites stub)
COPY src/ ./src/

# Reinstall package with real source (no-deps: deps already cached above)
RUN pip install --no-cache-dir --no-deps .

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8002

# Health check -- hit the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Entry point
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8002"]
