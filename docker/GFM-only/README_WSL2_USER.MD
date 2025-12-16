# Dycov (GFM-only) Deployment Guide for Windows

This guide explains how to set up the **GFM-only** version of the Dycov tool on Windows. There are **two methods** to run this tool:

* **Method A (Standalone Bundle):** Recommended if you **cannot** install Docker Desktop.
* **Method B (Docker Desktop):** Recommended if you already have Docker Desktop installed.

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
Download the file `DycovGFMBundle.tar` from the **Releases** section of this repository.

**Step 2: Import the Environment**
1.  Create a folder where the Linux system will live (e.g., `C:\DycovGFM`).
2.  Move the downloaded `DycovGFMBundle.tar` to a known location (e.g., Downloads).
3.  Open PowerShell and run:
    ```powershell
    # Syntax: wsl --import <Name> <InstallLocation> <PathToTar>
    wsl --import DycovGFMApp C:\DycovGFM "C:\Users\YourUser\Downloads\DycovGFMBundle.tar"
    ```

**Step 3: Enter the Environment**
To start the tool environment, run:
```powershell
wsl -d DycovGFMApp
```

**Step 4: Start Internal Docker**
Since you don't have Docker Desktop, you must manually start the engine inside the window that just opened:
```bash
sudo service docker start
```

**Step 5: Run Dycov**
Navigate to the scripts folder and run:
```bash
./run_dycov_docker.sh .
```

---

### Method B: Docker Desktop Integration

Use this method if you have the file `dycov_image_GFM-only.tar.gz` and the scripts.

**Step 1: Install Docker Desktop**
1.  Install **Docker Desktop for Windows**.
2.  Ensure **"Use WSL 2 based engine"** is checked.
3.  In Docker Settings -> **Resources -> WSL Integration**, ensure your Linux distro (e.g., Ubuntu) is turned **ON**.

**Step 2: Prepare the Scripts**
1.  Open your WSL terminal (Ubuntu).
2.  Navigate to the folder containing your Dycov GFM scripts.
3.  Convert line endings (Windows fix) and make executable:
    ```bash
    sudo apt-get update && sudo apt-get install -y dos2unix
    dos2unix *.sh
    chmod +x *.sh
    ```

**Step 3: Import the Image**
Run the import script to load the GFM-only image:
```bash
# From a local file
./import_image.sh

# OR from a URL
./import_image.sh --url "https://link-to-release/dycov_image_GFM-only.tar.gz"
```

**Step 4: Run Dycov**
To run the container using the current directory as the workspace:
```bash
./run_dycov_docker.sh .
```

---

## 3. Usage & Examples

Once the tool is running, you will be inside the container `dycov-gfm-only`.

* **Work Directory:** The script maps your current host directory to the container.
* **Examples:** A set of examples is automatically copied to `~/examples` inside the container.

To exit the session and stop the container:
```bash
exit
```