# DyCoV installation

This directory contains the installation documentation for DyCoV.
It describes how to make DyCoV available on a system before executing any workflows.

Installation is a prerequisite for using DyCoV, but it is **not a tutorial
workflow itself**. Once DyCoV is installed, usage is covered by the tutorials
in `../tutorials/`.

---

## Supported installation methods

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
- supports both Linux natively and Windows environments via WSL or Docker Desktop

See: [Using the provided image](using_the_provided_image.md)

---

### 2. Native Linux installation (advanced users only)

DyCoV can also be installed directly on a native Linux system without using the
prebuilt image.

In this mode:
- DyCoV is installed inside a user‑level Python virtual environment,
- Dynawo is automatically downloaded and installed as part of the DyCoV installation process,
- system‑level prerequisites (Python ≥ 3.13, uv, LaTeX, build tools) must be
  installed manually by the user.

This method is intended for **advanced users** who require full control over
their system environment.

See: [Linux native](linux_native.md)

---

## Next steps

After completing one of the installation procedures above, continue with the
user-facing tutorials to start using DyCoV:

See: [Reading guide](../tutorials/README.md)