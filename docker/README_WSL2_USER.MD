# Dycov Deployment Guide for Windows (WSL2)

This guide explains how to set up the Dycov tool on Windows. There are **two methods** to run this tool, depending on your system restrictions:

* **Method A (Standalone Bundle):** Recommended if you **cannot** install Docker Desktop. The Docker engine is embedded inside the download.
* **Method B (Docker Desktop):** Recommended if you already have Docker Desktop installed on your machine.

## 1. Prerequisites (Required for BOTH methods)

Before handling the files, you must enable Linux support on your Windows machine.

1.  Open the **PowerShell** application as **Administrator**.
2.  Run the following command:
    ```powershell
    wsl --install
    ```
3.  **Restart your computer**.

---

## 2. Choose Your Installation Method

### Method A: The Standalone Bundle (No Docker Desktop)

Use this method if you do not have Docker Desktop.

**Step 1: Download the Bundle**
Download the file `DycovBundle.tar` from the **Releases** section of this repository.

**Step 2: Import the Environment**
1.  Create a folder where the Linux system will live (e.g., `C:\DycovLinux`).
2.  Move the downloaded `DycovBundle.tar` to a known location (e.g., your Downloads folder).
3.  Open PowerShell and run:
    ```powershell
    # Syntax: wsl --import <Name> <InstallLocation> <PathToTar>
    wsl --import DycovApp C:\DycovLinux "C:\Users\YourUser\Downloads\DycovBundle.tar"
    ```

**Step 3: Enter the Environment**
To start the tool environment, run:
```powershell
wsl -d DycovApp
```

**Step 4: Start Internal Docker**
Since you don't have Docker Desktop, you must manually start the engine inside the window that just opened:
```bash
sudo service docker start
```

**Step 5: Run Dycov**
Navigate to the scripts folder (or wherever the scripts are placed) and run:
```bash
./run_dycov_docker.sh .
```

---

### Method B: Docker Desktop Integration

Use this method if you have the file `dycov_image.tar.gz` and `import_image.sh`.

**Step 1: Install Docker Desktop**
1.  Download and install **Docker Desktop for Windows**.
2.  During installation, ensure **"Use WSL 2 based engine"** is checked.
3.  Open Docker Desktop settings: **Resources -> WSL Integration**. Ensure your Linux distro (e.g., Ubuntu) is turned **ON**.

**Step 2: Prepare the Scripts**
1.  Open your WSL terminal (Ubuntu).
2.  Navigate to the folder containing your Dycov scripts.
3.  Convert line endings (Windows fix) and make executable:
    ```bash
    sudo apt-get update && sudo apt-get install -y dos2unix
    dos2unix *.sh
    chmod +x *.sh
    ```

**Step 3: Import the Image**
Run the import script to load the Docker image:
```bash
# From a local file
./import_image.sh

# OR from a URL
./import_image.sh --url "https://link-to-release/dycov_image.tar.gz"
```

**Step 4: Run Dycov**
To run the container using the current directory as the workspace:
```bash
./run_dycov_docker.sh .
```

---

## 3. Usage & Examples

Once the tool is running (regardless of the method used above), you will be inside the container.

* **Work Directory:** The script maps your current host directory to the container. Any file you save inside the container's working directory will appear on your Windows machine.
* **Examples:** A set of examples is automatically copied to `~/examples` inside the container.

To exit the session and stop the container:
```bash
exit
```