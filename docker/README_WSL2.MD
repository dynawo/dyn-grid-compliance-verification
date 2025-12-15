# Dycov Deployment Guide for WSL2 (Using a Pre-Built Image)

This guide explains how to transfer a pre-built `dycov:latest` Docker image from a Linux machine and run it on a Windows machine using WSL2.

This workflow is much faster than building the image from scratch and avoids installing build dependencies on Windows.

## 1. Prerequisites: Setting Up Your WSL2 Environment

* **WSL2:** Open PowerShell as Administrator and run `wsl --install`.
* **Docker Desktop for Windows:** Ensure you **enable the "Use WSL2 based engine"** option in settings.

## 2. The Deployment Files

You require the following files on your Windows/WSL2 machine:

1.  **`dycov_image.tar.gz`:** The exported image file.
2.  **`import_image.sh`:** The script to load the image.
3.  **`run_dycov_docker.sh`:** The script to run the container.

## 3. Step-by-Step Deployment

### Step 1: Export the Image (On your Linux build machine)

Run the export script on the machine where you successfully built the image.

```bash
./export_image.sh
```
This generates the `dycov_image.tar.gz` file.

### Step 2: Transfer the Files (To your WSL2 machine)

Copy `dycov_image.tar.gz`, `import_image.sh`, and `run_dycov_docker.sh` to your Windows/WSL2 environment (e.g., inside your user home directory).

### Step 3: Import the Image (Inside your WSL2 terminal)

Open your WSL2 terminal (Ubuntu), navigate to the folder where you copied the files, and run:

```bash
chmod +x import_image.sh run_dycov_docker.sh
./import_image.sh
```

This will load the `dycov:latest` image into your Docker Desktop instance.

### Step 4: Run the Container

You can now launch the container using the run script. It requires one argument: the path to your working directory on the host.

```bash
# Usage: ./run_dycov_docker.sh <WORK_DIR>
./run_dycov_docker.sh $HOME/dycov_projects
```

**Note:**
1.  This script will create a `dycov_docker` subdirectory inside your project folder.
2.  **Examples:** The `examples` folder will be automatically copied to your home directory inside the container upon launch, ready for use.