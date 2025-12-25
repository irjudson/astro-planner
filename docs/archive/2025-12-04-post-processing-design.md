# Post-Processing Workflow Design

**Date:** 2025-12-04
**Status:** Approved

## Goal

Design a full astrophotography post-processing pipeline with pluggable backends, template-based workflows, and GPU acceleration.

## Decisions

| Decision | Choice |
|----------|--------|
| Use case | Full astrophotography pipeline |
| Input sources | Multiple (Seestar direct, folder watch, upload, cloud sync) |
| Processing engine | Pluggable backends, Siril + built-in as default |
| Orchestration | Template-based linear pipelines, customizable |
| Execution | Celery workers with GPU routing when available |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Input Sources                              │
├──────────┬──────────┬──────────┬──────────┬────────────────────┤
│ Seestar  │  Folder  │  Upload  │  Cloud   │                    │
│  Direct  │  Watch   │   API    │  Sync    │                    │
└────┬─────┴────┬─────┴────┬─────┴────┬─────┘                    │
     │          │          │          │                           │
     └──────────┴──────────┴──────────┘                           │
                      │                                            │
                      ▼                                            │
              ┌───────────────┐                                    │
              │  File Ingress │ ← Validate, extract FITS metadata  │
              │    Service    │                                    │
              └───────┬───────┘                                    │
                      │                                            │
                      ▼                                            │
              ┌───────────────┐                                    │
              │   Pipeline    │ ← Select template or custom        │
              │   Selector    │                                    │
              └───────┬───────┘                                    │
                      │                                            │
                      ▼                                            │
              ┌───────────────┐      ┌─────────────────────┐      │
              │    Celery     │──────│   GPU Worker Pool   │      │
              │  Task Queue   │      │  (when available)   │      │
              └───────┬───────┘      └─────────────────────┘      │
                      │                                            │
                      ▼                                            │
              ┌───────────────┐                                    │
              │   Backend     │                                    │
              │   Router      │                                    │
              └───────┬───────┘                                    │
                      │                                            │
        ┌─────────────┼─────────────┐                              │
        ▼             ▼             ▼                              │
   ┌─────────┐  ┌─────────┐  ┌─────────┐                          │
   │  Siril  │  │ Built-in│  │PixInsight│  ← Pluggable backends   │
   │   CLI   │  │ (Python)│  │   CLI   │                          │
   └─────────┘  └─────────┘  └─────────┘                          │
                      │                                            │
                      ▼                                            │
              ┌───────────────┐                                    │
              │    Output     │ ← FITS, TIFF, PNG, JPEG            │
              │   Storage     │                                    │
              └───────────────┘                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Input Sources

### 1. Seestar Direct
- Pull images via Seestar API during/after observation
- Auto-trigger processing when session ends
- Store raw frames + stacked result

### 2. Folder Watch
- Monitor configured directory for new FITS/TIFF files
- Detect file patterns (lights, darks, flats, bias)
- Auto-group by target/filter/date

### 3. Manual Upload
- Web UI file upload
- Drag-and-drop interface
- Bulk upload with ZIP support

### 4. Cloud Sync
- Dropbox, Google Drive, OneDrive integration
- Watch specific folders
- Sync on schedule or on-demand

## Processing Backends

### Backend Interface

```python
class ProcessingBackend(ABC):
    """Abstract base for processing backends."""

    @abstractmethod
    def calibrate(self, lights: List[Path], darks: List[Path],
                  flats: List[Path], bias: List[Path]) -> Path:
        """Apply calibration frames."""
        pass

    @abstractmethod
    def register(self, frames: List[Path]) -> List[Path]:
        """Align/register frames."""
        pass

    @abstractmethod
    def stack(self, frames: List[Path], method: str = "average") -> Path:
        """Stack registered frames."""
        pass

    @abstractmethod
    def stretch(self, image: Path, method: str, params: dict) -> Path:
        """Apply histogram stretch."""
        pass

    @abstractmethod
    def denoise(self, image: Path, strength: float) -> Path:
        """Apply noise reduction."""
        pass

    @property
    @abstractmethod
    def supports_gpu(self) -> bool:
        """Whether this backend can use GPU."""
        pass
```

### Siril Backend (Default)

```python
class SirilBackend(ProcessingBackend):
    """Siril CLI backend - high quality, scriptable."""

    def __init__(self, siril_path: str = "siril-cli"):
        self.siril = siril_path

    def stack(self, frames: List[Path], method: str = "average") -> Path:
        script = self._generate_script(frames, method)
        subprocess.run([self.siril, "-s", script])
        return output_path
```

### Built-in Backend

```python
class BuiltinBackend(ProcessingBackend):
    """Python/NumPy/CuPy backend - fast preview, GPU accelerated."""

    def __init__(self):
        self.use_gpu = gpu_ops.check_gpu_available()["available"]

    def stretch(self, image: Path, method: str, params: dict) -> Path:
        if self.use_gpu:
            return gpu_ops.gpu_histogram_stretch(image, **params)
        return cpu_ops.histogram_stretch(image, **params)
```

## Pipeline Templates

### Template Structure

```python
@dataclass
class PipelineTemplate:
    name: str
    description: str
    steps: List[PipelineStep]
    input_requirements: InputRequirements

@dataclass
class PipelineStep:
    operation: str  # calibrate, register, stack, stretch, denoise, etc.
    backend: str    # siril, builtin, pixinsight, or "default"
    params: dict
    optional: bool = False
```

### Built-in Templates

#### Seestar Quick Process
```yaml
name: Seestar Quick Process
description: Fast processing for Seestar stacked images
steps:
  - operation: stretch
    backend: builtin
    params:
      method: arcsinh
      black_point: 0.001
  - operation: color_balance
    backend: builtin
    params:
      method: auto
  - operation: export
    params:
      formats: [png, jpeg]
```

#### Full Calibration & Stack
```yaml
name: Full Calibration & Stack
description: Complete workflow with calibration frames
steps:
  - operation: calibrate
    backend: siril
    params:
      use_darks: true
      use_flats: true
      use_bias: true
  - operation: register
    backend: siril
    params:
      method: global_star_align
  - operation: stack
    backend: siril
    params:
      method: average
      rejection: winsorized
  - operation: stretch
    backend: builtin
    params:
      method: arcsinh
  - operation: denoise
    backend: builtin
    params:
      strength: 0.5
    optional: true
```

#### Narrowband HOO/SHO
```yaml
name: Narrowband Combine
description: Combine Ha, OIII, SII into color image
steps:
  - operation: channel_align
    backend: siril
  - operation: channel_combine
    backend: siril
    params:
      mapping: SHO  # or HOO
  - operation: stretch
    backend: builtin
  - operation: star_reduction
    backend: builtin
    optional: true
```

#### Mosaic Assembly
```yaml
name: Mosaic Assembly
description: Combine multiple panels into mosaic
steps:
  - operation: plate_solve
    backend: builtin
  - operation: mosaic_align
    backend: siril
  - operation: mosaic_blend
    backend: siril
    params:
      blend_mode: gradient
```

## Celery Task Structure

```python
# tasks/processing_tasks.py

@celery.task(bind=True, queue="processing")
def process_pipeline(self, job_id: int):
    """Execute a processing pipeline."""
    job = ProcessingJob.get(job_id)
    pipeline = job.pipeline

    for step in pipeline.steps:
        self.update_state(state="PROGRESS", meta={
            "current_step": step.operation,
            "progress": step_index / total_steps
        })

        backend = get_backend(step.backend)
        result = backend.execute(step.operation, step.params)

        job.update_step_result(step, result)

    return {"status": "completed", "output": job.output_path}

@celery.task(queue="gpu")
def gpu_stretch(input_path: str, params: dict) -> str:
    """GPU-accelerated stretch - routed to GPU workers."""
    return gpu_ops.gpu_histogram_stretch(input_path, **params)
```

### Worker Configuration

```python
# celery_app.py

celery.conf.task_routes = {
    "tasks.processing_tasks.gpu_*": {"queue": "gpu"},
    "tasks.processing_tasks.*": {"queue": "processing"},
}

celery.conf.task_queues = [
    Queue("processing", routing_key="processing"),
    Queue("gpu", routing_key="gpu"),  # Only GPU-enabled workers consume this
]
```

## Database Models

```python
class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True)
    status = Column(String(20))  # pending, running, completed, failed
    pipeline_id = Column(Integer, ForeignKey("pipeline_templates.id"))

    # Input files
    input_files = relationship("ProcessingFile")

    # Progress tracking
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Output
    output_path = Column(String(500))
    output_format = Column(String(20))

    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

class PipelineTemplate(Base):
    __tablename__ = "pipeline_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    description = Column(Text)
    steps = Column(JSON)  # Serialized pipeline steps
    is_builtin = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
```

## API Endpoints

```python
# POST /api/processing/jobs
# Create new processing job
{
    "input_files": [1, 2, 3],  # ProcessingFile IDs
    "template_id": 1,          # Or custom pipeline
    "custom_steps": null       # Override template steps
}

# GET /api/processing/jobs/{id}
# Get job status and progress

# GET /api/processing/jobs/{id}/preview
# Get preview image of current state

# POST /api/processing/templates
# Create custom pipeline template

# GET /api/processing/templates
# List available templates
```

## Implementation Order

1. **Phase 1: Core Infrastructure**
   - ProcessingBackend abstract interface
   - BuiltinBackend with existing gpu_ops
   - Basic Celery task structure

2. **Phase 2: Siril Integration**
   - SirilBackend implementation
   - Script generation for common operations
   - Docker container with Siril installed

3. **Phase 3: Input Sources**
   - Manual upload API
   - Folder watch service
   - Seestar integration

4. **Phase 4: Templates & UI**
   - Built-in templates
   - Template customization API
   - Frontend workflow builder

5. **Phase 5: Advanced Features**
   - GPU worker routing
   - Cloud sync integration
   - Mosaic support
