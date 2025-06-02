# Development Guide

## Project Structure

```
paper_auditor/
├── docs/                    # Documentation
│   ├── API_LOGGING_README.md  # API logging documentation
│   └── DEVELOPMENT.md         # This file
├── examples/                # Example usage
│   ├── demo_scripts/        # Demo and example scripts
│   └── sample_data/         # Sample papers, references, and reports
├── paper_auditor/           # Main package
│   ├── __init__.py         # Package initialization
│   ├── __main__.py         # CLI entry point
│   ├── auditor.py          # Main auditing logic
│   ├── cli.py              # Command-line interface
│   ├── extractors.py       # Citation extraction
│   ├── llm_evaluator.py    # LLM-based evaluation
│   ├── lookup.py           # Database lookups
│   ├── models.py           # Data models
│   └── reporters.py        # Report generation
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── test_api_logging.py
│   └── test_models.py
├── venv/                    # Virtual environment (ignored in git)
├── .gitignore              # Git ignore rules
├── Makefile                # Development commands
├── pytest.ini             # Pytest configuration
├── README.md               # Main documentation
├── requirements.txt        # Dependencies
├── setup.py               # Package setup
└── api_log_analyzer.py    # Standalone log analyzer
```

## Development Setup

### Prerequisites
- Python 3.8 or higher
- pip and virtualenv

### Quick Setup

1. **Clone and enter the project:**
   ```bash
   git clone <repo-url>
   cd paper-auditor
   ```

2. **Set up development environment:**
   ```bash
   make dev-setup
   ```

3. **Set up API keys:**
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   # OR
   export ANTHROPIC_API_KEY="your-anthropic-api-key"
   ```

### Manual Setup

If you prefer manual setup:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Install development tools
pip install pytest black isort flake8 mypy sphinx
```

## Development Workflow

### Available Make Commands

```bash
make help           # Show all available commands
make install        # Install package and dependencies
make install-dev    # Install with development dependencies
make test           # Run all tests
make test-unit      # Run unit tests only
make test-integration  # Run integration tests only
make lint           # Run code quality checks
make format         # Format code with black and isort
make clean          # Clean build artifacts
make build          # Build package for distribution
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test types
make test-unit
make test-integration

# Run tests with specific markers
pytest -m "not api"     # Skip API tests
pytest -m "slow"        # Run only slow tests
pytest -m "llm"         # Run only LLM tests

# Run specific test files
pytest tests/test_models.py
pytest tests/test_api_logging.py -v
```

### Code Quality

This project uses several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

```bash
# Format code
make format

# Check code quality
make lint

# Individual tools
black paper_auditor tests
isort paper_auditor tests
flake8 paper_auditor tests
mypy paper_auditor
```

### Testing Guidelines

#### Test Organization
- `tests/test_models.py`: Data model tests
- `tests/test_api_logging.py`: API integration tests

#### Test Markers
Use pytest markers to categorize tests:

```python
import pytest

@pytest.mark.unit
def test_citation_model():
    """Unit test for citation model."""
    pass

@pytest.mark.integration
def test_crossref_lookup():
    """Integration test requiring API calls."""
    pass

@pytest.mark.api
@pytest.mark.slow
def test_full_audit_pipeline():
    """Slow test requiring multiple API calls."""
    pass
```

#### Running Tests Without APIs
```bash
# Skip tests that require API calls
pytest -m "not api"

# Skip slow tests
pytest -m "not slow"
```

## Architecture Overview

### Core Components

1. **Extractors** (`extractors.py`): Extract citations from papers
2. **Lookup** (`lookup.py`): Verify citations against databases
3. **LLM Evaluator** (`llm_evaluator.py`): Assess relevance and justification
4. **Auditor** (`auditor.py`): Orchestrate the audit process
5. **Reporters** (`reporters.py`): Generate output reports
6. **CLI** (`cli.py`): Command-line interface

### Data Flow

```
Paper (PDF/TXT) → Extractors → Citations → Lookup → Metadata
                                     ↓
LLM Evaluator ← Citations + Context ← Auditor
      ↓
  Evaluations → Reporter → Final Report (MD/JSON)
```

### Key Design Principles

1. **Modular**: Each component has a single responsibility
2. **Configurable**: Support multiple LLM providers and output formats
3. **Respectful**: Built-in rate limiting for APIs
4. **Cacheable**: Cache responses to avoid redundant API calls
5. **Testable**: Clear separation of concerns for easy testing

## Adding New Features

### Adding a New Database Lookup

1. Add the lookup logic to `lookup.py`
2. Update the `DatabaseLookup` class
3. Add configuration options in `cli.py`
4. Write tests in `tests/test_api_logging.py`

### Adding a New Output Format

1. Add the formatter to `reporters.py`
2. Update the `generate_report` function
3. Add CLI option in `cli.py`
4. Add examples to `examples/sample_data/`

### Adding a New LLM Provider

1. Extend the `LLMEvaluator` class in `llm_evaluator.py`
2. Add configuration in `cli.py`
3. Update documentation

## Debugging

### Enable Verbose Logging

```bash
paper-auditor paper.pdf --verbose
```

### Debug Mode
Set environment variable for debug mode:
```bash
export PAPER_AUDITOR_DEBUG=1
```

### API Call Debugging
The project includes comprehensive API logging. See `docs/API_LOGGING_README.md` for details.

## Release Process

1. **Update version** in `setup.py`
2. **Run full test suite**: `make test`
3. **Check code quality**: `make lint`
4. **Build package**: `make build`
5. **Tag release**: `git tag v1.x.x`
6. **Push changes**: `git push origin main --tags`

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run the test suite: `make test`
5. Check code quality: `make lint`
6. Format code: `make format`
7. Commit changes with clear messages
8. Push and create a pull request

## Common Issues

### API Rate Limits
- The tool includes built-in rate limiting
- Use `--dry-run` to test without API calls
- Check API quota limits

### Virtual Environment Issues
```bash
# Recreate virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate
make install-dev
```

### Import Errors
```bash
# Reinstall in development mode
pip install -e .
``` 