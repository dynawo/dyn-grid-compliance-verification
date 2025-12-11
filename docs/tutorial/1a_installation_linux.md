===========================

TUTORIAL

HOW TO INSTALL ON LINUX SO

(c) 2023&mdash;25 RTE  
Developed by Grupo AIA

===========================

--------------------------------------------------------------------------------

#### Table of Contents

1. [Overview](#Overview)
2. [Install Dynawo](#Install-Dynawo)
3. [System Requirements](#System-Requirements)
4. [Installation](#Installation)
5. [Build and install (for developers)](#build-and-install-for-developers)

## Overview

Dynamic grid Compliance Verification is developed in `Python` and requires 
**Python 3.9+**. It relies on several third-party libraries which will be 
automatically installed along with the tool when using the installation script.

## Install Dynawo (Optional)
The tool requires Dynawo (v1.7.0 or later, Nightly build) to run simulations.

**The installation script (step 4) can automatically download and install Dynawo for you.** Unless you have a specific reason to manage Dynawo manually (e.g., you already have it 
installed globally), you can skip this step and let the installer handle it.

If you prefer to install it manually, follow the steps provided in the 
[official software repository](https://github.com/dynawo/dynawo) or 
on the [official page](https://dynawo.github.io/install/).
Remember to install its system dependencies:

```bash
apt install curl unzip gcc g++ cmake
```

Finally, to verify that Dynawo has been installed correctly, you can use the following 
command:

```bash
dynawo.sh --version
```

## System Requirements

The OS-level requirements are quite minimal. You’ll need a recent Linux distribution, 
along with **LaTeX** and **Python**. We recommend using Debian 12 or later, or Ubuntu 
22.04 LTS or newer. A Windows version is planned to be released by the end of 2024.

For Debian/Ubuntu systems, the following packages need to be installed:

* **Install LaTeX packages** (for report generation):

    ```bash
    apt install texlive-base texlive-latex-base texlive-latex-extra \
                texlive-latex-recommended texlive-science texlive-lang-french \
                latexmk
    ```

* **Install Python 3.9 or higher**, including `pip` and the `venv` module:

    ```bash
    apt install python3-minimal python3-pip python3-venv git
    ```
    
 
* **Install xdg-utils (Optional)**: 
   This package includes `xdg-open`, which may not be installed by default. It is used 
   for opening automatically the PDF reports:

    ```
    apt install xdg-utils
    ```

## Installation

1. Run the following command:

   ```bash
   curl -L https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/v0.8.1/linux_install.sh | bash
   ```

   This script will:
   1. Create a directory named `dycov` in your current path.
   2. Download and install Dynawo inside it (if you confirm the prompt).
   3. Download the DyCoV source code.
   4. Create a virtual environment and install the package and dependencies using `uv`.

2. Next, you must activate the virtual environment using the **generated wrapper script**.
   This is crucial as it ensures the local Dynawo installation is found in your PATH: 
   ```bash
   source dycov/activate_dycov
   ```

3. The tool is used via a single command `dycov` having several subcommands. Quickly
   check that your installation is working by running the help option, which will show
   you all available subcommands:
   ```bash
   dycov -h
   ```
   
The DyCoV application is now ready to use.


## Build and install (for developers)

* **Clone the repository**:

    ```bash
    git clone https://github.com/dynawo/dyn-grid-compliance-verification dycov_repo
    cd dycov_repo
    ```

* **Install Dependencies**:
  Ensure you have `uv` installed (`pip install uv`).

* **Run the build script**:
  Run the `build_and_install.sh` script. This will create a virtual environment inside 
  the `dycov_venv` subdirectory, and install the tool along with all required 
  development dependencies.

    ```bash
    ./build_and_install.sh --devel
    ```

* **Activate the virtual environment**:

    ```bash
    source dycov_venv/bin/activate
    ```

    **Note:** The tool includes a built-in sanity check to ensure that all necessary system 
              requirements are installed, and will notify you if any are missing.
    

* **First run**:
The first time the tool is run from a clean state, a configuration folder will be created
in `$HOME/.config/dycov`. This process may take several minutes and will only need to be repeated 
if the Dynawo version is updated.

[Dynawo Official Page](https://dynawo.github.io/)

[Dynawo Grid Compliance Verification Repository](https://github.com/dynawo/dyn-grid-compliance-verification/)