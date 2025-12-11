# Dycov Docker Container

This directory contains the Dockerfile and auxiliary scripts to build and run a Docker container for the Dycov application.

This guide assumes you are running commands from within the `docker/` directory of the repository.

## 1. Prerequisites

Before you begin, ensure you have the following tools installed on your host machine:

* **Docker:** To build and run the container.
* **[uv](https://github.com/astral-sh/uv):** The Python package manager.
* **A local installation of Dynawo:** You must have a complete Dynawo installation directory available on your host machine.

> **Tip:** If you have already run the standard `linux_install.sh` script, you already have a compatible Dynawo version installed in your installation folder (e.g., `$HOME/dycov/dynawo`). You can use that path.

## 2. Building the Docker Image

The build process uses `uv` to build the `dycov` Python package and bundles your local Dynawo installation into the image.

### Using the Build Script (Linux/macOS)

The `build.sh` script automates the process. It builds the wheel and creates the Docker image.

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
2.  Copy the wheel, examples, and Dynawo into the build context.
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