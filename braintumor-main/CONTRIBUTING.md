# Contributing to Brain Tumour Detection

Thank you for your interest in contributing. This document explains how to report issues, propose features, and submit pull requests.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How to Report a Bug](#how-to-report-a-bug)
3. [How to Request a Feature](#how-to-request-a-feature)
4. [Development Workflow](#development-workflow)
5. [Pull Request Guidelines](#pull-request-guidelines)
6. [Coding Standards](#coding-standards)
7. [Commit Message Convention](#commit-message-convention)
8. [Testing Requirements](#testing-requirements)
9. [Documentation Requirements](#documentation-requirements)
10. [Getting Help](#getting-help)

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating you agree to uphold these standards. Report unacceptable behaviour to the maintainers.

---

## How to Report a Bug

Before filing an issue:
1. Search [existing issues](https://github.com/your-org/brain-tumor-detection/issues) to avoid duplicates.
2. Check the [Troubleshooting Guide](docs/troubleshooting.md).

When filing a bug report include:
- A clear, descriptive title
- Steps to reproduce the issue
- Expected vs actual behaviour
- Relevant log output (redact any secrets)
- Environment details: OS, Python version, Node version, Docker version
- `git log --oneline -1` (the commit SHA you are running)

Use the **Bug Report** issue template.

---

## How to Request a Feature

Open a [Feature Request](https://github.com/your-org/brain-tumor-detection/issues/new?template=feature_request.md) issue describing:
- The problem you are solving
- Your proposed solution
- Alternatives you considered
- Whether you are willing to implement it

Features are discussed in the issue before implementation begins to avoid wasted effort.

---

## Development Workflow

### 1. Fork and clone

```bash
git clone https://github.com/<your-fork>/brain-tumor-detection.git
cd brain-tumor-detection
git remote add upstream https://github.com/your-org/brain-tumor-detection.git
```

### 2. Create a feature branch

Branch names follow `type/short-description`:

```bash
git checkout -b feat/add-mobilenet-architecture
git checkout -b fix/gradcam-blank-image
git checkout -b docs/expand-api-reference
```

### 3. Set up the development environment

```bash
make setup
```

Or manually — see [Developer Guide](docs/developer_guide.md#development-environment-setup).

### 4. Install pre-commit hooks

```bash
pip install pre-commit
pre-commit install
```

### 5. Make your changes

Follow the [Coding Standards](#coding-standards) below.

### 6. Run tests

```bash
make test
```

All existing tests must pass. New code requires new tests.

### 7. Push and open a PR

```bash
git push origin feat/add-mobilenet-architecture
```

Open a pull request against the `develop` branch (not `main`).

---

## Pull Request Guidelines

- PRs must target the `develop` branch unless it is a hotfix for `main`
- Title should match the commit convention: `feat: add MobileNet architecture`
- Fill in the PR description template completely
- Link the relevant issue: `Closes #123`
- Keep PRs focused — one feature or fix per PR
- All CI checks must pass before review
- Request review from at least one maintainer
- Address all review comments before merging

### PR size guidance

| Size | Lines changed | Notes |
|---|---|---|
| XS | < 20 | Bug fixes, typos |
| S | 20–100 | Small feature, single file |
| M | 100–400 | Feature with tests |
| L | 400–800 | Major feature |
| XL | > 800 | Discuss in issue first |

Large PRs are hard to review. Break them into smaller focused PRs when possible.

---

## Coding Standards

### Python (ai-service)

- Formatter: **black** (line length 100)
- Linter: **ruff**
- Import sorter: **isort** (black-compatible profile)
- All functions and classes must have docstrings
- Use type annotations on all public functions
- Use `from __future__ import annotations` at the top of every module
- Access configuration via `from app.core.config import settings` — never `os.environ.get()`
- Log via `from app.core.logging import logger` — never `print()`

Run checks:
```bash
cd ai-service
ruff check app/ tests/
black --check app/ tests/
isort --check-only app/ tests/
```

### TypeScript / React (frontend)

- Formatter: **Prettier**
- Linter: **ESLint** with react-hooks and jsx-a11y plugins
- TypeScript strict mode enabled — no `any` types
- Functional components only (no class components)
- All interactive elements must have accessible labels

### Node.js (backend)

- Formatter: **Prettier**
- Linter: **ESLint**
- Use `const` by default; `let` when reassignment is needed

---

## Commit Message Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

**Types:**

| Type | When to use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no logic change |
| `refactor` | Code restructure, no behaviour change |
| `test` | Adding or fixing tests |
| `chore` | Build scripts, tooling, dependencies |
| `perf` | Performance improvement |
| `ci` | CI/CD changes |

**Examples:**
```
feat(models): add MobileNetV3 architecture
fix(gradcam): handle channels-last vs channels-first layout
docs(api): add batch inference examples to API reference
test(security): add JWT expiry edge case tests
chore(deps): pin tensorflow to 2.20.0
```

Breaking changes must be noted in the footer:
```
feat(auth)!: require JWT for all prediction endpoints

BREAKING CHANGE: Clients must include Authorization: Bearer <token>
on all /predict requests. Set PREDICTION_AUTH_MODE=public to revert.
```

---

## Testing Requirements

All contributions must maintain or improve test coverage.

### Rules

- New features: add tests covering the happy path and at least two error cases
- Bug fixes: add a regression test that reproduces the bug
- Do not merge if any existing test is failing
- Test file names: `test_<module>.py` (Python) or `<Component>.test.tsx` (TypeScript)

### Running tests

```bash
# All suites
make test

# Python only
cd ai-service && python -m pytest tests/ -v --cov=app

# Frontend only
cd frontend && npm test

# Backend only
cd backend && npm test
```

---

## Documentation Requirements

- New endpoints: add to [docs/api_reference.md](docs/api_reference.md)
- New configuration variables: add to the environment tables in [README.md](README.md) and [docs/installation.md](docs/installation.md)
- New CLI scripts: add to the Makefile and document in [docs/deployment.md](docs/deployment.md)
- Breaking changes: add an upgrade note to [docs/release_notes.md](docs/release_notes.md)
- New model architectures: add to the architectures table in [README.md](README.md) and [docs/user_guide.md](docs/user_guide.md)

---

## Getting Help

- Open a [Discussion](https://github.com/your-org/brain-tumor-detection/discussions) for questions
- File an [Issue](https://github.com/your-org/brain-tumor-detection/issues) for bugs
- For security issues see [SECURITY.md](SECURITY.md)
