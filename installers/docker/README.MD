# Dycov: Dynamic Coverage Tool

This guide explains how to install and run the Dycov tool. There are three installation methods using the single distribution file.

## Installation Methods

| Option | OS | Method | Description |
| :--- | :--- | :--- | :--- |
| **1. Linux Native** | Linux | Docker | Standard usage on Linux machines. |
| **2. Docker Desktop** | Windows | Docker | Standard usage on Windows with Docker Desktop. |
| **3. WSL Standalone** | Windows | WSL Import | **No Docker required.** Runs directly as a WSL app. |

---

## Artifact Required
You need the file: **`dycov_dist.tar.gz`** (and the scripts).

---

## Option 1: Linux Native (Docker)

1.  **Import the Image:**
    Since the distribution file is a flat filesystem, you **must** use the import script to restore it properly into Docker:
    ```bash
    chmod +x import_image.sh
    ./import_image.sh dycov_dist.tar.gz
    ```

2.  **Run the Tool:**
    ```bash
    ./run_dycov_docker.sh .
    ```

---

## Option 2: Windows via Docker Desktop

**Prerequisites:** Docker Desktop installed.

1.  **Import the Image (PowerShell):**
    You cannot use `docker load`. You must run the import command manually to restore the configuration (PATH and ENTRYPOINT) which are stripped during the export process.
    
    Paste the following commands in PowerShell (in the folder containing the `.tar.gz`):
    ```powershell
    # 1. Define the environment variables to match the Linux configuration
    $DycovPath = 'ENV PATH="/opt/dynawo_install/dynawo:/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"'
    $DycovEntry = 'ENTRYPOINT ["/start_dycov.sh"]'

    # 2. Import the image applying the changes
    docker import --change $DycovPath --change $DycovEntry .\dycov_dist.tar.gz dycov:latest
    ```

2.  **Run the Tool:**
    ```powershell
    docker run --rm -it -v "${PWD}:/home/dycov_user" -w /home/dycov_user dycov:latest
    ```

---

## Option 3: Windows via Standalone WSL (No Docker)

Use this method to install Dycov as its own Linux distribution. **You do not need Docker Desktop installed.**

**1. Install as WSL App:**
1.  Open **PowerShell**.
2.  Create an install folder (e.g., `C:\DycovApp`).
3.  Import the distribution:
    ```powershell
    # Syntax: wsl --import <Name> <InstallLocation> <PathToTarGz>
    wsl --import DycovApp C:\DycovApp "C:\Path\To\dycov_dist.tar.gz"
    ```

**2. Run the Tool:**
To start the tool, simply launch the distribution:
```powershell
wsl -d DycovApp --exec /start_dycov.sh
```

*Note: The first time you run it, it may ask to configure the user. Follow the prompts.*