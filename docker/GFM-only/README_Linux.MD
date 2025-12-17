# Dycov GFM-only Docker Container

This directory contains the Dockerfile and scripts to build the **GFM-only** version of the Dycov container (without Dynawo dependency).

This guide assumes you are running commands from within the `GFM-only/` directory.

## 1. Prerequisites

* **Docker:** To build and run the container.
* **[uv](https://github.com/astral-sh/uv):** The Python package manager.

## 2. Building the Docker Image

The build process uses `uv` to build the `dycov` Python package and bundles it into the image. **Dynawo is NOT included.**

### Using the Build Script

The `build.sh` script automates the process.

**Arguments:**
1.  **TAG:** The version tag for your new Docker image (e.g., `v0.8.1`).

**Example command:**

```bash
./build.sh v0.8.1
```

This script will:
1.  Build the Python wheel using `uv`.
2.  Run `docker build`.
3.  Tag the image as `dycov:latest` and `dycov:<TAG>`.

## 3. Running the Container

Use the `run_dycov_docker.sh` script to launch the container.

**Example command:**

```bash
# Usage: ./run_dycov_docker.sh <WORK_DIR>
./run_dycov_docker.sh $HOME/dycov_projects
```

This will launch `dycov:latest`.

## 4. Distributing the Image

### Step A: Export (On the Build Machine)
```bash
./export_image.sh
```
This creates `dycov_image_GFM-only.tar.gz`.

### Step B: Transfer
Copy `dycov_image_GFM-only.tar.gz`, `import_image.sh`, and `run_dycov_docker.sh` to the target machine.

### Step C: Import (On the Target Machine)
```bash
./import_image.sh
```