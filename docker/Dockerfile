# Multi-stage build for Astro Planner
FROM python:3.11-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt .
COPY backend/requirements-test.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-test.txt

# Copy application code
COPY backend/app ./app
COPY backend/tests ./tests
COPY backend/scripts ./scripts
COPY backend/pytest.ini ./pytest.ini
COPY frontend ./frontend

# Create data directory and import catalog
RUN mkdir -p /app/data
RUN python scripts/import_catalog.py --database /app/data/catalogs.db

# Expose port
EXPOSE 9247

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=9247

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9247"]
