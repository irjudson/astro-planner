# Multi-stage build for Astro Planner
FROM python:3.11-bullseye AS base

# Set working directory
WORKDIR /app

# Install system dependencies including Docker CLI
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    libgomp1 \
    ca-certificates \
    gnupg \
    lsb-release \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt .
COPY backend/requirements-test.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --force-reinstall -r requirements.txt
RUN pip install --no-cache-dir --force-reinstall -r requirements-test.txt

# Copy application code
COPY backend/app ./app
COPY backend/tests ./tests
COPY backend/scripts ./scripts
COPY backend/pytest.ini ./pytest.ini
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic
COPY frontend ./frontend

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create data directory (database will be initialized at runtime)
RUN mkdir -p /app/data

# Expose port
EXPOSE 9247

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=9247

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:9247/api/health || exit 1

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9247"]
