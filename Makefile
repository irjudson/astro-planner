# Makefile for Astro Planner Project
# Common development tasks

.PHONY: help test test-verbose test-coverage test-quick clean install dev-up dev-down dev-logs lint format check-coverage

# Default target
help:
	@echo "Astro Planner - Available Commands"
	@echo "==================================="
	@echo ""
	@echo "Testing:"
	@echo "  make test              - Run all tests (no coverage)"
	@echo "  make test-verbose      - Run tests with verbose output"
	@echo "  make test-coverage     - Run tests with full coverage report"
	@echo "  make test-quick        - Run tests in parallel (fast)"
	@echo "  make test-file FILE=   - Run specific test file"
	@echo "  make check-coverage    - Show current coverage percentage"
	@echo ""
	@echo "Development:"
	@echo "  make install           - Install Python dependencies"
	@echo "  make dev-up            - Start development environment (Docker)"
	@echo "  make dev-down          - Stop development environment"
	@echo "  make dev-logs          - Show development logs"
	@echo "  make dev-simple        - Start simple dev mode (no Docker)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint              - Run linters (ruff, mypy)"
	@echo "  make format            - Format code with black and ruff"
	@echo "  make clean             - Remove cache and generated files"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate        - Run database migrations"
	@echo "  make db-upgrade        - Upgrade to latest migration"
	@echo "  make db-downgrade      - Downgrade one migration"
	@echo ""
	@echo "Git:"
	@echo "  make commit-tests      - Commit test changes"
	@echo "  make push              - Push to remote"
	@echo ""

# Testing targets
test:
	@echo "Running all tests (no coverage)..."
	@cd backend && python -m pytest tests/ --no-cov -q

test-verbose:
	@echo "Running tests with verbose output..."
	@cd backend && python -m pytest tests/ -v --no-cov

test-coverage:
	@echo "Running tests with full coverage report..."
	@cd backend && python -m pytest tests/ --cov=app --cov-report=term --cov-report=html
	@echo ""
	@echo "HTML coverage report generated in backend/htmlcov/index.html"

test-quick:
	@echo "Running tests in parallel..."
	@cd backend && python -m pytest tests/ -n auto --no-cov -q

test-file:
	@echo "Running specific test file: $(FILE)..."
	@cd backend && python -m pytest tests/$(FILE) -v --no-cov

check-coverage:
	@echo "Checking current coverage..."
	@cd backend && python -m pytest tests/ --cov=app --cov-report=term 2>&1 | grep -E "^TOTAL"

# Development environment
install:
	@echo "Installing Python dependencies..."
	@cd backend && pip install -r requirements.txt
	@cd backend && pip install -r requirements-processing.txt
	@echo "Dependencies installed!"

dev-up:
	@echo "Starting development environment..."
	@docker-compose up -d
	@echo "Development environment running!"
	@echo "API: http://localhost:8000"
	@echo "Frontend: http://localhost:5173"

dev-down:
	@echo "Stopping development environment..."
	@docker-compose down

dev-logs:
	@docker-compose logs -f

dev-simple:
	@echo "Starting simple development mode..."
	@./dev-simple.sh

# Code quality
lint:
	@echo "Running linters..."
	@cd backend && ruff check app/ tests/ || true
	@echo ""
	@echo "Type checking with mypy..."
	@cd backend && mypy app/ || true

format:
	@echo "Formatting code with black..."
	@cd backend && black app/ tests/
	@echo ""
	@echo "Sorting imports with ruff..."
	@cd backend && ruff check --fix app/ tests/

clean:
	@echo "Cleaning up cache and generated files..."
	@find backend -type f -name '*.pyc' -delete
	@find backend -type d -name '__pycache__' -delete
	@find backend -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	@rm -rf backend/.pytest_cache
	@rm -rf backend/htmlcov
	@rm -rf backend/.coverage
	@echo "Cleanup complete!"

# Database targets
db-migrate:
	@echo "Creating new migration..."
	@cd backend && alembic revision --autogenerate -m "$(MSG)"

db-upgrade:
	@echo "Upgrading database to latest migration..."
	@cd backend && alembic upgrade head

db-downgrade:
	@echo "Downgrading database one version..."
	@cd backend && alembic downgrade -1

# Git helpers
commit-tests:
	@echo "Committing test changes..."
	@git add backend/tests/
	@git commit -m "test: $(MSG)" -m "Generated with [Claude Code](https://claude.com/claude-code)" -m "Co-Authored-By: Claude <noreply@anthropic.com>"

push:
	@echo "Pushing to remote..."
	@git push

# Service-specific test targets
test-catalog:
	@echo "Running catalog service tests..."
	@cd backend && python -m pytest tests/test_catalog_service.py -v --no-cov

test-moon:
	@echo "Running moon service tests..."
	@cd backend && python -m pytest tests/test_moon_service.py -v --no-cov

test-api:
	@echo "Running API tests..."
	@cd backend && python -m pytest tests/test_api.py -v --no-cov

test-integration:
	@echo "Running integration tests..."
	@cd backend && python -m pytest tests/test_*_integration.py -v --no-cov

# Coverage targets for specific files
coverage-catalog:
	@echo "Checking catalog_service coverage..."
	@cd backend && python -m pytest tests/test_catalog_service.py --cov=app/services/catalog_service --cov-report=term

coverage-moon:
	@echo "Checking moon_service coverage..."
	@cd backend && python -m pytest tests/test_moon_service.py --cov=app/services/moon_service --cov-report=term

# Development shortcuts
run-backend:
	@echo "Starting backend server..."
	@cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-frontend:
	@echo "Starting frontend dev server..."
	@cd frontend && npm run dev

# Quick status check
status:
	@echo "Git Status:"
	@git status --short
	@echo ""
	@echo "Recent Commits:"
	@git log --oneline -5
	@echo ""
	@echo "Test Coverage:"
	@cd backend && python -m pytest tests/ --cov=app --cov-report=term 2>&1 | grep -E "^TOTAL" || echo "Run 'make test-coverage' first"
