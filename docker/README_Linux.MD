# Dycov Docker Container

This directory contains the Dockerfile and auxiliary scripts to build, run, and distribute a Docker container for the Dycov application.

This guide assumes you are running commands from within the `docker/` directory of the repository.

## 1. Prerequisites

Before you begin, ensure you have the following tools installed on your host machine:

* **Docker:** To build and run the container.
* **[uv](https://github.com/astral-sh/uv):** The Python package manager (required only if building from source).
* **A local installation of Dynawo:** Required only if building from source.

> **Tip:** If you have already run the standard `linux_install.sh` script, you already have a compatible Dynawo version installed in your installation folder (e.g., `$HOME/dycov/dynawo`). You can use that path.

## 2. Building the Docker Image

The build process uses `uv` to build the `dycov` Python package and bundles both your local Dynawo installation and the `examples` folder into the image.

### Using the Build Script

The `build.sh` script automates the process.

**Arguments:**
1.  **TAG:** The version tag for your new Docker image (e.g., `v0.8.1`).
2.  **DYNAWO_HOST_PATH:** The path to your local Dynawo installation directory.

**Example command:**

```bash
# Assuming you installed DyCoV in $HOME/dycov previously:
./build.sh v0.8.1 $HOME/dycov/dynawo
```

This script will:
1.  Build the Python wheel using `uv`.
2.  Copy the wheel, the `examples` folder, and Dynawo into the build context.
3.  Run `docker build`.
4.  Tag the image as `dycov:latest` and `dycov:<TAG>`.

## 3. Running the Container

Use the `run_dycov_docker.sh` script to launch the container. This script maps your work directory and ensures files created inside the container are owned by your host user.

**Example command:**

```bash
# Usage: ./run_dycov_docker.sh <WORK_DIR>
./run_dycov_docker.sh $HOME/dycov_projects
```

This will:
1.  Create a subdirectory `dycov_docker` inside your host path.
2.  Launch the container.
3.  Map that subdirectory to the container's home.
4.  Log you in as a user matching your host UID/GID.
5.  **Auto-copy Examples:** On the first run, the tool will copy the `examples` folder to `~/examples` inside the container so you can start working immediately.

## 4. Distributing the Image (No-Build Mode)

If you need to move the tool to a machine that does not have internet access or build dependencies (like `uv`), use the provided export/import scripts.

### Step A: Export (On the Build Machine)
Run this on the machine where you successfully built the image.

```bash
./export_image.sh
```
This creates a compressed file named `dycov_image.tar.gz`.

### Step B: Transfer
Copy the following files to the target machine:
1.  `dycov_image.tar.gz`
2.  `import_image.sh`
3.  `run_dycov_docker.sh`

### Step C: Import (On the Target Machine)
Run the import script to load the image into Docker.

```bash
./import_image.sh
```

Once imported, you can run the tool using `run_dycov_docker.sh` as described in Section 3.