# Processing Worker Dockerfile with GPU support
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Install Python 3.11
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements
COPY backend/requirements-processing.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements-processing.txt

# Copy processing code
COPY backend/app /app/backend/app

# Create processing user (non-root for security)
RUN useradd -m -u 1000 processor && \
    chown -R processor:processor /app && \
    mkdir -p /job && \
    chown -R processor:processor /job

USER processor

# Entry point for processing jobs
ENTRYPOINT ["python3.11", "-m", "backend.app.processing.runner"]
