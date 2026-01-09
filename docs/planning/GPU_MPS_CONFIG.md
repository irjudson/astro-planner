# GPU and MPS Configuration

This document describes the NVIDIA GPU and Multi-Process Service (MPS) configuration for the astronomus worker container.

## Overview

The Celery worker container (`astronomus-worker`) is configured to use NVIDIA GPU acceleration with MPS for efficient GPU sharing. This allows multiple Celery worker processes to share the GPU simultaneously, improving throughput for parallel processing tasks like image stacking.

## Hardware

- **GPU**: NVIDIA GeForce RTX 5060 Ti (16GB)
- **Compute Capability**: 12.0 (Blackwell architecture)
- **CUDA Version**: 12.8.0
- **Driver Version**: 580.95.05

## MPS Configuration

### What is MPS?

NVIDIA Multi-Process Service (MPS) allows multiple CUDA applications to share a single GPU context, providing better GPU utilization and reduced memory overhead when running multiple processes.

### Host Configuration

MPS must be running on the host system:

```bash
# Check if MPS is running
ps aux | grep nvidia-cuda-mps

# Expected output:
# nvidia-cuda-mps-control -d
# nvidia-cuda-mps-server
```

MPS directory structure:
```bash
/tmp/nvidia-mps/
├── control              # MPS control socket
├── control_lock         # Control lock file
├── control_privileged   # Privileged control socket
├── log                  # MPS log pipe
└── nvidia-cuda-mps-control.pid
```

### Docker Container Configuration

The worker container is configured with:

```yaml
celery-worker:
  runtime: nvidia
  environment:
    - NVIDIA_VISIBLE_DEVICES=all
    - NVIDIA_DRIVER_CAPABILITIES=compute,utility
    - CUDA_MPS_PIPE_DIRECTORY=/tmp/nvidia-mps
    - CUDA_MPS_LOG_DIRECTORY=/tmp/nvidia-mps
  volumes:
    - /tmp/nvidia-mps:/tmp/nvidia-mps
```

**Key Configuration:**

1. **runtime: nvidia** - Enables NVIDIA Container Runtime
2. **NVIDIA_VISIBLE_DEVICES=all** - Makes all GPUs visible to container
3. **NVIDIA_DRIVER_CAPABILITIES** - Enables compute and utility capabilities
4. **CUDA_MPS_PIPE_DIRECTORY** - Points to MPS control socket directory
5. **CUDA_MPS_LOG_DIRECTORY** - MPS logging directory
6. **Volume mount** - Shares MPS socket from host

## CuPy GPU Acceleration

The stacking service uses CuPy for GPU-accelerated array operations:

```python
from app.services.stacking_service import StackingService

# Enable GPU acceleration
service = StackingService(use_gpu=True)

# Stack frames
result = service.stack_folder(folder_path, sigma=2.5)
```

**CuPy Features Used:**
- Sigma-clipped mean stacking
- Array operations (mean, std, abs)
- Masked array operations
- GPU memory pooling

## Verification

### Verify MPS is Running

```bash
# From host
echo "get_server_list" | CUDA_MPS_PIPE_DIRECTORY=/tmp/nvidia-mps nvidia-cuda-mps-control

# Expected: PID of MPS server
```

### Verify Worker GPU Access

```bash
# Check GPU access
docker exec astronomus-worker nvidia-smi

# Test CuPy
docker exec astronomus-worker python3 -c "
import cupy as cp
print(f'CUDA available: {cp.cuda.is_available()}')
print(f'Device count: {cp.cuda.runtime.getDeviceCount()}')
"
```

### Test Stacking Service

```bash
# Test GPU-enabled stacking
docker exec astronomus-worker python3 -c "
from app.services.stacking_service import StackingService

service = StackingService(use_gpu=True)
print(f'GPU enabled: {service.use_gpu}')
"
```

## Performance Benefits

### With MPS

- **GPU Sharing**: Multiple Celery workers can use GPU simultaneously
- **Lower Overhead**: Shared GPU context reduces memory overhead
- **Better Utilization**: GPU is used more efficiently across processes

### Without MPS

- **Serial Access**: Only one process can use GPU at a time
- **Higher Overhead**: Each process creates separate GPU context
- **Underutilization**: GPU may be idle while waiting for exclusive access

## GPU Memory Management

The stacking service automatically manages GPU memory:

```python
# CuPy memory pool
pool = cp.get_default_memory_pool()

# Memory is automatically released after operations
# Pool can be manually cleared if needed:
pool.free_all_blocks()
```

## Fallback to CPU

If GPU is not available, the stacking service automatically falls back to CPU:

```python
service = StackingService(use_gpu=True)

# If CuPy is not available or GPU fails:
# - use_gpu will be set to False
# - All operations use NumPy instead of CuPy
# - No code changes required
```

## Troubleshooting

### MPS Not Running

```bash
# Start MPS control daemon
sudo nvidia-cuda-mps-control -d

# Verify
ps aux | grep nvidia-cuda-mps
```

### GPU Not Accessible in Container

```bash
# Check NVIDIA runtime
docker info | grep -i runtime

# Verify NVIDIA Container Toolkit
nvidia-ctk --version

# Check container GPU access
docker exec astronomus-worker nvidia-smi
```

### CuPy Import Errors

```bash
# Verify CuPy installation
docker exec astronomus-worker python3 -c "import cupy; print(cupy.__version__)"

# Check CUDA version match
docker exec astronomus-worker python3 -c "
import cupy as cp
print(f'CUDA Runtime: {cp.cuda.runtime.runtimeGetVersion()}')
print(f'CUDA Driver: {cp.cuda.runtime.driverGetVersion()}')
"
```

### MPS Pipe Not Found

```bash
# Verify MPS directory is mounted
docker exec astronomus-worker ls -la /tmp/nvidia-mps/

# Check environment variable
docker exec astronomus-worker env | grep CUDA_MPS_PIPE_DIRECTORY
```

## Environment Variables

All CUDA/NVIDIA environment variables in the worker:

```bash
CUDA_MPS_PIPE_DIRECTORY=/tmp/nvidia-mps
CUDA_MPS_LOG_DIRECTORY=/tmp/nvidia-mps
CUDA_VERSION=12.8.0
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility
```

## Docker Compose Reference

Complete worker configuration:

```yaml
celery-worker:
  build:
    context: .
    dockerfile: docker/Dockerfile
  container_name: astronomus-worker
  runtime: nvidia
  command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
  environment:
    - REDIS_URL=redis://:buffalo-jump@redis:6379/1
    - DATABASE_URL=postgresql://pg:buffalo-jump@postgres:5432/astronomus
    - FITS_DIR=/fits
    - NVIDIA_VISIBLE_DEVICES=all
    - NVIDIA_DRIVER_CAPABILITIES=compute,utility
    - CUDA_MPS_PIPE_DIRECTORY=/tmp/nvidia-mps
    - CUDA_MPS_LOG_DIRECTORY=/tmp/nvidia-mps
  volumes:
    - ./data:/app/data
    - /mnt/seestar-s50:/fits:rw
    - /tmp/nvidia-mps:/tmp/nvidia-mps
  restart: unless-stopped
  networks:
    - shared-infra
```

## Related Documentation

- [SEESTAR_PROCESSING.md](SEESTAR_PROCESSING.md) - Image processing pipeline
- [NVIDIA MPS Documentation](https://docs.nvidia.com/deploy/mps/index.html)
- [CuPy Documentation](https://docs.cupy.dev/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/)
