# DyCoV installation

This directory contains the documentation describing **how to install DyCoV**
and make it available on your system.

Installation is a prerequisite for using DyCoV, but it is **not a tutorial
workflow itself**. Once DyCoV is installed, usage is covered by the tutorials
in `docs/tutorials/`.

---

## Installation methods

DyCoV supports two installation paths for end‑users.

### 1. Using the prebuilt distribution image (recommended)

This is the **recommended installation method for most users**.

The prebuilt distribution image provides a fully self‑contained Linux
environment that includes:
- DyCoV
- Dynawo
- Python
- uv
- LaTeX
- all required system dependencies

This method:
- avoids manual dependency installation,
- ensures a controlled and reproducible environment,
- supports both Linux and Windows (via WSL or Docker Desktop).

➡️ See: `using_the_provided_image.md`

---

### 2. Native Linux installation (advanced users only)

DyCoV can also be installed directly on a native Linux system without using the
prebuilt image.

In this mode:
- DyCoV is installed inside a user‑level Python virtual environment,
- Dynawo is automatically downloaded and installed by the DyCoV installer,
- system‑level prerequisites (Python ≥ 3.13, uv, LaTeX, build tools) must be
  installed manually by the user.

This method is intended for **advanced users** who require full control over
their system environment.

➡️ See: `linux_native.md`

---

## Next steps

After completing one of the installation procedures above, continue with the
user‑facing tutorials:

➡️ `../tutorials/README.md`