# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies (README + app are required for hatchling metadata and editable install)
COPY pyproject.toml README.md ./
COPY app ./app/
RUN pip install --no-cache-dir --user -e .
RUN pip install --no-cache-dir --user stripe

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
    chown -R appuser:appuser /home/appuser/.local
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Run with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]