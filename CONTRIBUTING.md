# Contributing

Thank you for your interest in contributing to this project! We welcome bug reports, feature requests, and pull requests.

## Getting Started

1. **Fork** the repository and clone your fork locally.
2. **Install dependencies** using [uv](https://docs.astral.sh/uv/):
   ```bash
   uv sync --all-groups
   ```
3. Create a new branch for your changes:
   ```bash
   git checkout -b my-feature-or-fix
   ```

## Development Workflow

- Make your changes on the feature branch.
- Run the test suite before opening a pull request:
  ```bash
  uv run pytest
  ```
- Ensure all tests pass and add new tests for any new behavior.

## Submitting a Pull Request

1. Push your branch to your fork.
2. Open a pull request against the `main` branch of this repository.
3. Fill in the pull request template (if present) and describe what your changes do and why.
4. A maintainer will review your PR. Please respond to any review comments in a timely manner.
5. Once approved, a maintainer will merge your pull request.

## Reporting Issues

Please use the [GitHub Issues](../../issues) page to report bugs or request features. When reporting a bug, include:

- A clear description of the problem.
- Steps to reproduce the issue.
- The expected vs. actual behavior.
- Relevant environment information (OS, Python version, package version).

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code.
- Keep commits focused and atomic — one logical change per commit.
- Write clear, descriptive commit messages.

## License

By contributing, you agree that your contributions will be licensed under the same license as this project. See [LICENSE](LICENSE) for details.
