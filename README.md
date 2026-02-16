# DyCoV &mdash; a Dynamic grid Compliance Verification tool

[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Documentation](https://readthedocs.org/projects/sphinx/badge/?version=master)](https://dycov.github.io/index.html)

A tool for automating the verification of dynamic grid compliance requirements
for solar, wind, and storage farms (Power Park Modules - PPM) as well as
synchronous machines (SM), including:

  * validation of RMS models (a.k.a. _"phasor models"_) for PPM
  * verification of electric performance requirements for both PPM and SM

The tool is pre-configured to use the tests required by the French connection
network code (i.e., those of RTE's
[DTR](https://www.services-rte.com/files/live//sites/services-rte/files/documentsLibrary/20240729_DTR_5867_fr)
Fiches "I"), but it can be easily configured and extended to run other tests.


(c) 2023&mdash;24 RTE  
Developed by Grupo AIA

--------------------------------------------------------------------------------

#### Table of Contents

1. [Overview](#overview)
2. [DyCoV Installation](#dycov-installation)
3. [Quick start](#quick-start)
4. [Running examples](#running-examples)
5. [Configuration](#configuration)
6. [Workshop presentation](#workshop-presentation)
7. [For developers](#for-developers)
8. [Roadmap](#roadmap)
9. [Contact](#contact)

--------------------------------------------------------------------------------

# Overview

The **Dynamic grid Compliance Verification** tool (DyCoV for short) is designed
to automate most tasks related to the validation of RMS models, in the context
of compliance requirements for new generation facilities. It contemplates
**model validation** properly speaking (i.e., _"does the model and its
parameterization match the actual behavior?"_), as well as **electric
performance** requirements testing (i.e., _"does the behavior, either measured
or simulated, pass the grid code requirements for connection?"_).

The tool is built with **Python**. Internally it is structured as a series of
independent tests, each producing its own report in PDF. These tests correspond
to the _Fiches I*_ in RTE's DTR document. To be specific, they contain the
following tests:

* **Electric Performance tests (Synchronous Machines)**: Fiches I2 (except
  stability margin calculations), I3, I4, I6, I7, I8, and I10.
* **Electric Performance tests (Power Park Modules)**: Fiches I2, I5, I6, I7, and I10.
* **RMS Model Validation tests (Power Park Modules)**: Fiche I16, structured into:
    - **Zone 1** (converter-level): Fault Ride-Through, Setpoint steps, Grid
      Frequency ramps, and Grid Voltage step.
    - **Zone 3** (plant-level): Voltage Regulation behavior (like I2), Fault
      Ride-Through (like I5), Voltage-dip Ride-Through (like I6), Voltage-swell
      Ride-Through (like I7), and Islanding (like I10).

Correspondingly, the results directory is structured along these lines.

Usually, the inputs are simply three files: the **DYD** and **PAR** files
corresponding to the [Dyna&omega;o](https://github.com/dynawo/dynawo) model on
the producer's side (i.e., everything "left" of the connection point, the PDR
bus), and an **INI** file containing the parameters and metadata that cannot be
provided in the DYD/PAR files. See the available examples in the `examples`
directory, at the top level of the git repository.  For more information about
these files, consult the [User Manual](docs/manual).

Additionally, in the case of _Model Validation_, the user must also provide the
**reference curves** for each test, against which the simulated curves will be
compared. They should be provided as a CSV file and a DICT file that describes
the format.  For more information about these files, consult the [User
Manual](docs/manual).

In the case of _Electric Performance_ testing, the user has also the option of
providing test curves, either to be used _instead of_ Dyna&omega;o simulations,
or to be used along Dyna&omega;o simulations (just for plotting both and
comparing them).

# DyCoV installation

> [!IMPORTANT]  
> **This section covers installing and running DyCoV as an end‑user** (prebuilt artifacts, installers and/or packaged distribution).
> If you intend to **develop or modify the source code**, please skip to
> **[For developers](#for-developers)** where we explain how to clone the GitHub repo and build the project for development
> (Linux natively and Windows via **WSL or Docker running Linux**).

## Linux installation

### System requirements

The requirements at the OS-level are rather minimal: one just needs a recent
Linux distribution. If you do not have any strong preference, we would
recommend Debian 12 or higher, as well as Ubuntu 22.04 LTS or higher.

To be more specific, we explicitly list here the packages to be installed,
assuming a Debian/Ubuntu system:

* Install the following packages (required by Dyna&omega;o):
  ```bash
  apt install curl unzip gcc g++ cmake
  ```

* Install these LaTeX packages:
  ```bash
   apt install texlive-base texlive-latex-base texlive-latex-recommended \
               texlive-latex-extra texlive-science texlive-lang-french latexmk
  ```

* Install a basic Python installation (version 3.9 or higher), containing at
  least `pip`, `venv` and `git`:
   ```bash
   apt install python3-minimal python3-pip python3-venv git
   ```

Note that the tool itself is a Python package. However, this package and all of
its dependencies (NumPy, etc.) will get installed at the user-level, i.e.,
inside the user's `$HOME` directory, under a _Python virtual environment_.


### Installation

1. Choose a base directory of your choice and run the following command:

   ```bash
   curl -L https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/v0.9.2/linux_install.sh | bash
   ```

   This script will install the DyCoV tool under your current directory in `$PWD/dycov`. 
   It will automatically:
   * Download and install a matching version of Dyna&omega;o (if confirmed by the user).
   * Clone the latest stable release.
   * Build & install the application (and all of its dependencies) using `uv` inside a virtual environment.

2. Next, you must activate the virtual environment using the **wrapper script** generated in the installation folder. This is important to ensure Dyna&omega;o is found in the system PATH:
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



## Windows installation

### Installation

> [!NOTE]  
> The Windows installation described here will install not only the DyCoV tool, but
> also all of the other requirements for you. Read the next section if you are
> interested in the details of what is installed in the Operating System
> (Dynawo, Python, LaTeX).

1. Download the **distribution artifacts** (typically from the Release page):

   - [dycov_dist.tar.gz](https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/v0.9.2/dycov_dist.tar.gz): The heavy application package; do not unzip this manually.
   - [import_image.sh](https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/v0.9.2/import_image.sh): Helper script for Linux Docker.
   - [run_dycov_docker.sh](https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/v0.9.2/run_dycov_docker.sh): Helper script for Linux Docker.

2. Install:

   - for WSL installation:
     Open PowerShell. We will "import" the file as a new Linux distribution named "DycovApp".
      ```powershell
      # Syntax: wsl --import <App_Name> <Install_Location> <Tar_File>
      # This creates a folder C:\DycovApp containing the system files.
      wsl --import DycovApp C:\DycovApp .\dycov_dist.tar.gz
      ```

   - for Docker installation:
     Open PowerShell in the folder containing `dycov_dist.tar.gz`. You need to import the image while manually restoring the configuration.
     *Tip: Be careful when copy-pasting. Ensure the backslashes before the quotes (`\"`) are preserved.*

      ```powershell
      # 1. Define variables with escaped quotes (Crucial for PowerShell)
      $DycovPath = 'ENV PATH=\"/opt/dynawo_install/dynawo:/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"'
      $DycovEntry = 'ENTRYPOINT [\"/start_dycov.sh\"]'

      # 2. Import the image applying the changes
      docker import --change $DycovPath --change $DycovEntry .\dycov_dist.tar.gz dycov:latest
      ```

3. Run:

   - for WSL installation:
     To start the tool, you simply launch this specific distribution:
      ```powershell
      wsl -d DycovApp
      ```
     *Note: In this mode, you are directly inside the Linux environment. You can access your Windows C: drive via `/mnt/c/` if needed.*

   - for Docker installation:
     Launch the container mapping your current directory (`${PWD}`) so the tool can see your files.
      ```powershell
      docker run --rm -it -v "${PWD}:/home/dycov_user" -w /home/dycov_user dycov:latest
      ```

4. The tool is used via a single command `dycov` having several subcommands. Quickly
   check that your installation is working by running the help option, which will show
   you all available subcommands:
   ```winbatch
   dycov -h
   ```

The DyCoV application is now ready to use.


### System requirements (for manual installs)

> [!NOTE]  
> The Windows installation (described in the previous section) will install all of
> these system requirements for you. This is only here for your information.

The requirements of the DyCoV tool at the OS-level are rather minimal: one just
needs a recent Windows distribution in which you should install **Dyna&omega;o**
(and its requirements), **LaTeX**, and **Python**. If you do not have any strong
preference, we would recommend Windows 10 or higher.

To be more specific, we explicitly list here the packages to be installed:

* Install Dyna&omega;o (v1.7.0 or later) and its required packages: Dyna&omega;o
  is a simulation platform required by this tool. Follow the steps outlined in
  the official Dyna&omega;o installation guide at [Dynawo Installation
  Guide](https://dynawo.github.io/install/).
   - **Nightly Version**: Download the **Nightly version** of Dynawo from the
     repository to ensure you have the latest features and updates.

* Install LaTeX.

* Install a basic Python installation (version 3.9 or higher), containing at
  least `pip` and the `venv` module.

Note that the DyCoV tool itself is a Python package. However, this package and
all of its dependencies (NumPy, etc.) will get installed under a *Python virtual
environment*.




# Quick start

The tool currently has different entry points, depending on what you want to use
it for:
* For **RMS model** validation: `dycov validate`
* For **electric performance** verification: `dycov performance`



## RMS model validations

In this mode the tool runs a set of _Model Validation tests_.  Some of these
tests resemble those of Fiches I, while some are different.  Of course, here one
is validating the model, not the electric performance; therefore, it is
mandatory to provide _reference curves_ as well as a model or producer curves.


Run the command with option `--help` (or `-h`) to get a quick overview of the
inputs you need to provide:
```bash
usage: dycov validate [-h] [-d] [-l LAUNCHER_DWO]
                     [-m PRODUCER_MODEL | -c PRODUCER_CURVES] [-p PCS]
                     [-o RESULTS_DIR] [-od]
                     [reference_curves]

positional arguments:
  reference_curves      enter the path to the folder containing the reference
                        curves for the Performance Checking Sheet (PCS)

options:
  -h, --help            show this help message and exit
  -d, --debug           more debug messages
  -l LAUNCHER_DWO, --launcher_dwo LAUNCHER_DWO
                        enter the path to the Dynawo launcher
  -m PRODUCER_MODEL, --producer_model PRODUCER_MODEL
                        enter the path to the folder containing the
                        producer_model files (DYD, PAR, INI)
  -c PRODUCER_CURVES, --producer_curves PRODUCER_CURVES
                        enter the path to the folder containing the curves for
                        the Performance Checking Sheet (PCS)
  -p PCS, --pcs PCS     enter one Performance Checking Sheet (PCS) to validate
  -o RESULTS_DIR, --results_dir RESULTS_DIR
                        enter the path to the results dir
  -od, --only_dtr       validate using only the PCS defined in the DTR
```



## Electric performance verifications

In this mode the tool runs an execution pipeline consisting in a set of
pre-defined tests, those of _Fiches_ "I" in RTE's DTR. You would use the command
`dycov performance` for _Synchronous Machines_ and for
_Power Park Modules_ (i.e. Wind and PV farms).

Run the command with option `--help` (or `-h`) to get a quick overview of the
inputs you need to provide:
```bash
usage: dycov performance [-h] [-d] [-l LAUNCHER_DWO] [-m PRODUCER_MODEL]
                    [-c PRODUCER_CURVES] [-p PCS] [-o RESULTS_DIR] [-od]

options:
  -h, --help            show this help message and exit
  -d, --debug           more debug messages
  -l LAUNCHER_DWO, --launcher_dwo LAUNCHER_DWO
                        enter the path to the Dynawo launcher
  -m PRODUCER_MODEL, --producer_model PRODUCER_MODEL
                        enter the path to the folder containing the
                        producer_model files (DYD, PAR, INI)
  -c PRODUCER_CURVES, --producer_curves PRODUCER_CURVES
                        enter the path to the folder containing the curves for
                        the Performance Checking Sheet (PCS)
  -p PCS, --pcs PCS     enter one Performance Checking Sheet (PCS) to validate
  -o RESULTS_DIR, --results_dir RESULTS_DIR
                        enter the path to the results dir
  -od, --only_dtr       validate using only the PCS defined in the DTR
```

Note that, in this mode, the tool can perform the electrical performance
verification using either a user-provided Dyna&omega;o **model** (running
Dyna&omega;o simulations), or a set of user-provided **curves**, or both (in
which case the curves are used only for showing them on the graphs, along the
simulated curves). Therefore you must provide either a `PRODUCER_MODEL` or a
`PRODUCER_CURVE` directory, or both.

The options and the required format of INI and curves files are documented in
the tool's [User Manual](docs/manual). For the format of DYD and PAR files (that
is, the Dyna&omega;o model of the producer's facilities), see the [Dyna&omega;o
documentation](https://dynawo.github.io/docs/).




# Running examples

In the `examples` folder (located at the first level inside the cloned
repository) one can find several valid input files that can be used as
examples.

## Model Validation Example:

```bash
dycov validate $PWD/dycov/examples/Model/Wind/IEC2015/ReferenceCurves -m $PWD/dycov/examples/Model/Wind/IEC2015/Dynawo
```

Upon execution, the screen output should be similar to the
following. Additionally, all results will be generated in a (newly created)
results directory. PDF reports for each kind of test will be found in the 'Reports'
subdirectory within the results' directory. If run with `--debug`, all Dyna&omega;o simulations are
also preserved inside this directory, so that they can be inspected and re-run
for deeper analysis, if desired.

```
2024-10-11 11:27:51,765 |           DyCoV.ModelValidation |       INFO |       model_validation.py:   92 | DyCoV Model Validation
2024-10-11 11:27:51,798 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3
...
2024-10-11 11:32:36,547 |           DyCoV.ModelValidation |       INFO |       model_validation.py:   40 | Opening the report: Results/Model/Reports/report.pdf
Opening in existing browser session.
```

## Electrical Performance Example:

```bash
dycov performance -m $PWD/dycov/examples/SM/Dynawo/SingleAux
```

Upon execution, the screen output should be similar to the
following. Additionally, all results will be generated in a (newly created)
results directory. PDF reports for each kind of test will be found in the 'Reports'
subdirectory within the results' directory. If run with `--debug`, all Dyna&omega;o simulations are
also preserved inside this directory, so that they can be inspected and re-run
for deeper analysis, if desired.

```
2024-10-11 11:34:29,199 |           DyCoV.ModelValidation |       INFO |       model_validation.py:   76 | Electric Performance Verification for Synchronous Machines
2024-10-11 11:34:29,232 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: AReactance
...
2024-10-11 11:35:08,797 |           DyCoV.ModelValidation |       INFO |       model_validation.py:   40 | Opening the report: Results/Performance/Reports/report.pdf
Opening in existing browser session.
```

# Grid-forming (GFM) envelope calculation

In addition to generic-model validation and electrical performance verification, DyCoV includes a specialized module for **Grid Forming (GFM)** analysis. This module calculates the theoretical dynamic response **envelopes** (i.e., max/min tolerances), based on the desired damping 
D and inertia H characteristics

This allows for the verification of whether the generator's behavior remains within operational and stability limits calculated analytically for various grid events.

## Supported GFM Events

The tool supports envelope calculation for the following dynamic events:

* **Amplitude Step:** Calculates the reactive current ($I_q$) and reactive power envelopes in response to a grid voltage step.
* **Phase Jump:** Analyzes the active power ($P$) response to a sudden change in the grid voltage phase angle.
* **RoCoF (Rate of Change of Frequency):** Calculates the active power response to a frequency ramp, modeling finite-duration events by superimposing step responses.
* **SCR Jump:** Evaluates stability and power response following a sudden change in the Short Circuit Ratio (grid impedance), differentiating between overdamped and underdamped responses.

## Hybrid Parameters & Configuration

The GFM module is highly configurable via the `Producer.ini` file. A key feature is the ability to handle **Hybrid** configurations, creating merged envelopes that cover the uncertainty between different operating modes (e.g., varying damping conditions).

### Standard vs. Hybrid Mode

The tool automatically detects the operating mode based on the parameters defined in the configuration:

1.  **Standard Mode:** Uses classic control parameters $D$ (Damping) and $H$ (Inertia). The tool calculates a single set of Upper and Lower envelopes.
2.  **Hybrid Mode:** If specific parameters are defined for both overdamped and underdamped behaviors, the tool generates a **Merged Envelope**.
    * Independent traces are calculated for the *Overdamped* set ($D_{over}, H_{over}$) and the *Underdamped* set ($D_{under}, H_{under}$).
    * The final envelope is constructed by taking the maximum of the upper limits and the minimum of the lower limits, ensuring a robust validation range that covers both dynamic spectrums.

### Key Configuration Parameters

Parameters are defined in the `[GFM Parameters]` section of the producer's INI file:

* **Physical:** `Snom`, `Unom`.
* **Control (Standard):** `D`, `H`, `Xeff` (Effective Reactance).
* **Control (Hybrid):** `D_Overdamped`, `H_Overdamped`, `D_Underdamped`, `H_Underdamped`.
* **Limits:** `p_max_injection`, `p_min_injection`, `q_max`, `q_min`.
* **Simulation Settings:**
    * `save_all_envelopes`: If set to `true`, the CSV output will include all intermediate envelopes (individual overdamped and underdamped traces) in addition to the final merged envelope.
    * `RatioMin`, `RatioMax`: Used for sensitivity analysis regarding parameter variations.

## GFM Outputs

For each GFM simulation case, the tool generates the following files in the results directory:

* **Plots (HTML & PNG):** Interactive and static graphs showing the PCC signal alongside the calculated Upper/Lower envelopes. In Hybrid mode, it can also visualize the individual Over/Under traces.
* **CSV Data:** Files containing the time series of the analyzed magnitude ($P$, $Q$, $I_q$) and their calculated limits.
* **INI Dump:** A `_ini_dump.txt` file that preserves the exact configuration and calculated internal values (such as the damping ratio $\epsilon$) used during the execution.

# Configuration

The tool is configured via a `config.ini` file, written in the well-known INI
format (of the [Python
flavor](https://docs.python.org/3/library/configparser.html)). The location of
this file follows the customary standard of each platform for application data:

* Under Linux: `$HOME/.config/dycov/`
* Under Windows: `%APPDATA%\Local\dycov`

The supplied INI file contains just the options that most users of the tool
would want to change, but there exist many more internal configuration options
that may be overriden in this INI file.  For more information about
configuration, including more advanced tasks such as adding a whole new test,
consult the [User Manual](docs/manual).


# Workshop presentation
Here you can watch the video of the presentation workshop held on 11/03/2025. (english subtitles available only if you download the video)
Part 1: 

https://github.com/user-attachments/assets/d8c0bcd8-339f-47e4-9f26-e452b2e87980

Part 2:

https://github.com/user-attachments/assets/ff219478-f3d2-4790-bc45-39a11e227b5b



# For developers

> [!NOTE]  
> **This section is for contributors and developers** who want to clone the GitHub repository and build DyCoV from source.
> If you only want to *use* DyCoV, see **[DyCoV Installation](#dycov-installation)** (end‑user installation on Linux/Windows).

## Build and install on Linux (using uv)

1.  Clone the repository:
    ```bash
    git clone https://github.com/dynawo/dyn-grid-compliance-verification dycov_repo
    cd dycov_repo
    ```

2.  Ensure you have `uv` installed. If not, you can install it via pipx or pip:
    ```bash
    pip install uv
    ```

3.  Use the provided helper script to create the environment and install dependencies:
    ```bash
    ./build_and_install.sh --devel
    ```
    
    *Alternatively, you can run the steps manually:*
    ```bash
    uv venv dycov_venv
    source dycov_venv/bin/activate
    uv pip install -e .[dev,test]
    ```

4.  Quickly check that your installation is working by running the help option:
    ```bash
    dycov -h
    ```
   
The DyCoV application is now ready for development.

## Build and install on Windows (using uv)

> [!IMPORTANT]  
> **The recommended way to use and develop DyCoV on Windows is through either  
> (1) Windows Subsystem for Linux (WSL) or  
> (2) Docker.**  
> Both methods provide a fully Linux‑compatible environment, which is required for Dynawo and LaTeX.

### Recommended approaches (WSL or Docker)

#### Option A — Development using **WSL** (recommended)

1. Enable WSL and install Ubuntu 22.04 or later.
2. Open a WSL terminal and follow the Linux instructions exactly:

   ```bash
   git clone https://github.com/dynawo/dyn-grid-compliance-verification dycov_repo
   cd dycov_repo

   pip install uv  # if not already installed
   ./build_and_install.sh --devel
   ```

3. Activate the environment and run:

   ```bash
   source dycov_venv/bin/activate
   dycov -h
   ```
#### Option B — Development using **Docker**

1. Start a basic Linux container (e.g., Ubuntu), mounting your project folder:

   ```bash
   docker run --rm -it -v "${PWD}:/workspace" -w /workspace ubuntu:22.04
   ```

2. Inside the container, install required system tools:

   ```bash
   apt update
   apt install -y python3 python3-pip python3-venv git curl unzip gcc g++ cmake
   pip install uv
   ```

3. Build and install DyCoV exactly as in Linux:

   ```bash
   ./build_and_install.sh --devel
   ```

4. Run the tool:

   ```bash
   source dycov_venv/bin/activate
   dycov -h
   ```

#### Native Windows installation (not recommended)

> [!WARNING]  
> Native Windows execution is not recommended because Dynawo, LaTeX tools, and several
> system‑level dependencies are Linux‑oriented.
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

Finally, if you want to further _develop_ the source code of this tool, consult
the [Developer Manual](docs/manual_dev).

## DyCoV flowchart

Below is the DyCoV flowchart. This diagram is not intended to show all the details of the tool, but rather to facilitate understanding of its main flow.

![DyCoV Flowchart](./docs/manual_dev/source/figs_structure/flowchart.svg?sanitize=true)

# Roadmap

Below are the major development axis identified for DyCoV in the next few months with associated contents. It is important to notice that the development content may be subject to change due to unforeseen complexity in implementing features or priority changes.

## Axis 1 - Models support

* Complete support of WECC PV and BESS models
* Support of IEC 63426 standard model ("Generic RMS simulations models of converter-based generating units")

## Axis 2 - Ease of use

* Analysis and report improvements
* Tutorials
* Addition of a Graphical User Interface
* Windows portability

## Axis 3 - Tool performance, quality and robustness

* Consolidation of the signal processing part
* Robustness improvements
* Inclusion of on-site verification for RMS model validation

# Contact

For any questions or feedback, please reach out to the appropriate contact below:
* For inquiries related to electrical modeling, please contact RTE at: rte-r-d-raccordement@rte-france.com
* For any software-related issues or questions, please contact AIA at: dycov@aia.es