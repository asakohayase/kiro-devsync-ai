# Python Tooling Standards

## Package Management
- Always use `uv` for Python package management instead of pip
- Use `uv run` to execute Python commands and scripts
- Use `uv add` to install new dependencies
- Use `uv sync` to install dependencies from lock file

## Testing
- Use `uv run pytest` to run tests
- Include appropriate flags like `-v` for verbose output
- Use `--run` flag when running tests that need to be terminable

## Code Quality
- Use `uv run black` for code formatting
- Use `uv run flake8` for linting
- Use `uv run mypy` for type checking

## Examples
```bash
# Install dependencies
uv sync

# Run tests
uv run pytest tests/ -v

# Add new dependency
uv add requests

# Run the application
uv run python -m devsync_ai.main
```