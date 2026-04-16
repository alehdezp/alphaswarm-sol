# AlphaSwarm.sol Docker Image
# Multi-stage build for minimal image size
#
# Usage:
#   docker build -t alphaswarm-sol:0.5.0 .
#   docker run --rm alphaswarm-sol:0.5.0 --help
#   docker run --rm -v ./contracts:/workspace alphaswarm-sol:0.5.0 build-kg /workspace

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.11-slim-bookworm AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set up working directory
WORKDIR /app

# Copy dependency files first (better layer caching)
COPY pyproject.toml uv.lock README.md ./

# Copy source code (needed for uv sync to install the package)
COPY src/ ./src/
COPY patterns/ ./patterns/
COPY vulndocs/ ./vulndocs/
COPY schemas/ ./schemas/

# Create virtual environment and install dependencies
RUN uv sync --frozen --no-dev \
    && chmod -R a+rX /app

# =============================================================================
# Stage 2: Runtime (CLI)
# =============================================================================
FROM python:3.11-slim-bookworm AS runtime

# OCI Labels
LABEL org.opencontainers.image.title="AlphaSwarm.sol"
LABEL org.opencontainers.image.description="AI-native smart contract security analysis powered by behavioral knowledge graphs"
LABEL org.opencontainers.image.version="0.5.0"
LABEL org.opencontainers.image.source="https://github.com/alphaswarm/alphaswarm-sol"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.vendor="AlphaSwarm"

# Install runtime dependencies and solc-select in single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir solc-select \
    && solc-select install 0.8.20 \
    && solc-select use 0.8.20

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash alphaswarm \
    && mkdir -p /workspace \
    && chown -R alphaswarm:alphaswarm /workspace

# Copy virtual environment from builder (already has correct permissions)
COPY --from=builder /app/.venv /app/.venv

# Copy application code and data
WORKDIR /app
COPY --from=builder /app/src ./src
COPY --from=builder /app/patterns ./patterns
COPY --from=builder /app/vulndocs ./vulndocs
COPY --from=builder /app/schemas ./schemas
COPY --from=builder /app/pyproject.toml ./

# Set up PATH to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"

USER alphaswarm

# Set working directory for analysis
WORKDIR /workspace

# Expose volume for contracts
VOLUME ["/workspace"]

# Entry point to AlphaSwarm CLI
ENTRYPOINT ["alphaswarm"]
CMD ["--help"]

# =============================================================================
# Stage 3: Development (optional, for testing)
# Build with: docker build --target development -t alphaswarm-sol:dev .
# Note: Requires tests/ directory - either mount it or exclude tests/ from .dockerignore
# =============================================================================
FROM runtime AS development

# Switch to root for dev dependency installation
USER root

# Install development dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-xdist

# Tests should be mounted at runtime:
# docker run -v ./tests:/app/tests alphaswarm-sol:dev pytest /app/tests/

WORKDIR /app

# Switch back to non-root user
USER alphaswarm

# Override entrypoint for development
ENTRYPOINT ["/bin/bash"]
