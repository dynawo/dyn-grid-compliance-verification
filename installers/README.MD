# Dycov: Installation and User Guide

Welcome to Dycov (Dynamic Coverage Tool). This document serves as a complete, step-by-step guide for installing, configuring, and running the tool.

## Installation Overview

There are **four ways** to install Dycov depending on your Operating System and preferences. Please verify which files you have before starting.

| Method | OS | Required Files | Description |
| :--- | :--- | :--- | :--- |
| **1. Windows WSL** | Windows | `dycov_rawimage.tar.gz`, `import_wsl.bat`, `import_wsl.ps1`, `run_dycov_wsl.ps1` | **No Docker.** Runs as a standalone App inside the Windows Subsystem for Linux (WSL). |
| **2. Windows Docker** | Windows | `dycov_rawimage.tar.gz` | Runs inside Docker Desktop. Requires familiarity with PowerShell. |
| **3. Linux Native** | Linux | `linux_install.sh` | **No Docker.** Automatically downloads Dynawo and installs Dycov directly into your system. Requires internet. |
| **4. Linux Docker** | Linux | `dycov_rawimage.tar.gz`, `import_image.sh`, `run_dycov_docker.sh` | Runs inside a secure container using the provided helper scripts. Recommended for servers. |

---

## 1. Prerequisites (Check your files)

Before starting, create a clean folder on your computer (e.g., `Dycov_Install/`) and place the required files there.

**If using Method 1 (Windows WSL):**
Download the following files from the Release page and place them in the same folder:
* `dycov_rawimage.tar.gz` (The heavy application package; do not unzip this manually).
* `import_wsl.bat` (Double-click installer — starts the installation process).
* `import_wsl.ps1` (Installation logic, called automatically by `import_wsl.bat`).
* `run_dycov_wsl.ps1` (Launcher, called automatically by the desktop shortcut).

**If using Method 2 (Windows Docker):**
* `dycov_rawimage.tar.gz`

**If using Method 3 (Linux Native):**
* `linux_install.sh`
* *Requirement:* You must have an active internet connection so the script can download Dynawo and Python dependencies.

**If using Method 4 (Linux Docker):**
* `dycov_rawimage.tar.gz`
* `import_image.sh`
* `run_dycov_docker.sh`

---

## 2. Installation Instructions

Choose **ONE** of the following methods that best fits your environment.

### Method 1: Windows via Standalone WSL (No Docker)
*Best for: Windows users without Docker Desktop. This installs Dycov as a separate "App" in your Windows Subsystem for Linux.*

**Step 1: Install**
Place all four required files in the same folder. Then **double-click `import_wsl.bat`**.

The installer will:
* Import `dycov_rawimage.tar.gz` as a WSL distribution named `DycovApp`.
* Create a **Desktop shortcut** and a **Start Menu entry** named `Dycov`.

*Note: If Windows asks whether to allow the script to run, click Yes.*

**Step 2: Run**
Double-click the `Dycov` shortcut on your Desktop (or find it in the Start Menu).

The tool will start an interactive Linux session. Your Windows drives are accessible from inside the session via `/mnt/c/`, `/mnt/d/`, etc.

---

### Method 2: Windows via Docker Desktop
*Best for: Windows users who already use Docker Desktop and are comfortable with PowerShell.*

**Step 1: Import (PowerShell)**
Open PowerShell in the folder containing `dycov_rawimage.tar.gz`. You need to import the image while manually restoring the configuration.
*Tip: Be careful when copy-pasting. Ensure the backslashes before the quotes (`\"`) are preserved.*

```powershell
# 1. Define variables with escaped quotes (Crucial for PowerShell)
$DycovPath = 'ENV PATH=\"/opt/dynawo_install/dynawo:/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"'
$DycovEntry = 'ENTRYPOINT [\"/start_dycov.sh\"]'

# 2. Import the image applying the changes
docker import --change $DycovPath --change $DycovEntry .\dycov_rawimage.tar.gz dycov:latest
```

**Step 2: Run**
Launch the container mapping your current directory (`${PWD}`) so the tool can see your files.
```powershell
docker run --rm -it -v "${PWD}:/home/dycov_user" -w /home/dycov_user dycov:latest
```

---

### Method 3: Linux Native (Automatic Installer)
*Best for: Linux users who want a standard installation without using Docker containers.*

1.  Download `linux_install.sh` to your folder.
2.  Give it execution permissions and run it:
    ```bash
    chmod +x linux_install.sh
    ./linux_install.sh
    ```
    *What this does:* The script will create a local `dycov` folder, download the correct version of the Dynawo application, set up a private Python virtual environment, and install the tool.

3.  **To use the tool:** Since this is a local installation, you must "activate" the tool every time you open a new terminal window:
    ```bash
    source dycov/activate_dycov
    ```
    (You will see `(dycov)` appear in your terminal prompt when active).

---

### Method 4: Linux via Docker
*Best for: Linux servers or users who prefer isolated containers to keep their system clean.*

**Step 1: Permissions**
Linux blocks scripts by default. Grant execution permissions to the helper scripts:
```bash
chmod +x import_image.sh
chmod +x run_dycov_docker.sh
```

**Step 2: Import the Image**
You must use the provided script instead of the standard `docker load`. This script restores critical metadata (like the ENTRYPOINT) that allows the tool to run automatically.
```bash
./import_image.sh dycov_rawimage.tar.gz
```

**Step 3: Run**
When running Docker on Linux, files created by the container often belong to the "root" user, making them impossible to delete or edit later. To fix this, we map your user ID into the container.

```bash
# 1. Create a folder for your simulation projects if you haven't already
mkdir my_project

# 2. Run the tool mapping your current User ID (-u) and Group ID (-g)
./run_dycov_docker.sh -u $(id -u) -g $(id -g) my_project/
```

---

## 3. GFM Configuration & Usage

Users typically want to use the GFM (Grid Forming) capabilities. This requires configuring specific files **before** running the simulation commands.

### Key Configuration Files
When you prepare a study in your working directory (e.g., inside `examples/`), you will see several `.ini` files. Here is what they control:

| File | Purpose | Detailed Description |
| :--- | :--- | :--- |
| **`Producer.ini`** | Physical Parameters | This represents the physical generator. Modify values here for **H** (Inertia), **D** (Damping), and other machine constants. |
| **`config.alias`** | Operating Conditions | This file maps variable names to values. Modify this to change the initial **Active Power (P)**, **Voltage (U)**, or **Reactive Power (Q)** for the simulation start point. |
| **`PCS_*.ini`** | Control Scenarios | Defines specific control scenarios (e.g., `PCS_RTE-IGFM1.ini`). Edit these files to change parameters specific to the controller logic. |
| **`config.ini`** | Global Config | **Critical:** This is where you set the grid strength. Look for **`SCRmax`** (Short Circuit Ratio) to adjust the grid stiffness. |

### Advanced Configuration (Source Code)
* **Simulation Time:** The duration of the simulation is currently hardcoded in the source file `src/dycov/gfm/constants.py`.
* *Warning:* If you are using Docker or WSL (Methods 1, 2, 4), this file is inside the image. You cannot easily edit it. If you need longer simulations, please request a parameter update. If using Method 3 (Linux Native), you can edit this file directly in your installation folder.

### A Note on Units ⚠️
Please be extremely careful with unit definitions in the `PCS Description.ini` files.
* **Internal Calculation:** The solver always uses **Radians per second (rad/s)**.
* **Plots/Legend:** The output graphs often convert this to **Degrees (°)** for readability.
* *Example:* If you see a formula like `DeltaPhase = ...`, ensure the inputs match the expected units (rad vs deg).

---

## 4. Running a Simulation

Once you have edited your configuration files, you are ready to generate the results (envelopes).

**Standard Command:**
```bash
dycov generateEnvelopes -i GFM_Fusion/Producer.ini -e -o ../Envelopes/Fusion
```

**Command Breakdown:**
* `dycov generateEnvelopes`: The command to start the Grid Forming calculation module.
* `-i GFM_Fusion/Producer.ini`: The **Input**. This must point to your main `Producer.ini` file.
* `-e`: This flag tells the tool to calculate the "Envelopes" (the min/max boundaries).
* `-o ../Envelopes/Fusion`: The **Output**. Specifies the folder where the results (CSV files and Plots) will be saved.

**Troubleshooting Permissions (Docker users):**
If you see "Permission Denied" when trying to open the result files after the simulation:
1.  Run this command in your host terminal (outside Docker) to reclaim ownership:
    ```bash
    sudo chown -R $USER:$USER my_project_folder/
    ```
2.  Next time, remember to use `-u $(id -u)` when launching the container (see Method 4).

---

## 5. Dynawo PAR generation utility (from Excel)

Every installation ships a small standalone utility that turns an Excel model
specification into two Dynawo PAR fragments (`zone1.par` and `zone3.par`), ready
to paste into your models. It only extracts and formats parameters — it does not
validate or interpret the model.

**Where it is:**
* Methods 1, 2, 4 (WSL / Docker): `~/tools/dynawo_par/`
* Method 3 (Linux Native): `dycov/tools/dynawo_par/` (inside your install folder)
* It is also available as a direct download, `dycov_par_tool.zip`, on the Release page.

**How to run it** (no extra dependencies — any Python 3 works):
```bash
python ~/tools/dynawo_par/generate_par.py --excel my_model.xlsx
```
This writes `zone1.par` and `zone3.par` next to the Excel file (or use
`--outdir DIR`). A worked example is included at
`tools/dynawo_par/examples/WECCSample.xlsx`, and full details are in
`tools/dynawo_par/README.md`.

---

## 6. Native Windows installation for developers (not recommended)

> [!WARNING]
> Native Windows execution is not recommended because Dynawo, LaTeX tools, and several
> system-level dependencies are Linux-oriented.
> Use this option only if you cannot use WSL or Docker.

If you still prefer to set up DyCoV natively in Windows:

1.  Clone the Repository using your favorite Git client (e.g., GitHub Desktop or `git-scm`).
    ```bash
    git clone https://github.com/dynawo/dyn-grid-compliance-verification dycov_repo
    cd dycov_repo
    ```

2.  Ensure you have `uv` installed. You can install it via pip:
    ```bash
    pip install uv
    ```

3.  Set up the virtual environment and install dependencies.
    - Open a **CMD terminal** or **PowerShell**.
    - Navigate to the root folder of the cloned repository.
    - Create a new virtual environment:
      ```winbatch
      uv venv dycov_venv
      ```
    - Activate the virtual environment:
      ```winbatch
      dycov_venv\Scripts\activate
      ```
    - Install the package in editable mode with all development and test dependencies:
      ```winbatch
      uv pip install -e .[dev,test]
      ```

4.  Verify Installation. This should display the help message for the tool.
    ```winbatch
    dycov -h
    ```

5.  Pre-Execution Compilation. Before running the tool for the first time, compile the tool's resources:
    ```winbatch
    dycov compile
    ```

The DyCoV application is now ready for development.