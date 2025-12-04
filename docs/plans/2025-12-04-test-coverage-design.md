# Test Coverage Improvement Design

**Date:** 2025-12-04
**Status:** Approved

## Goal

Increase test coverage from 32% to 70% across the codebase.

## Decisions

| Decision | Choice |
|----------|--------|
| Target coverage | 70% |
| Priority order | Planning Core → Celestial Objects → Telescope → External APIs → Processing |
| External API strategy | Mock by default + `@pytest.mark.live` for optional real tests |

## Service Priority Order

### Phase 1: Observation Planning Core
These services form the heart of user interactions:

| Service | Current | Target | LOE |
|---------|---------|--------|-----|
| scheduler_service.py | 11% | 70% | Medium |
| planner_service.py | 17% | 70% | Medium |
| ephemeris_service.py | 17% | 70% | Medium |

### Phase 2: Celestial Object Services
Accuracy is critical for astronomy calculations:

| Service | Current | Target | LOE |
|---------|---------|--------|-----|
| moon_service.py | 0% | 70% | High |
| planet_service.py | 14% | 70% | Medium |
| comet_service.py | 18% | 70% | Medium |

### Phase 3: Telescope/Execution
Where bugs cause real-world problems:

| Service | Current | Target | LOE |
|---------|---------|--------|-----|
| telescope_service.py | 34% | 70% | Medium |
| telescope_tasks.py | 0% | 70% | High |

### Phase 4: External Data Services
Mostly mocking external APIs:

| Service | Current | Target | LOE |
|---------|---------|--------|-----|
| weather_service.py | 15% | 70% | Medium |
| horizons_service.py | 17% | 70% | Medium |
| seven_timer_service.py | 18% | 70% | Low |

### Phase 5: Processing Pipeline
Wait until post-processing design is implemented:

| Service | Current | Target | LOE |
|---------|---------|--------|-----|
| processing_service.py | 16% | 70% | High |
| direct_processor.py | 16% | 70% | High |
| export_service.py | 13% | 70% | Medium |

## External API Testing Strategy

### Default: Mocked Tests
- All external API calls mocked with realistic fixtures
- Fast execution for CI/CD
- Deterministic results

### Optional: Live Tests
```python
@pytest.mark.live
def test_horizons_real_query():
    """Test real JPL Horizons query - requires internet."""
    ...
```

Run live tests with:
```bash
pytest -m live  # Run only live tests
pytest -m "not live"  # Skip live tests (default in CI)
```

### Fixture Strategy
- Use `responses` or `httpx_mock` for HTTP mocking
- Store representative API responses in `tests/fixtures/`
- Document fixture creation date for staleness tracking

## Implementation Notes

- Write tests for public interface methods first
- Focus on happy path + key error cases
- Skip internal helper methods unless complex
- Use property-based testing for calculation-heavy services (ephemeris, moon)
