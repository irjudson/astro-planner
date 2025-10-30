# Testing

This document describes how to run tests for the Astro Planner application.

## Test Suite

The test suite includes:

- **Unit tests**: Test individual services and functions
- **API tests**: Test REST API endpoints
- **Integration tests**: Test the complete application via Docker

## Running Tests

### Prerequisites

Make sure Docker is running:
```bash
docker-compose up -d
```

### Option 1: Run tests in Docker (Recommended)

Rebuild the Docker image with test dependencies:
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

Run pytest in the container:
```bash
docker exec astro-planner pytest tests/ -v --cov=app --cov-report=term
```

### Option 2: Run tests locally

Install test dependencies:
```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-test.txt
```

Run pytest:
```bash
cd backend
pytest tests/ -v --cov=app --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Option 3: Run integration tests

The integration test script tests the running API:

```bash
# Make sure the app is running
docker-compose up -d

# Run integration tests
python test_api.py
```

## Test Structure

```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures
│   ├── test_api.py          # API endpoint tests
│   └── test_services.py     # Service layer tests
├── pytest.ini               # Pytest configuration
└── requirements-test.txt    # Test dependencies
```

## Continuous Integration

Tests run automatically on:
- Every push to `main` branch
- Every pull request to `main` branch

The GitHub Actions workflow:
1. Runs pytest unit tests
2. Builds Docker image
3. Runs integration tests
4. Uploads coverage reports

See `.github/workflows/tests.yml` for details.

## Test Coverage

Current test coverage targets:
- **Minimum**: 70% overall coverage
- **Goal**: 80%+ coverage

Run coverage report:
```bash
docker exec astro-planner pytest tests/ --cov=app --cov-report=term --cov-report=html
```

## Writing Tests

### API Tests

Add tests to `backend/tests/test_api.py`:

```python
def test_new_endpoint(client):
    """Test description."""
    response = client.get("/api/new-endpoint")
    assert response.status_code == 200
```

### Service Tests

Add tests to `backend/tests/test_services.py`:

```python
def test_new_service_method():
    """Test description."""
    service = MyService()
    result = service.my_method()
    assert result is not None
```

## Common Issues

### Tests fail with import errors
Make sure you're in the `backend` directory when running pytest.

### Coverage too low
Check the HTML coverage report to see which lines aren't covered:
```bash
open htmlcov/index.html
```

### Docker tests fail
Ensure the app is healthy:
```bash
curl http://localhost:9247/api/health
```

Check logs if unhealthy:
```bash
docker-compose logs
```
