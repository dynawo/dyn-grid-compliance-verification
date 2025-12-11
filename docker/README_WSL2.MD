# Dycov Deployment Guide for WSL2 (Using a Pre-Built Image)

This guide explains how to transfer a pre-built `dycov:latest` Docker image from a Linux machine and run it on a Windows machine using WSL2.

## 1. Prerequisites: Setting Up Your WSL2 Environment

* **WSL2:** Open PowerShell as Administrator and run `wsl --install`.
* **Docker Desktop for Windows:** Ensure you **enable the "Use WSL2 based engine"** option in settings.

## 2. The Deployment Files

You require **one** script to run the container on Windows:

1.  **`run_dycov_docker.sh`:** The wrapper script found in this directory.

## 3. Step-by-Step Deployment

### Step 1: Export the Image (On your Linux build machine)

Run this on the machine where you successfully built the image using `build.sh`.

```bash
docker save dycov:latest | gzip > dycov_image.tar.gz
```

### Step 2: Transfer the Image (To your WSL2 machine)

Copy `dycov_image.tar.gz` and `run_dycov_docker.sh` to your Windows/WSL2 environment.

### Step 3: Import the Image (Inside your WSL2 terminal)

Open your WSL2 terminal (Ubuntu), navigate to the file location, and run:

```bash
docker load < dycov_image.tar.gz
```

Verify with `docker images`.

### Step 4: Prepare the Run Script

```bash
chmod +x run_dycov_docker.sh
```

### Step 5: Run the Container

```bash
# Usage: ./run_dycov_docker.sh <WORK_DIR>
./run_dycov_docker.sh $HOME/dycov_projects
```

This will launch the container. Data saved inside the container will persist in `$HOME/dycov_projects/dycov_docker` on your WSL2 filesystem.