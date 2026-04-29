# Public API Code Quality Audit

This directory contains tooling to audit the **public Python API** of the
`dycov` project and produce an **actionable report** of missing:

- type hints (via `mypy`)
- docstrings (via `pydocstyle`, NumPy-style)

The goal is **not** to refactor or fix code automatically, but to provide a
clear, deterministic list of actions required to bring the public API to the
expected quality level.

---

## What is considered "public API"

A function or method is considered **public** if:

- its name does **not** start with `_`
- and, for methods, the containing class name does **not** start with `_`

The visibility of the module itself (e.g. `_internal.py`) is intentionally
**not** used as a filter: public functions inside private modules are treated
as part of the internal public API and are therefore audited.

---

## How it works (high level)

The audit combines three independent sources of truth:

1. **AST inventory**  
   Parses the `src/` tree and builds the authoritative list of public functions
   and methods, including their exact line ranges.

2. **mypy**  
   Detects public functions or methods missing type annotations
   (`no-untyped-def`).

3. **pydocstyle**  
   Detects public functions or methods missing docstrings (`D102`, `D103`).

The results are cross-checked using file paths and line ranges to associate
each finding with the correct function or method.

---

## Scripts overview

| Script | Responsibility |
|------|----------------|
| `ast_inventory.py` | Build the AST-based inventory of public API elements |
| `run_mypy.py` | Run `mypy` with the project configuration |
| `run_pydocstyle.py` | Run `pydocstyle` for missing public docstrings |
| `cross_check.py` | Correlate AST, mypy, and pydocstyle results |
| `audit_public_api.py` | Orchestrator: runs the full audit and writes the report |

---

## Requirements

The audit relies on development dependencies declared in `pyproject.toml`:

- `mypy`
- `pydocstyle`

They must be installed using `uv`:

```bash
uv pip install -e .[dev]