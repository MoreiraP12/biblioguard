.PHONY: help install install-dev test test-unit test-integration lint format clean build docs serve-docs

# Default help command
help:
	@echo "Available commands:"
	@echo "  install      Install package and dependencies"
	@echo "  install-dev  Install package with development dependencies"
	@echo "  test         Run all tests"
	@echo "  test-unit    Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  lint         Run linting checks"
	@echo "  format       Format code with black and isort"
	@echo "  clean        Clean build artifacts and cache files"
	@echo "  build        Build package"
	@echo "  docs         Generate documentation"
	@echo "  serve-docs   Serve documentation locally"

# Installation
install:
	pip install -r requirements.txt
	pip install -e .

install-dev:
	pip install -r requirements.txt
	pip install -e .
	pip install pytest black isort flake8 mypy sphinx

# Testing
test:
	pytest

test-unit:
	pytest -m "not integration and not slow"

test-integration:
	pytest -m integration

test-api:
	pytest -m api

# Code quality
lint:
	flake8 paper_auditor tests
	mypy paper_auditor
	black --check paper_auditor tests
	isort --check-only paper_auditor tests

format:
	black paper_auditor tests
	isort paper_auditor tests

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .pytest_cache/ .mypy_cache/ .coverage htmlcov/

# Building
build: clean
	python setup.py sdist bdist_wheel

# Documentation
docs:
	@echo "Documentation generation would go here"
	@echo "Consider adding sphinx or mkdocs setup"

serve-docs:
	@echo "Documentation serving would go here"

# Development shortcuts
dev-setup: install-dev
	@echo "Development environment ready!" 