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
automatically installed along with the tool when using the `build_and_install.sh` 
script. However there are some required packages that should be installed manually.

## Install Dynawo
The first requirement to use the tool is to have Dynawo installed on your computer. 
To do so, follow the steps provided in the [official software repository](https://github.com/dynawo/dynawo) or 
on the [official page](https://dynawo.github.io/install/).

For optimal functionality of the package, Dynawo version v1.7.0 or later is required, 
which should be obtained from the **nightly** builds of the official repository 
(currently, as of September 2024, only available as a [Nightly release](https://github.com/dynawo/dynawo/releases)).

This must be the version with Open Modelica integrated.

It's important to remember that Dynawo requires a series of dependencies that can be 
installed with the following command:

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
along with `Dynawo` (and its dependencies), **LaTeX**, and **Python**. We recommend 
using Debian 12 or later, or Ubuntu 22.04 LTS or newer. A Windows version is planned 
to be released by the end of 2024.

For Debian/Ubuntu systems, the following packages need to be installed:

* **Install Dynawo** (v1.7.0 or later) and its necessary dependencies (previous step)

* **Install LaTeX packages**:

    ```bash
    apt install texlive-base texlive-latex-base texlive-latex-extra \
                texlive-latex-recommended texlive-science texlive-lang-french \
                make
    ```

* **Install Python 3.9 or higher**, including `pip` and the `venv` module:

    ```bash
    apt install python3.9-minimal python3-pip python3.9-venv
    ```
    
 
* **Install xdg-utils (Optional)**: 
   This package includes `xdg-open`, which may not be installed by default. It is used 
* for opening automatically the PDF reports:

    ```
    apt install xdg-utils
    ```

Note that this tool is also distributed as a Python package. Once installed, it, along 
with its dependencies, will be placed in a *Python virtual environment* inside your 
`$HOME` directory.

## Installation

1. Run the following command:

   ```bash
   curl https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/v0.8.1/linux_install.sh | bash
   ```

   This will download the lastest version of the Python package,
   create a Python virtual environment under the subdirectory `dycov_venv`, and
   install the package into it (together with all the necessary library 
   dependencies, such as NumPy, etc.).

2. Next, you must activate the virtual environment that has just been created: 
   ```bash
   source dycov_venv/bin/activate
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
    ```

    You can rename the top-level directory to something other than `"dycov_repo"` if you wish.

* **Navigate to the repository** and run the `build_and_install.sh` script. This will 
  build the Python package, create a virtual environment inside the `dycov_venv` 
  subdirectory, and install the tool along with all required dependencies.

* **Activate the virtual environment**:

    ```bash
    source dycov_venv/bin/activate
    ```

    **Note:** The tool includes a built-in sanity check to ensure that all necessary system 
              requirements are installed, and will notify you if any are missing.
    

* **First run**:
The first time the tool is run from a clean state, a configuration folder will be created
in $HOME/.config/dycov. This process may take several minutes and will only need to be repeated 
if the Dynawo version is updated.

[Dynawo Official Page](https://dynawo.github.io/)

[Dynawo Grid Compliance Verification Repository](https://github.com/dynawo/dyn-grid-compliance-verification/)
