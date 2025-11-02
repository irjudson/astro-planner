# Seestar S50 Integration Architecture

This document outlines the design for integrating direct Seestar S50 telescope control into the astro-planner application.

## Overview

The integration will allow astro-planner to directly control a Seestar S50 smart telescope to execute observation plans, eliminating the need for ASCOM Alpaca middleware.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Astro Planner Frontend                    │
│  (Browser - Plan Generation, Target List, Control UI)       │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP/REST API
┌───────────────────────────▼─────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ Planner Service  │  │ Catalog Service  │                 │
│  └──────────────────┘  └──────────────────┘                 │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │Scheduler Service │  │ Telescope Service│◄──── NEW        │
│  └──────────────────┘  └────────┬─────────┘                 │
│                                  │                           │
│                         ┌────────▼──────────┐                │
│                         │ Seestar Client    │◄──── NEW      │
│                         │  - TCP Socket     │                │
│                         │  - JSON Protocol  │                │
│                         │  - State Machine  │                │
│                         └────────┬──────────┘                │
└──────────────────────────────────┼───────────────────────────┘
                                   │ TCP Socket (Port 5555)
                         ┌─────────▼──────────┐
                         │  Seestar S50       │
                         │  Smart Telescope   │
                         └────────────────────┘
```

## Component Design

### 1. Seestar Client Library (`backend/app/clients/seestar_client.py`)

A low-level client library that handles TCP socket communication with the Seestar S50.

**Responsibilities**:
- Manage TCP socket connection to Seestar S50
- Send/receive JSON messages with proper formatting
- Handle message ID generation and response matching
- Implement reconnection logic
- Provide async methods for all telescope commands

**Key Methods**:
```python
class SeestarClient:
    async def connect(host: str, port: int = 5555) -> bool
    async def disconnect() -> None
    async def goto_target(ra_hours: float, dec_degrees: float, target_name: str) -> bool
    async def start_imaging(restart: bool = True) -> bool
    async def stop_imaging() -> bool
    async def auto_focus() -> bool
    async def get_status() -> dict
    async def set_exposure(exposure_ms: int) -> bool
    async def configure_settings(**settings) -> bool
    async def park() -> bool
```

**State Management**:
- Track connection state
- Monitor operation states (goto, focus, imaging)
- Handle timeouts and errors
- Provide status callbacks

### 2. Telescope Service (`backend/app/services/telescope_service.py`)

High-level service that orchestrates telescope operations for the planner.

**Responsibilities**:
- Translate scheduled targets into telescope commands
- Execute observation sequences (goto → focus → image)
- Monitor telescope state during execution
- Handle errors and retries
- Provide progress updates to frontend

**Key Methods**:
```python
class TelescopeService:
    def __init__(seestar_client: SeestarClient)
    async def execute_plan(scheduled_targets: List[ScheduledTarget]) -> ExecutionResult
    async def execute_target(target: ScheduledTarget) -> bool
    async def get_telescope_status() -> TelescopeStatus
    async def abort_execution() -> None
    async def park_telescope() -> bool
```

**Execution Flow**:
1. Connect to telescope
2. Configure initial settings (exposure, dither, etc.)
3. For each scheduled target:
   - Goto target coordinates
   - Wait for goto completion
   - Run auto focus
   - Start imaging for specified duration
   - Stop imaging
   - Report progress
4. Park telescope when complete

### 3. REST API Endpoints (`backend/app/main.py`)

New endpoints for telescope control and monitoring.

```python
# Connect to telescope
POST /api/telescope/connect
Request: {"host": "seestar.local", "port": 5555}
Response: {"connected": true, "status": {...}}

# Get telescope status
GET /api/telescope/status
Response: {
    "connected": true,
    "current_ra": 12.5,
    "current_dec": 45.2,
    "state": "idle",
    "is_tracking": false
}

# Execute observation plan
POST /api/telescope/execute
Request: {"plan_id": "uuid", "scheduled_targets": [...]}
Response: {"execution_id": "uuid", "status": "started"}

# Get execution progress
GET /api/telescope/execution/{execution_id}
Response: {
    "execution_id": "uuid",
    "status": "running",
    "current_target": 2,
    "total_targets": 10,
    "progress": 20,
    "errors": []
}

# Abort execution
POST /api/telescope/abort
Response: {"status": "aborted"}

# Park telescope
POST /api/telescope/park
Response: {"status": "parking"}
```

### 4. Frontend Integration

Add telescope control UI to the planner interface.

**New Components**:
- **Telescope Connection Panel**: Connect/disconnect from Seestar
- **Execution Controls**: Start/stop/pause plan execution
- **Progress Monitor**: Real-time execution progress
- **Status Display**: Current telescope state and position

**UI Flow**:
1. User generates observation plan
2. User connects to Seestar S50
3. User clicks "Execute Plan" button
4. System shows progress as targets are executed
5. User can monitor status, abort if needed
6. System reports completion

## Data Models

### ScheduledTarget (Enhanced)
```python
class ScheduledTarget:
    target: DSOTarget
    start_time: datetime
    end_time: datetime
    duration: timedelta
    exposure_count: int
    exposure_seconds: int
    altitude_at_start: float
    score: TargetScore
    # New fields for telescope control
    goto_completed: bool = False
    focus_completed: bool = False
    imaging_completed: bool = False
    actual_exposures: int = 0
    errors: List[str] = []
```

### TelescopeStatus
```python
class TelescopeStatus:
    connected: bool
    host: str
    current_ra_hours: float
    current_dec_degrees: float
    state: str  # "idle", "slewing", "focusing", "imaging", "parked"
    is_tracking: bool
    current_target: Optional[str]
    firmware_version: str
```

### ExecutionProgress
```python
class ExecutionProgress:
    execution_id: str
    status: str  # "idle", "running", "paused", "completed", "aborted", "error"
    total_targets: int
    completed_targets: int
    current_target_index: int
    current_target_name: str
    progress_percent: float
    elapsed_time: timedelta
    estimated_remaining: timedelta
    errors: List[ExecutionError]
```

## Error Handling

### Connection Errors
- Timeout connecting to telescope
- Network disconnection during execution
- Invalid host/port

**Strategy**: Retry with exponential backoff, notify user, allow manual retry

### Command Errors
- Goto failed (equipment moving, out of range)
- Focus failed (no stars visible)
- Imaging failed (settings invalid)

**Strategy**:
1. Retry command up to 3 times
2. Skip target if still failing
3. Continue with next target
4. Log error for user review

### Timeout Errors
- Command takes too long (>10s)
- No response from telescope

**Strategy**: Cancel command, reconnect if needed, retry or skip

## Configuration

Add to `backend/app/config.py`:

```python
class SeestarConfig:
    DEFAULT_HOST: str = "seestar.local"
    DEFAULT_PORT: int = 5555
    CONNECTION_TIMEOUT: int = 10
    COMMAND_TIMEOUT: int = 10
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2

    # Imaging defaults
    DEFAULT_EXPOSURE_MS: int = 10000
    DEFAULT_DITHER_ENABLED: bool = True
    DEFAULT_DITHER_PIXELS: int = 50
    DEFAULT_DITHER_INTERVAL: int = 10
    DEFAULT_GAIN: int = 80
```

## Implementation Phases

### Phase 1: Core Client Library
- Implement `SeestarClient` with TCP socket communication
- Add message send/receive with ID tracking
- Implement basic commands (connect, goto, start/stop imaging)
- Add unit tests

### Phase 2: Telescope Service
- Implement `TelescopeService` with execution orchestration
- Add state machine for execution flow
- Implement error handling and retries
- Add integration tests

### Phase 3: REST API
- Add telescope control endpoints
- Implement WebSocket for real-time progress updates (optional)
- Add request validation and error responses

### Phase 4: Frontend Integration
- Add telescope connection UI
- Add execution control buttons
- Add progress monitoring display
- Add error display and recovery options

### Phase 5: Testing & Refinement
- Test with real Seestar S50 hardware
- Refine timing and retry logic
- Optimize performance
- Add logging and debugging tools

## Future Enhancements

1. **Multiple Telescope Support**: Support connecting to multiple Seestar units
2. **Scheduler Integration**: Auto-start execution at scheduled time
3. **Weather Integration**: Pause execution if weather deteriorates
4. **Image Download**: Download stacked images from Seestar
5. **Live Preview**: Show live view from telescope during execution
6. **Advanced Settings**: Expose all Seestar settings in UI
7. **Simulation Mode**: Test execution without telescope connected

## Security Considerations

- Validate all user inputs (host, port, coordinates)
- Implement rate limiting on API endpoints
- Add authentication for telescope control endpoints
- Log all telescope commands for audit trail
- Implement emergency stop mechanism
- Prevent multiple simultaneous executions

## Performance Considerations

- Use async/await for non-blocking telescope communication
- Implement connection pooling if supporting multiple telescopes
- Cache telescope status to reduce polling
- Optimize state monitoring frequency
- Use WebSockets for real-time updates instead of polling

## Dependencies

New Python packages needed:
```
# None required - uses standard library:
# - socket (TCP communication)
# - json (message serialization)
# - asyncio (async communication)
# - threading (background tasks)
```

## Testing Strategy

1. **Unit Tests**: Mock TCP socket, test message formatting and parsing
2. **Integration Tests**: Use Seestar simulator or test mode
3. **End-to-End Tests**: Test with real hardware in controlled environment
4. **Load Tests**: Test with long observation plans
5. **Failure Tests**: Simulate network failures, timeouts, invalid responses
