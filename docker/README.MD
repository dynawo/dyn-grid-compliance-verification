# Dycov Docker Container

This directory contains the Dockerfile and auxiliary scripts to build and run a Docker container for the Dycov application.

This guide assumes you are running commands from within the `docker/` directory of the repository.

## 1. Prerequisites

Before you begin, ensure you have the following tools installed on your host machine:

* **Docker:** To build and run the container.
* **[uv](https://github.com/astral-sh/uv):** The Python package manager and builder.
* **A local installation of Dynawo:** You must have a complete Dynawo installation directory available on your host machine. The build script will copy this directory into the Docker image.

## 2. Building the Docker Image

The new build process uses `uv` to build the `dycov` Python package and bundles your local Dynawo installation into the image.

### Using the Build Script (Linux/macOS)

The `build.sh` script automates the entire process. It requires two arguments:
1.  **TAG:** The version tag for your new Docker image (e.g., `v1.1`).
2.  **DYNAWO_HOST_PATH:** The absolute or relative path to your local Dynawo installation directory. This is the directory that contains the `dynawo/dynawo.sh` executable.

**Example command:**

```bash
# Usage: ./build.sh <TAG> <PATH_TO_DYNAWO>
./build.sh v1.1 ../../Dynawo/Dynawo_omc_v1.8.0/dynawo/dynawo.sh
```

This script will:
1.  Navigate to the project's root and use `uv build` to create the Python wheel in the `dist/` directory.
2.  Copy the new wheel, the `examples/` directory, and your entire Dynawo installation into the `docker/` (build context) directory.
3.  Run `docker build`, passing the package name and directory names as build arguments.
4.  Tag the new image as `dycov:latest` and `dycov:<TAG>`.
5.  Clean up the copied files from the `docker/` directory.

## 3. Running the Container

Use the provided `run_dycov_docker.sh` script to easily launch and manage the container. This script handles mapping your work directory and, most importantly, ensuring that files created inside the container are owned by you on the host.

### Using the Run Script (Linux/macOS)

The script requires one argument: the path to your working directory on the host machine.

**Example command:**

```bash
# Usage: ./run_dycov_docker.sh <WORK_DIR>
./run_dycov_docker.sh $HOME/dycov_projects
```

This script will:
1.  Create a subdirectory named `dycov_docker` inside your specified `<WORK_DIR>`.
2.  Launch the `dycov:latest` container.
3.  Mount `$HOME/dycov_projects/dycov_docker` to the user's home directory (`/home/myuser`) inside the container.
4.  Create a new user inside the container with the same User ID (UID) and Group ID (GID) as your host user.
5.  Drop you into an interactive shell (`bash`) as that user.

Any files you save in your home directory inside the container will appear in `$HOME/dycov_projects/dycov_docker` on your host.