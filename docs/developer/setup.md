# Developer setup

This document explains how to set up a **DyCoV development environment**
from source.

It is intended for **developers and contributors** who want to:
- modify DyCoV,
- debug internal behavior,
- add or extend features,
- contribute changes to the codebase.

If you only want to **use DyCoV**, do **not** follow this document.
Refer instead to the installation guides in `docs/installation/`.

---

## 1. Scope and assumptions

This document describes a **native Linux development workflow**.

Assumptions:
- You are working on a Linux system.
- You are comfortable with command‑line tools.
- You understand Python virtual environments at a basic level.

End‑user installation methods (distribution image, WSL, Docker end‑user mode)
are **not suitable for development workflows**.

---

## 2. System requirements

### 2.1 Operating system

A recent Linux distribution is required.

Recommended:
- Debian 12 or newer
- Ubuntu 22.04 LTS or newer

---

### 2.2 System packages

Install the required system tools:

```bash
sudo apt install \
  git \
  curl \
  unzip \
  gcc \
  g++ \
  cmake
````

These tools are required for:

*   building and running Dynawo,
*   developing and debugging DyCoV.

***

### 2.3 LaTeX

DyCoV generates PDF reports, which are often needed during development.

```bash
sudo apt install \
  texlive-base \
  texlive-latex-base \
  texlive-latex-recommended \
  texlive-latex-extra \
  texlive-science \
  texlive-lang-french \
  latexmk
```

***

### 2.4 Python (≥ 3.13)

DyCoV **requires Python version 3.13 or newer**.

Ensure Python 3.13 is installed and available:

```bash
python3.13 --version
```

If multiple Python versions are installed, explicitly use Python 3.13 when
creating the development environment.

***

### 2.5 uv

DyCoV uses **uv** to manage virtual environments and dependencies.

Install uv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

> **Note**
>
> `pip` and `venv` are not used directly.
> All dependency management is handled by `uv`.

***

## 3. Dynawo requirement (developer responsibility)

DyCoV relies on **Dynawo** to run RMS simulations.

In a **development context**:
- Dynawo is **not installed or managed by DyCoV**.
- Installing and maintaining Dynawo is the **responsibility of the developer**.

In practice, developers usually work with a **Dynawo nightly distribution**,
as this is the reference used for ongoing developments and for alignment with
current model and feature support.

You may:
- use a precompiled Dynawo distribution (for example, a nightly build), or
- clone the Dynawo repository and build it yourself from source.

The choice depends on your development needs and constraints.

For instructions on installing or compiling Dynawo, refer to the **official
Dynawo documentation**.

Developers must ensure that:
- a compatible Dynawo version is available,
- the `dynawo.sh` launcher can be found (for example via `PATH` or an explicit
  configuration).

DyCoV does not enforce a specific Dynawo installation method in development mode.

### Using Dynawo without modifying PATH

It is **not mandatory** to add Dynawo to the system `PATH`.

If the Dynawo launcher (`dynawo.sh`) is **not available in PATH**, the developer
must explicitly provide its location when running DyCoV, using the
`-l` / `--launcher` command‑line option.

For example:

```bash
dycov validate -l /path/to/dynawo/dynawo.sh ...
```

***

## 4. Cloning the repository

Choose a working directory and clone the DyCoV repository:

```bash
git clone https://github.com/dynawo/dyn-grid-compliance-verification dycov_repo
cd dycov_repo
```

***

## 5. Creating the development environment

Create a virtual environment using **Python 3.13**:

```bash
uv venv dycov_venv --python 3.13
```

Activate the environment:

```bash
source dycov_venv/bin/activate
```

***

## 6. Installing DyCoV in development mode

Install DyCoV in editable mode with development dependencies:

```bash
uv pip install -e .[dev,test]
```

This installs:

*   DyCoV itself in editable mode,
*   all runtime dependencies,
*   development and test dependencies.

***

## 7. Running DyCoV in development mode

With the virtual environment activated, verify that DyCoV is available:

```bash
dycov -h
```

Commands executed in this environment:

*   use the local source tree,
*   reflect code changes immediately.

***

## 8. Typical development workflow

A common development loop is:

1.  Activate the environment:
    ```bash
    source dycov_venv/bin/activate
    ```
2.  Modify source files under `src/dycov/`.
3.  Ensure Dynawo is correctly configured and reachable.
4.  Run DyCoV commands or tests.
5.  Inspect logs, generated results, and reports.
6.  Iterate.

***

## 9. When to use this setup

Use this development setup if you:

*   work on DyCoV internals,
*   need to debug execution logic,
*   add or modify workflows or PCS,
*   contribute changes to the codebase.

If your goal is only to run validations or generate reports,
use the installation methods described in `docs/installation/` instead.

