# Dycov Deployment Guide for WSL2 (Using a Pre-Built Image)

This guide explains how to transfer a pre-built `dycov:latest` Docker image from a Linux machine and run it on a Windows machine using WSL2.

This workflow is much faster than building the image from scratch, but it requires you to have a machine where the image is already built.

## 1. Prerequisites: Setting Up Your WSL2 Environment

Before you begin, you must have the following tools installed and configured:

* **WSL2:** You must have WSL2 installed.
    * **How to Install:** Open a Windows PowerShell as Administrator and run `wsl --install`. This will install WSL2 and the default Ubuntu distribution.
* **Docker Desktop for Windows:**
    * **Crucial Configuration:** During installation, ensure you **enable the "Use WSL2 based engine"** option. This allows Docker to integrate directly with your Ubuntu (or other) Linux distribution.

## 2. The Deployment Files

This simplified process only requires **one** script to run the container:

1.  **`run_dycov_docker.sh`:** A wrapper script to conveniently run the container with the correct user permissions and volume mounts.

## 3. Step-by-Step Deployment

Follow these steps to transfer and run the image.

### Step 1: Export the Image (On your Linux build machine)

On the Linux machine where you built the image, run the following command in your terminal. This will save the `dycov:latest` image to a compressed file.

```bash
# This saves the image 'dycov:latest' and compresses it
docker save dycov:latest | gzip > dycov_image.tar.gz
```

### Step 2: Transfer the Image (To your WSL2 machine)

Move the `dycov_image.tar.gz` file from your Linux machine to your WSL2 environment on your Windows machine. You can use a USB drive, a network share, or `scp`.

Place the file somewhere accessible, like your WSL2 home directory.

### Step 3: Import the Image (Inside your WSL2 terminal)

Open your WSL2 (Ubuntu) terminal on Windows. Navigate to where you saved the image file and run `docker load`.

```bash
# Navigate to the file's location
cd /home/myuser/imports/

# This will load the image into your local Docker instance
docker load < dycov_image.tar.gz
```

After this command finishes, you can run `docker images` to verify that `dycov:latest` is now listed.

### Step 4: Prepare the Run Script

You only need the `run_dycov_docker.sh` script. Make sure it is executable. This is a one-time setup.

```bash
# Navigate to where your script is (e.g., your project's docker/ dir)
cd /path/to/your/project/docker/

# Make the script executable
chmod +x run_dycov_docker.sh
```

### Step 5: Run the Container

You can now launch the container using the same `run_dycov_docker.sh` script as before. It requires one argument: the path to your working directory on the host.

```bash
# Usage: ./run_dycov_docker.sh <WORK_DIR>
./run_dycov_docker.sh $HOME/dycov_projects
```

This script will:
1.  Create a subdirectory named `dycov_docker` inside `$HOME/dycov_projects`.
2.  Launch the `dycov:latest` container you just imported.
3.  Mount `$HOME/dycov_projects/dycov_docker` to the home directory inside the container.
4.  Create a new user inside the container with the same User ID (UID) and Group ID (GID) as your host user.

You are now running the container without having to build it.