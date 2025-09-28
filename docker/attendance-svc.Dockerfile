FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install system dependencies and Poetry
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && pip install poetry \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire monorepo into the container
COPY ../../pyproject.toml /app/pyproject.toml
COPY ../../poetry.lock /app/poetry.lock
COPY ../../libs /app/libs
COPY services/attendance-svc /app/services/attendance-svc

# Install shared libraries and service dependencies using poetry
RUN cd /app && poetry install --no-root --no-directory --sync

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]

