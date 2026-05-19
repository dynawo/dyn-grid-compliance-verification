# Project structure

This document provides an overview of the **DyCoV repository structure** from a
developer perspective.

Its goal is to help contributors understand:
- how the project is organized,
- where to find specific components,
- which parts are relevant depending on the type of change.

This is **not** an API reference and does not describe internal algorithms in
detail.

---

## Repository overview

At a high level, the DyCoV repository is organized as follows:

```text
dyn-grid-compliance-verification/
├── src/
├── examples/
├── docs/
├── installers/
├── tests/
├── tests_integration/
├── pyproject.toml
└── ...
```

Each top‑level directory serves a distinct purpose.
Understanding these roles is essential when introducing changes, 
as modifications in one area may implicitly affect others.

---

## `src/` — DyCoV source code

```text
src/
└── dycov/
```

This directory contains the **DyCoV Python source code**.

Typical contents include:

*   command‑line interface (CLI),
*   workflow orchestration logic,
*   signal processing utilities,
*   PCS execution logic,
*   report generation.

Developers modifying DyCoV behavior will spend most of their time here, 
as all core logic and workflows are implemented in this package.

The package is installed in editable mode during development, so changes under
`src/dycov/` are reflected immediately when running DyCoV commands.

---

## `examples/` — Reference input cases

Examples are considered part of the functional specification of DyCoV and 
should remain consistent with expected behavior.

```text
examples/
├── Model/
├── Performance/
└── GFM/
```

This directory contains **validated example inputs** for the main DyCoV
workflows.

It is used for:

*   user onboarding,
*   regression testing,
*   debugging and development.

When modifying or extending DyCoV logic, developers are encouraged to:

*   reuse existing examples,
*   or add new examples illustrating new functionality.

Examples are treated as part of the project’s functional reference.

---

## `docs/` — Documentation

```text
docs/
├── installation/
├── tutorials/
├── developer/
└── ...
```

This directory contains the **public documentation**.

It is organized by audience and purpose:

*   `installation/` — how to install DyCoV,
*   `tutorials/` — how to use DyCoV workflows,
*   `developer/` — how to develop or extend DyCoV.

Other subdirectories may exist for figures, reference material, or documentation
tooling and are not part of the main reading flow.

---

## `installers/` — Distribution and packaging tools

```text
installers/
├── linux_install.sh
├── docker/
└── windows/
```

This directory contains scripts and tooling used to:

*   build distribution artifacts,
*   generate container images,
*   prepare end‑user installation packages.

Developers typically touch this directory when:

*   modifying installation behavior,
*   updating distribution logic,
*   debugging packaging issues.

It is **not** used during normal DyCoV execution.

---

## `tests/` — Tests and validation utilities

```text
tests/
```

This directory contains:

*   automated tests,
*   test utilities,
*   regression checks.

These tests are intended to be:

*   reasonably fast to execute,
*   runnable in typical development environments,
*   part of the regular development workflow.

Developers modifying logic are expected to update or extend these tests where
appropriate.

---

## `tests_integration/` — Integration and end‑to‑end tests (optional)

```text
tests_integration/
```

This directory contains **integration and end‑to‑end tests** that exercise DyCoV
together with external tools such as Dynawo.

These tests:

*   typically require a fully configured environment,
*   may rely on long‑running simulations,
*   often depend on specific Dynawo versions or setups.

They are **not intended to be executed as part of the regular development loop**.

Typical use cases include:

*   validating complete workflows end‑to‑end,
*   targeted regression testing,
*   manual or controlled verification.

New contributors can safely ignore this directory until advanced validation is
required.

---

## Project configuration files

### `pyproject.toml`

This file defines:

*   project metadata,
*   dependency specifications,
*   development and test dependencies,
*   build configuration.

Any change to dependencies or packaging must be reflected here.

---

## Typical developer entry points

Depending on your task, you will primarily work in:

| Task                         | Relevant directory   |
| ---------------------------- | -------------------- |
| Modify workflows or logic    | `src/dycov/`         |
| Add or update examples       | `examples/`          |
| Update documentation         | `docs/`              |
| Modify installers            | `installers/`        |
| Add unit or functional tests | `tests/`             |
| Run full integration checks  | `tests_integration/` |

Understanding this structure helps avoid unintended side effects when making
changes.

---

## Next steps

After understanding the project structure, continue with:

*   `setup.md` — to set up the development environment,
*   `extending_dycov.md` — to learn how to extend DyCoV functionality.

