# Contributing to ASA

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a feature branch
4. Make your changes
5. Run tests
6. Submit a pull request

## Development Setup

```bash
pip install -e ".[dev]"
cd frontend && npm install && cd ..
```

## Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=asa tests/

# Specific test file
pytest tests/unit/test_evidence.py -v
```

## Code Standards

- Use type hints everywhere
- Follow existing code style
- Write tests for new features
- Update documentation for user-facing changes
- Keep commits atomic and well-described

## Architecture Guidelines

- Every finding must have evidence
- Prefer deterministic analysis over LLM guessing
- Prefer AST parsing over regex
- Never allow claims without machine-verifiable proof
- Test with synthetic repositories for edge cases
