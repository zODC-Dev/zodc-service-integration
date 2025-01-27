# STAGE 1: BUILD STAGE
FROM python:3.12-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.8.5

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock* /app/

# Install project dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --without dev

# Copy src files
COPY src /app/src
COPY alembic.ini /app/
COPY alembic_migrations /app/alembic_migrations

# STAGE 2: RUNTIME STAGE
FROM python:3.12-slim

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY --from=builder /app /app
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Create logs and secrets directories
RUN mkdir -p /app/logs /app/secrets

# Set working directory
WORKDIR /app

# Create an entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose port
EXPOSE 8001

# Run migrations and start the application
ENTRYPOINT ["/docker-entrypoint.sh"]
