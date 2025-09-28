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
COPY ./pyproject.toml /app/pyproject.toml
COPY ./poetry.lock /app/poetry.lock
COPY ./libs /app/libs
COPY ./workflows /app/workflows

# Install shared libraries and service dependencies using poetry
RUN cd /app && poetry install --no-root --no-directory --sync

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser

# Run the application
CMD ["python", "workflows/worker.py"]

