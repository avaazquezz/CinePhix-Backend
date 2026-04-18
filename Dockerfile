# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies (README + app are required for hatchling metadata and editable install)
COPY pyproject.toml README.md ./
COPY app ./app/
COPY alembic.ini ./
COPY migrations ./migrations/
COPY scripts ./scripts/
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh && pip install --no-cache-dir --user -e .

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder (to user-accessible location)
COPY --from=builder /root/.local /home/appuser/.local
COPY --from=builder /app /app

# Add Python to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /home/appuser/.local /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Apply DB migrations then start API
CMD ["/app/docker-entrypoint.sh"]