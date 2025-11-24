# Contributing to CAI

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/cai.git
cd cai
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

## Code Style

CAI follows PEP 8 style guidelines. We use:
- Black for code formatting
- isort for import sorting
- flake8 for linting
- mypy for type checking

To run the code quality checks:
```bash
black .
isort .
flake8
mypy .
```

## Testing

We use pytest for testing. To run the test suite:
```bash
pytest
```

## Documentation

Documentation is built using MkDocs. To build and serve the documentation locally:
```bash
mkdocs serve
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run all tests and code quality checks
5. Submit a pull request

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) when contributing to CAI.

## License

By contributing to CAI, you agree that your contributions will be licensed under the project's [MIT License](LICENSE). 