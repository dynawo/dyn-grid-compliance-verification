# Dycov Deployment Guide for Windows (WSL2)

This guide explains how to set up the environment from scratch, transfer a pre-built `dycov:latest` Docker image, and run it on a Windows machine using WSL2 (Windows Subsystem for Linux).

This workflow avoids installing complex build dependencies on Windows by using a pre-packaged Docker image.

## 1. Prerequisites: Setting Up Your Environment

Before handling the files, you must enable Linux support on your Windows machine.

### Step 1.1: Install WSL2
1.  Open the **PowerShell** application as **Administrator**.
2.  Run the following command:
    ```powershell
    wsl --install
    ```
3.  **Restart your computer**.
4.  After restarting, a terminal window will open automatically. It will ask you to create a **UNIX username** and **password**. Follow the prompts (note: the password will not appear on screen while typing).

### Step 1.2: Install Docker Desktop
1.  Download and install **Docker Desktop for Windows**.
2.  During installation, ensure the **"Use WSL 2 based engine"** option is checked.
3.  Once installed, open Docker Desktop, go to **Settings (gear icon) -> Resources -> WSL Integration**.
4.  Ensure the toggle for your Linux distribution (e.g., "Ubuntu") is turned **ON**.

## 2. The Deployment Files

You need the following files on your Windows machine (e.g., in a folder named `Dycov` on your Desktop):

1.  **`dycov_image.tar.gz`**: The compressed Docker image.
2.  **`import_image.sh`**: The script to load the image into Docker.
3.  **`run_dycov_docker.sh`**: The script to launch the container.

## 3. Step-by-Step Deployment

### Step 1: Open the WSL Terminal
Open the "Ubuntu" application from your Windows Start menu. You are now in the Linux command line.

### Step 2: Navigate to your Windows Files
In WSL, your Windows drives are mounted under `/mnt`. To go to the folder created in Section 2 (assuming it is on your Desktop):

```bash
# Replace 'YOUR_USER' with your actual Windows username
cd /mnt/c/Users/YOUR_USER/Desktop/Dycov
```

### Step 3: Sanitize the Scripts (Crucial for Windows)
Windows and Linux use different codes for line breaks. If you try to run scripts copied directly from Windows, they may fail.

1.  Install the conversion tool:
    ```bash
    sudo apt-get update && sudo apt-get install -y dos2unix
    ```
2.  Convert the scripts to Linux format:
    ```bash
    dos2unix *.sh
    ```
3.  Make the scripts executable:
    ```bash
    chmod +x *.sh
    ```

### Step 4: Import the Image
Run the import script to load the Docker image layers into your local system:

```bash
./import_image.sh
```
*This process loads the image from `dycov_image.tar.gz`.*

### Step 5: Run the Container
You can now launch the tool. You must specify a "Work Directory" (a folder on your host machine that the container can read/write to).

To use the current folder (`.`) as your workspace:

```bash
./run_dycov_docker.sh .
```

* **What happens next?** The script will map your user permissions and log you into the container.
* **Accessing Examples:** The `examples` folder is automatically copied to `~/examples` inside the container for immediate use.

### Step 6: Exiting
To close the session and stop the container, simply type:
```bash
exit
```