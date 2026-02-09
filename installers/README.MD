# Dycov: Installation and User Guide

This document serves as a complete step-by-step guide for installing, configuring, and running the tool.

This guide is divided into three main sections:
1.  **Prerequisites:** What files you need before starting.
2.  **Installation:** How to set up the tool (Docker or Linux Native).
3.  **GFM Configuration & Usage:** How to configure the physics/scenarios and run simulations.

---

## 1. Prerequisites and Downloads

Before attempting any installation, ensure you have the necessary files. These are provided in the **Releases** section of the repository or sent by the distribution team.

You must have the following three files in a single folder on your computer:

* **dycov_dist.tar.gz**: This is the main application package. It is a large file containing the tool and all its dependencies.
* **import_image.sh**: A script required to load the application into Docker correctly.
* **run_dycov_docker.sh**: The script you will use to launch the tool daily.

> **Note:** Do not try to extract the .tar.gz file manually. The scripts will handle it.

---

## 2. Installation Methods

There are two ways to install Dycov. **Method A (Docker)** is highly recommended because it guarantees the tool runs in a controlled environment compatible with Windows and Linux, without library conflicts.

### Method A: Docker Installation (Recommended)

Follow these steps exactly in order.

#### Step 1: Prepare the Scripts
By default, Linux prevents scripts from running for security reasons. You must grant them "execution permissions".
Open your terminal in the folder where you downloaded the files and run:

```bash
chmod +x import_image.sh
chmod +x run_dycov_docker.sh
```

#### Step 2: Import the Application Image
You need to load the `dycov_dist.tar.gz` file into your Docker system.
**Important:** Do not use the standard `docker load` command. You must use the provided script because it restores critical configuration settings (Metadata) that are specific to this tool.

Run the following command:

```bash
./import_image.sh dycov_dist.tar.gz
```

*If you receive a "Permission denied" error regarding the docker socket, try running it with sudo:*

```bash
sudo ./import_image.sh dycov_dist.tar.gz
```

#### Step 3: Run Dycov
To use the tool, you will "enter" the Docker container.
A common issue users face is that files created inside Docker are locked (owned by the `root` user). To prevent this, we will tell Docker to use your current User ID.

1.  Create a folder where you will store your simulation projects (e.g., `my_dycov_work`):
    ```bash
    mkdir my_dycov_work
    ```

2.  Launch the tool mapping your user ID and group ID:
    ```bash
    ./run_dycov_docker.sh -u $(id -u) -g $(id -g) my_dycov_work/
    ```

**Explanation of the command:**
* `-u $(id -u)`: Tells Dycov to run as your current user ID.
* `-g $(id -g)`: Tells Dycov to run as your current group ID.
* `my_dycov_work/`: This is the folder that will be accessible inside the tool.

Once the command finishes, your terminal prompt will change. You are now inside Dycov and ready to run simulations.

---

### Method B: Linux Native Installation (Advanced)

If you cannot use Docker and have a compatible Linux operating system (e.g., Ubuntu, Debian), you can install the tool directly.

1.  Download the `linux_install.sh` script from the repository.
2.  Make it executable and run it:
    ```bash
    chmod +x linux_install.sh
    ./linux_install.sh
    ```
    *The script will automatically download the Dynawo solver, create a Python virtual environment, and install all dependencies.*

3.  Every time you want to use the tool, you must activate the environment:
    ```bash
    source dycov/activate_dycov
    ```

---

## 3. GFM Configuration and Usage Guide

This section explains how to configure the Grid Forming (GFM) simulations. Users often need to modify physical parameters, scenarios, or simulation times before running the tool.

### Key Configuration Files

All configuration files are located inside your example or project folder. You must edit these files using a text editor (like Notepad, VS Code, or Nano) **before** running the command.

| File Name | Purpose | What to Modify |
| :--- | :--- | :--- |
| **Producer.ini** | Physical Generator Parameters | Modify this file to change physical constants such as Inertia (H) or Damping (D). |
| **config.alias** | Operating Point | Edit this file to change the initial Operating Conditions (Voltage, Power, etc.) for the simulation. |
| **PCS_*.ini** | PCS Scenarios | There is one file per PCS scenario (e.g., `PCS_RTE-IGFM1.ini`). Edit these to change specific control scenarios. |
| **config.ini** | Global Settings | Modify the `SCR` (Short Circuit Ratio) value here. Look for `SCRmax` or similar variables. |

### Important Note on Units
Please be extremely careful when reading or editing the **PCS Description.ini** files. There is a difference between the internal calculation units and the display units.

* **Internal Calculations:** The tool uses **Radians per second (rad/s)** for calculations.
* **Plots and Legends:** The output graphs often display **Degrees (°)** for readability.

**Example Calculation:**
If you see a formula like `DeltaPhase = 0.3 * (Xeff + 1/SCRmax)`, ensure you understand that `DeltaPhase` is being calculated for the solver (likely in rads) even if the final plot shows degrees.

---

## 4. Running a Simulation

Once you have edited your configuration files (`Producer.ini`, `config.ini`, etc.), you are ready to generate the envelopes.

1.  Ensure you are inside the Docker container (or have activated the Linux environment).
2.  Navigate to your working directory.
3.  Run the generation command.

**Standard Command:**
```bash
dycov generateEnvelopes -i GFM_Fusion/Producer.ini -e -o ../Envelopes/Fusion
```

**Command Breakdown:**
* `dycov generateEnvelopes`: The main command to start the process.
* `-i GFM_Fusion/Producer.ini`: The **Input** file. This points to your main producer configuration.
* `-e`: Enables the "Envelope" calculation mode.
* `-o ../Envelopes/Fusion`: The **Output** directory where the results and plots will be saved.

---

## Troubleshooting

**Problem: "Permission Denied" when trying to open result files.**
* **Cause:** You likely ran the Docker container without specifying your user ID. The files were created by `root`.
* **Solution:**
    1.  Exit the container.
    2.  Run `sudo chown -R $USER:$USER my_dycov_work/` to fix current file permissions.
    3.  Next time, always use the `-u $(id -u)` and `-g $(id -g)` flags as shown in the Installation Step 3.

**Problem: "Image dycov:latest not found"**
* **Cause:** You skipped the import step.
* **Solution:** Run `./import_image.sh dycov_dist.tar.gz` before trying to start the tool.
