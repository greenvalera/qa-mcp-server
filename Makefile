# Makefile for QA MCP Server

.PHONY: help install test test-unit test-integration test-scenarios test-all test-coverage clean lint format

# Default target
help:
	@echo "QA MCP Server - Available commands:"
	@echo ""
	@echo "Installation:"
	@echo "  install          Install dependencies"
	@echo "  install-test     Install test dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run unit tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-scenarios   Run test scenarios only"
	@echo "  test-all         Run all tests"
	@echo "  test-coverage    Run tests with coverage report"
	@echo "  test-fast        Run tests excluding slow ones"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run linting"
	@echo "  format           Format code"
	@echo "  clean            Clean temporary files"
	@echo ""
	@echo "Development:"
	@echo "  dev-setup        Setup development environment"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-test      Run tests in Docker"

# Installation
install:
	pip install -r app/requirements.txt

install-test:
	pip install -r tests/requirements-test.txt

# Testing
test: test-unit

test-unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -v -m unit

test-integration:
	@echo "Running integration tests..."
	@echo "Make sure MCP server is running on http://localhost:3000"
	pytest tests/integration/ -v -m integration

test-scenarios:
	@echo "Running test scenarios..."
	@echo "Make sure MCP server is running on http://localhost:3000"
	pytest tests/scenarios/ -v -m scenario

test-all:
	@echo "Running all tests..."
	@echo "Make sure MCP server is running on http://localhost:3000"
	pytest tests/ -v

test-coverage:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=app --cov-report=html --cov-report=term-missing -v

test-fast:
	@echo "Running fast tests (excluding slow ones)..."
	pytest tests/ -v -m "not slow"

# Code Quality
lint:
	@echo "Running linting..."
	flake8 app/ tests/
	mypy app/
	black --check app/ tests/
	isort --check-only app/ tests/

format:
	@echo "Formatting code..."
	black app/ tests/
	isort app/ tests/

# Cleanup
clean:
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/

# Development
dev-setup: install install-test
	@echo "Setting up development environment..."
	@echo "Creating .env file from example..."
	@if [ ! -f .env ]; then cp env.example .env; fi
	@echo "Development environment setup complete!"

# Docker
docker-build:
	@echo "Building Docker image..."
	docker build -t qa-mcp-server .

docker-test:
	@echo "Running tests in Docker..."
	docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Server management
start-server:
	@echo "Starting MCP server..."
	cd app && python -m mcp_server

start-server-dev:
	@echo "Starting MCP server in development mode..."
	cd app && python -m mcp_server --dev

# Test specific scenarios
test-search-functionality:
	@echo "Testing search functionality scenarios..."
	pytest tests/scenarios/test_search_scenarios.py::TestSearchFunctionalityScenarios -v

test-error-handling:
	@echo "Testing error handling scenarios..."
	pytest tests/scenarios/test_search_scenarios.py::TestErrorHandlingScenarios -v

test-performance:
	@echo "Testing performance scenarios..."
	pytest tests/scenarios/test_search_scenarios.py::TestPerformanceScenarios -v

test-end-to-end:
	@echo "Testing end-to-end scenarios..."
	pytest tests/scenarios/test_search_scenarios.py::TestEndToEndScenarios -v

# CI/CD helpers
ci-test: install-test test-unit
	@echo "CI unit tests completed"

ci-test-full: install-test test-all
	@echo "CI full tests completed"

# Documentation
docs:
	@echo "Generating test documentation..."
	@echo "See tests/README.md for detailed documentation"

# Quick development cycle
dev-test: format lint test-unit
	@echo "Development cycle completed"

# Full test suite with all checks
full-test: clean install-test format lint test-coverage
	@echo "Full test suite completed"
