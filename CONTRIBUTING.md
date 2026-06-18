# Contributing to DyCoV

Thank you for contributing to DyCoV.
This document describes the conventions and workflow used by the team.

---

## 1. Setting up the development environment

Follow the instructions in
[docs/developer/setup.md](docs/developer/setup.md).

---

## 2. Branching strategy

### Feature branches

Create a branch from `master` for every change.
Use the related GitHub issue number as the base of the branch name:

```
42-fix-curve-normalization
87-add-pcs-i18-support
```

If no issue exists for the change, use a short descriptive name:

```
fix-dynawo-path-detection
refactor-benchmark-init
```

Branches are deleted after merge.

### Release branches

Stable release lines are maintained as long-lived branches named `vX.Y`
(e.g. `v1.0`, `v1.1`). Patch releases (`1.0.x`) are tagged from these
branches.

---

## 3. Submitting changes

### Pull requests

- Open PRs against **`master`** by default.
- For hotfixes on a published release, open the PR against the
  corresponding release branch (e.g. `v1.0`) and cherry-pick the
  fix into `master` afterwards.
- Keep PRs focused — one logical change per PR.
- Fill in the PR description with a clear summary of what changed and why.

### Code review

Code review is not enforced by GitHub but is **strongly recommended**
before merging. All PRs must pass the CI checks before merge.

Potential reviewers:

| Organization | Scope | GitHub handle |
|-------------|-------|---------------|
| RTE | Electrical modeling and grid-code compliance | @louisg-rte |
| RTE | Electrical modeling and grid-code compliance | @Philibert92 |
| AIA | Software architecture and implementation | @marcosmc |
| AIA | Software architecture and implementation | @marinjl |
| AIA | Software architecture and implementation | @guiuomsfont-aia |

### Issue templates

GitHub issue templates are provided for bug reports and feature requests.
Use them when opening new issues.

---

## 4. CI checks

CI runs automatically on every pull request across three platforms
(Linux, macOS, Windows) with Python 3.13.

The following checks must pass before merging:

| Check | Tool | Command |
|-------|------|---------|
| Linting | Ruff | `uv run ruff check src` |
| Tests | pytest | `uv run pytest` |
| Build | build | `uv run python -m build --wheel` |

Run them locally before pushing:

```bash
uv run ruff check src
uv run pytest -q
```

> **Note:** Coverage is collected by CI (`uv run pytest --cov=src`) but
> there is no coverage gate yet. It is available for informational purposes
> and may be enforced in a future release.

The `[dev,test]` extras include all tools needed for development:

| Extra | Package | Purpose |
|-------|---------|---------|
| `dev` | `ruff` | Linting and formatting |
| `dev` | `sphinx` | Building the reference manual locally (see `docs/manual/README.md`) |
| `test` | `pytest` | Test runner |
| `test` | `pytest-cov` | Coverage reporting |
| `test` | `pytest-mock` | Mocking utilities |

> **Note:** The signal processing workbench under `attic/sigproc_workbench/`
> has its own isolated environment. Use the `create_venv.sh` script provided
> there.

---

## 5. Code style

DyCoV uses **Ruff** for linting and style enforcement.
The configuration is defined in `pyproject.toml`.

Key conventions:
- All source code and comments must be written in **English**.
- Follow the existing patterns in the module you are modifying.
- Prefer guard clauses over deeply nested conditionals.
- Use named constants instead of magic numbers.
- Keep functions and methods focused — avoid functions exceeding ~50 lines.
- Use `get_` prefix for functions that always return a value,
  `find_` for functions that may return `None`.

Run Ruff to check your changes before pushing:

```bash
uv run ruff check src
```

To auto-fix issues where possible:

```bash
uv run ruff check src --fix
```

---

## 6. Adding a new PCS

See [docs/developer/add_new_pcs.md](docs/developer/add_new_pcs.md)
for a step-by-step guide.

---

## 7. Documentation

Any change that affects user-facing behavior, available workflows,
inputs, or outputs must be reflected in the documentation:

- Update the relevant tutorial under `docs/tutorials/`.
- Add or update examples under `examples/`.
- Update `docs/developer/` if the change affects internal architecture.

Developer-only refactors with no user impact may be documented in
code comments only.

---

## 8. Contact

For questions about the contribution process:

- Software issues and questions (AIA): dycov@aia.es