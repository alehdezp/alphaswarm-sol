# Contributing

Thank you for your interest in contributing to AlphaSwarm.sol.

## Getting Started

1. Fork the repository
2. Clone your fork
3. Install development dependencies with `uv sync`
4. Run tests to verify setup: `uv run pytest`

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with parallel execution (faster)
uv run pytest -n auto --dist loadfile

# Run specific test file
uv run pytest tests/test_builder.py -v
```

### Code Style

- Use `ruff` for linting and formatting
- Follow existing code patterns
- Add type hints to new code

### Pull Requests

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Documentation

Documentation is built with MkDocs Material. To preview locally:

```bash
pip install mkdocs-material
mkdocs serve
```

## Questions

Open an issue on GitHub for questions or discussion.
