# Contributing to PrivateCloud

Thank you for your interest in contributing to PrivateCloud!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/privatecloud.git`
3. Create a virtual environment: `python -m venv venv && source venv/bin/activate`
4. Install in dev mode: `pip install -e ".[dev]"`
5. Install pre-commit hooks: `pre-commit install`

## Development Workflow

### Running Tests

```bash
pytest tests/ -v
```

### Code Style

We use:
- **Black** for code formatting
- **Ruff** for linting
- **MyPy** for type checking

```bash
black privatecloud/
ruff check privatecloud/
mypy privatecloud/
```

### Pre-commit Hooks

Before committing, run:

```bash
pre-commit run --all-files
```

## Submitting Changes

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes and commit with clear, descriptive messages
3. Push to your fork: `git push origin feature/your-feature-name`
4. Open a Pull Request with:
   - Clear description of the changes
   - Link to any related issues
   - Screenshots for UI changes

## Reporting Issues

When reporting issues, please include:
- PrivateCloud version (`privatecloud --version`)
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error logs if applicable

## Good First Issues

Looking for a way to contribute? Check out issues labeled [`good first issue`](https://github.com/Kubenew/privatecloud/labels/good%20first%20issue)!

## Questions?

Feel free to open a Discussion or reach out to the maintainers.