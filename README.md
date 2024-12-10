# dgcv &mdash; a Dynamic Grid Compliance Verification tool

[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Documentation](https://readthedocs.org/projects/sphinx/badge/?version=master)](https://dgcv.github.io/index.html)

A tool for automating the verification of dynamic grid compliance requirements for
solar, wind, and storage farms (Power Park Modules - PPM) as well as synchronous machines (SM), including:

  * validation of RMS models (a.k.a. _"phasor models"_) for PPM
  * verification of electric performance requirements for both PPM and SM

The tool is pre-configured to use the tests required by the French connection network code (i.e.,
those of RTE's [DTR](https://www.services-rte.com/files/live//sites/services-rte/files/documentsLibrary/20240729_DTR_5867_fr) Fiches "I"), but it can be easily configured and extended to run
other tests.


(c) 2023&mdash;24 RTE  
Developed by Grupo AIA

--------------------------------------------------------------------------------

#### Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick start](#quick-start)
4. [Running examples](#running-examples)
5. [Configuration](#configuration)
6. [Compiling Modelica models](#compiling-modelica-models)
7. [For developers](#for-developers)
8. [Roadmap](#roadmap)
9. [Contact](#contact)

--------------------------------------------------------------------------------

# Overview

The **Dynamic Grid Compliance Verification** tool (DGCV for short) is designed to automate
most tasks related to the validation of RMS models, in the context of compliance
requirements for new generation facilities. It contemplates **model validation**
properly speaking (i.e., _"does the model and its parameterization match the
actual behavior?"_), as well as **electric performance** requirements testing
(i.e., _"does the behavior, either measured or simulated, pass the grid code
requirements for connection?"_).

The tool is built with **Python**. Internally it is structured as a series of independent
tests, each producing its own report in PDF. These tests correspond to the
_Fiches I*_ in RTE's DTR document. To be specific, they contain the following
tests:

* **Electric Performance tests (Synchronous Machines)**: Fiches I2 (except
  stability margin calculations), I3, I4, I6, I7, I8, and I10.
* **Electric Performance tests (Power Park Modules)**: Fiches I2, I5, I6, I7, and I10.
* **RMS Model Validation tests (Power Park Modules)**: Fiche I16, structured into:
    - **Zone 1** (converter-level): Fault Ride-Through, Setpoint steps, Grid Frequency ramps, and Grid
      Voltage step.
    - **Zone 3** (plant-level): Voltage Regulation behavior (like I2), Fault
      Ride-Through (like I5), Voltage-dip Ride-Through (like I6), Voltage-swell
      Ride-Through (like I7), and Islanding (like I10).

Correspondingly, the results directory is structured along these lines.

Usually, the inputs are simply three files: the **DYD** and **PAR** files
corresponding to the [Dyna&omega;o](https://github.com/dynawo/dynawo) model on the producer's side (i.e., everything
"left" of the connection point, the PDR bus), and an **INI** file containing the
parameters and metadata that cannot be provided in the DYD/PAR
files. See the available examples in the `examples` directory, at the top level
of the git repository.  For more information about these files, consult the
[User Manual](docs/manual).

Additionally, in the case of _Model Validation_, the user must also provide the
**reference curves** for each test, against which the simulated curves will be
compared. They should be provided as a CSV file and a DICT file that describes
the format.  For more information about these files, consult the [User
Manual](docs/manual).

In the case of _Electric Performance_ testing, the user has also the option of
providing test curves, either to be used _instead of_ Dyna&omega;o simulations, or to
be used along Dyna&omega;o simulations (just for plotting both and comparing them).




# Linux installation

## System requirements

The requirements at the OS-level are rather minimal: one just needs a recent
Linux distribution in which you should install
Dyna&omega;o's requirements,
**LaTeX**, and **Python**. If you do not have any strong preference, we would
recommend Debian 12 or higher, as well as Ubuntu 22.04 LTS or higher.

To be more specific, we explicitly list here the packages to be installed,
assuming a Debian/Ubuntu system:

* Install the following required packages:
  ```bash
  apt install curl unzip gcc g++ cmake
  ```

* Install `make` and these LaTeX packages:
  ```bash
   apt install make texlive-base texlive-latex-base texlive-latex-extra \
               texlive-latex-recommended texlive-science texlive-lang-french latexmk
  ```

* Install a basic Python installation (version 3.9 or higher), containing at
  least `pip` and the `venv` module:
   ```bash
   apt install python3-minimal python3-pip python3-venv
   ```

Note that the tool itself is also a Python package. However, this package and
all of its dependencies (NumPy, etc.) will get installed at the user-level, i.e.,
inside the user's `$HOME` directory, under a _Python virtual environment_.


## Installation

1. Choose a base directory of your choice and run the following command:

   ```bash
   curl -L https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/v0.5.2/linux_install.sh | bash
   ```

   This script will install the DGCV tool, together with a matching version of
   Dyna&omega;o, under your current directory in `$PWD/dgcv`.  It will do so by
   cloning the latest stable release and building & installing the application
   (and all of its dependencies, such as NumPy, etc.) under a Python virtual
   environment.

2. Next, you must activate the virtual environment that has just been created: 
   ```bash
   source $PWD/dgcv/activate_dgcv
   ```

3. The tool is used via a single command `dgcv` having several subcommands. Quickly
   check that your installation is working by running the help option, which will show
   you all available subcommands:
   ```bash
   dgcv -h
   ```

4. Upon the first use, the tool will automatically compile the Modelica models
   internally defined by the tool. You can also run this command explicitly, as follows:
   ```bash
   dgcv compile
   ```
   (Note: this command is also used to compile any new Modelica models custom-defined by the
   user; see the section below on [Compiling Modelica models](#compiling-modelica-models).)
   
The dgcv application is now ready to use.

# Windows installation

## System requirements

An easy-to-use installer is being created to simplify and unify the installation of the package on Windows. In the meantime, the package requirements for Windows can be found in the [installation tutorial for developers](https://github.com/dynawo/dyn-grid-compliance-verification/blob/windows_version/docs/manual_dev/source/development/installation.rst).

## Installation

An easy-to-use installer is being created to simplify and unify the installation of the package on Windows. In the meantime, the package installation steps for Windows can be found in the [installation tutorial for developers](https://github.com/dynawo/dyn-grid-compliance-verification/blob/windows_version/docs/manual_dev/source/development/installation.rst).

# Quick start

The tool currently has different entry points, depending on what you want to use
it for:
* For **RMS model** validation: `dgcv validate`
* For **electric performance** verification: `dgcv performance`



## RMS model validations

In this mode the tool runs a set of _Model Validation tests_.  Some of these
tests resemble those of Fiches I, while some are different.  Of course, here one
is validating the model, not the electric performance; therefore, it is
mandatory to provide _reference curves_ as well as a model or producer curves.


Run the command with option `--help` (or `-h`) to get a quick overview of the
inputs you need to provide:
```
usage: dgcv validate [-h] [-d] [-l LAUNCHER_DWO]
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
`dgcv performance` for _Synchronous Machines_ and for
_Power Park Modules_ (i.e. Wind and PV farms).

Run the command with option `--help` (or `-h`) to get a quick overview of the
inputs you need to provide:
```
usage: dgcv performance [-h] [-d] [-l LAUNCHER_DWO] [-m PRODUCER_MODEL]
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
verification using either a user-provided dyna&omega;o **model** (running Dyna&omega;o
simulations), or a set of user-provided **curves**, or both (in which case the
curves are used only for showing them on the graphs, along the simulated
curves). Therefore you must provide either a `PRODUCER_MODEL` or a
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

```
dgcv validate $PWD/dgcv/examples/Model/Wind/IEC2015/ReferenceCurves -m $PWD/dgcv/examples/Model/Wind/IEC2015/Dynawo
```

Upon execution, the screen output should be similar to the
following. Additionally, all results will be generated in a (newly created)
results directory. PDF reports for each kind of test will be found in the 'Reports'
subdirectory within the results' directory. If run with `--debug`, all Dyna&omega;o simulations are
also preserved inside this directory, so that they can be inspected and re-run
for deeper analysis, if desired.

```
2024-10-11 11:27:51,765 |           DGCV.ModelValidation |       INFO |       model_validation.py:   92 | DGCV Model Validation
2024-10-11 11:27:51,798 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3
2024-10-11 11:27:56,324 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR10
2024-10-11 11:27:59,540 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3Qmin
2024-10-11 11:28:02,960 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientHiZTc800
2024-10-11 11:28:17,388 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientHiZTc500
2024-10-11 11:28:33,459 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentBolted
2024-10-11 11:28:37,575 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentHiZ
2024-10-11 11:28:50,476 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Active
2024-10-11 11:28:54,294 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Reactive
2024-10-11 11:28:57,550 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Voltage
2024-10-11 11:28:57,601 |                    DGCV.Dynawo |    WARNING |       model_parameters.py:  351 | IECWT4BCurrentSource2015 control mode will be changed
2024-10-11 11:29:01,219 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridFreqRamp, OPER. COND.: W500mHz250ms
2024-10-11 11:29:04,795 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Rise
2024-10-11 11:29:08,083 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Drop
2024-10-11 11:29:11,629 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.USetPointStep, OPER. COND.: AReactance
2024-10-11 11:29:11,694 |                    DGCV.Dynawo |    WARNING |       model_parameters.py:  351 | IECWPP4BCurrentSource2015 control mode will be changed
2024-10-11 11:29:15,820 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.USetPointStep, OPER. COND.: BReactance
2024-10-11 11:29:15,871 |                    DGCV.Dynawo |    WARNING |       model_parameters.py:  351 | IECWPP4BCurrentSource2015 control mode will be changed
2024-10-11 11:29:19,563 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.PSetPointStep, OPER. COND.: Dec40
2024-10-11 11:29:23,539 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.PSetPointStep, OPER. COND.: Inc40
2024-10-11 11:29:27,268 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.QSetPointStep, OPER. COND.: Inc10
2024-10-11 11:29:30,366 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.QSetPointStep, OPER. COND.: Dec20
2024-10-11 11:29:33,440 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.ThreePhaseFault, OPER. COND.: TransientBolted
2024-10-11 11:29:40,400 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.GridVoltageDip, OPER. COND.: Qzero
2024-10-11 11:29:46,410 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.GridVoltageSwell, OPER. COND.: QMax
2024-10-11 11:29:51,451 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.GridVoltageSwell, OPER. COND.: QMin
2024-10-11 11:29:56,347 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.Islanding, OPER. COND.: DeltaP10DeltaQ4
2024-10-11 11:29:58,116 |                    DGCV.Dynawo |    WARNING |              simulator.py:  892 | Simulation Fails, logs in Results/Model/PCS_RTE-I16z3/Islanding/DeltaP10DeltaQ4/outputs/logs/dynawo.log
2024-10-11 11:30:47,926 |                  DGCV.PDFLatex |    WARNING |                 figure.py:  507 | All curves appear to be flat in PCS_RTE-I16z1.GridFreqRamp.W500mHz250ms; something must be wrong with the simulation
2024-10-11 11:31:46,592 |                    DGCV.Report |       INFO |                 report.py:  273 | 
Summary Report
==============

***Run on 2024-10-11 11:31 CEST***
***Dynawo version: 1.7.0 (rev:master-4ee311a)***
***Model: examples/Model/Wind/IEC2015/Dynawo***
***Reference: examples/Model/Wind/IEC2015/ReferenceCurves***


Pcs          Benchmark                Operating Condition      Overall Result
-----------------------------------------------------------------------------
PCS_RTE-I16z1ThreePhaseFault          TransientBoltedSCR3      Compliant
PCS_RTE-I16z1ThreePhaseFault          TransientBoltedSCR10     Compliant
PCS_RTE-I16z1ThreePhaseFault          TransientBoltedSCR3Qmin  Compliant
PCS_RTE-I16z1ThreePhaseFault          TransientHiZTc800        Compliant
PCS_RTE-I16z1ThreePhaseFault          TransientHiZTc500        Compliant
PCS_RTE-I16z1ThreePhaseFault          PermanentBolted          Compliant
PCS_RTE-I16z1ThreePhaseFault          PermanentHiZ             Compliant
PCS_RTE-I16z1SetPointStep             Active                   Non-compliant
PCS_RTE-I16z1SetPointStep             Reactive                 Compliant
PCS_RTE-I16z1SetPointStep             Voltage                  Non-compliant
PCS_RTE-I16z1GridFreqRamp             W500mHz250ms             Non-compliant
PCS_RTE-I16z1GridVoltageStep          Rise                     Non-compliant
PCS_RTE-I16z1GridVoltageStep          Drop                     Non-compliant
PCS_RTE-I16z3USetPointStep            AReactance               Non-compliant
PCS_RTE-I16z3USetPointStep            BReactance               Non-compliant
PCS_RTE-I16z3PSetPointStep            Dec40                    Compliant
PCS_RTE-I16z3PSetPointStep            Inc40                    Compliant
PCS_RTE-I16z3QSetPointStep            Inc10                    Compliant
PCS_RTE-I16z3QSetPointStep            Dec20                    Non-compliant
PCS_RTE-I16z3ThreePhaseFault          TransientBolted          Compliant
PCS_RTE-I16z3GridVoltageDip           Qzero                    Compliant
PCS_RTE-I16z3GridVoltageSwell         QMax                     Compliant
PCS_RTE-I16z3GridVoltageSwell         QMin                     Compliant
PCS_RTE-I16z3Islanding                DeltaP10DeltaQ4          Failed simulation


2024-10-11 11:32:17,921 |                  DGCV.PDFLatex |       INFO |                 report.py:  414 | PDF done: /tmp/DGCV_Results_debian/0b738550-9d10-4ead-bfc5-e03cc2bcaee5/Reports/report.tex
2024-10-11 11:32:36,547 |           DGCV.ModelValidation |       INFO |       model_validation.py:   40 | Opening the report: Results/Model/Reports/report.pdf
Opening in existing browser session.
```

## Electrical Performance Example:

```
dgcv performance -m $PWD/dgcv/examples/SM/Dynawo/SingleAux
```

Upon execution, the screen output should be similar to the
following. Additionally, all results will be generated in a (newly created)
results directory. PDF reports for each kind of test will be found in the 'Reports'
subdirectory within the results' directory. If run with `--debug`, all Dyna&omega;o simulations are
also preserved inside this directory, so that they can be inspected and re-run
for deeper analysis, if desired.

```
2024-10-11 11:34:29,199 |           DGCV.ModelValidation |       INFO |       model_validation.py:   76 | Electric Performance Verification for Synchronous Machines
2024-10-11 11:34:29,232 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: AReactance
2024-10-11 11:34:29,766 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: BReactance
2024-10-11 11:34:30,215 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I3.LineTrip, OPER. COND.: 2BReactance
2024-10-11 11:34:30,828 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I4.ThreePhaseFault, OPER. COND.: TransientBolted
2024-10-11 11:34:41,351 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I6.GridVoltageDip, OPER. COND.: Qzero
2024-10-11 11:34:42,511 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I7.GridVoltageSwell, OPER. COND.: QMax
2024-10-11 11:34:43,523 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I7.GridVoltageSwell, OPER. COND.: QMin
2024-10-11 11:34:44,482 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I8.LoadShedDisturbance, OPER. COND.: PmaxQzero
2024-10-11 11:34:44,925 |       DGCV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I10.Islanding, OPER. COND.: DeltaP10DeltaQ4
2024-10-11 11:34:57,351 |                    DGCV.Report |       INFO |                 report.py:  273 | 
Summary Report
==============

***Run on 2024-10-11 11:34 CEST***
***Dynawo version: 1.7.0 (rev:master-4ee311a)***
***Model: examples/SM/Dynawo/SingleAux***


Pcs          Benchmark                Operating Condition      Overall Result
-----------------------------------------------------------------------------
PCS_RTE-I2   USetPointStep            AReactance               Non-compliant
PCS_RTE-I2   USetPointStep            BReactance               Non-compliant
PCS_RTE-I3   LineTrip                 2BReactance              Compliant
PCS_RTE-I4   ThreePhaseFault          TransientBolted          Compliant
PCS_RTE-I6   GridVoltageDip           Qzero                    Compliant
PCS_RTE-I7   GridVoltageSwell         QMax                     Compliant
PCS_RTE-I7   GridVoltageSwell         QMin                     Compliant
PCS_RTE-I8   LoadShedDisturbance      PmaxQzero                Compliant
PCS_RTE-I10  Islanding                DeltaP10DeltaQ4          Compliant


2024-10-11 11:35:08,635 |                  DGCV.PDFLatex |       INFO |                 report.py:  414 | PDF done: /tmp/DGCV_Results_debian/e66c17ee-caff-4ef1-ae1f-eba5592092bb/Reports/report.tex
2024-10-11 11:35:08,797 |           DGCV.ModelValidation |       INFO |       model_validation.py:   40 | Opening the report: Results/Performance/Reports/report.pdf
Opening in existing browser session.
```



# Configuration

The tool is configured via a `config.ini` file, written in the well-known INI
format (of the [Python
flavor](https://docs.python.org/3/library/configparser.html)). The location of
this file follows the customary standard of each platform for application data:

* Under Linux: `$HOME/.config/dgcv/`
* Under Windows: `%APPDATA%\Local\dgcv`

Besides the `config.ini` file, there is a subfolder named `ddb`, which will
contain all compiled preassembled Modelica models (see next section).

The supplied INI file contains just the options that most users of the tool
would want to change, but there exist many more internal configuration options
that may be overriden in this INI file.  For more information about
configuration, including more advanced tasks such as adding a whole new test,
consult the [User Manual](docs/manual).



# Compiling Modelica models

The tool uses some _preassembled_ Modelica models defined internally, and the
user may also define additional ones of his own. They should be compiled by
using the supplied script, `dgcv compile`.

As mentioned above, all compiled models (both the tool's and the user's) will be
saved under the tool's config directory, in the `ddb` subfolder. All of the
compilation output (standard output and standard error messages) will also be
logged there, in a file named `compile.log`.

For models provided by the user, the definition files `*.xml, *.mo, *.extvar`
may be located anywhere, but upon compilation they will be _copied_ to a
subfolder `user_models`, sibling to the `ddb` subfolder.

In case of upgrading the version of Dyna&omega;o, you may want to recompile all
models. You can easily do this by running the command with only the `--force`
option.

Run the command with option --help (or -h) to get a quick overview of the inputs
you need to provide:
```
usage: dgcv compile [-h] [-d] [-l LAUNCHER_DWO] [-m DYNAWO_MODEL] [-f]

options:
  -h, --help            show this help message and exit
  -d, --debug           more debug messages
  -l LAUNCHER_DWO, --launcher_dwo LAUNCHER_DWO
                        enter the path to the Dynawo launcher
  -m DYNAWO_MODEL, --dynawo_model DYNAWO_MODEL
                        XML file describing a custom Modelica model
  -f, --force           force the recompilation of all Modelica models (the
                        user's and the tool's own)
```



# For developers

## Build and install

1. Clone the repository via: 
   ```bash
   git clone https://github.com/dynawo/dyn-grid-compliance-verification dgcv_repo
   ```
   (you may of course use any name for the top-level directory, here `"dgcv_repo"`.)
   
2. Get into the repository and run the shell script named `build_and_install.sh`.
   This builds the Python package, creates a Python virtual environment under
   the subdirectory `dgcv_venv`, and installs the package into it (together with
   all the necessary library dependencies, such as NumPy, etc.).

3. Next, you must activate the virtual environment that has just been created: 
   ```bash
   source dgcv_venv/bin/activate
   ```

4. The tool is used via a single command `dgcv` having several subcommands. Quickly
   check that your installation is working by running the help option, which will show
   you all available subcommands:
   ```bash
   dgcv -h
   ```

5. Upon the first use, the tool will automatically compile the Modelica models
   internally defined by the tool. You can also run this command explicitly, as follows:
   ```bash
   dgcv compile
   ```
   (Note: this command is also used to compile any new Modelica models custom-defined by the
   user; see the section below on [Compiling Modelica models](#compiling-modelica-models).)
   
The dgcv application is now ready to use.


Finally, if you want to further _develop_ the source code of this tool, consult
the [Developer Manual](docs/manual_dev).

# Roadmap

Below are the major development axis identified for dgcv in the next few months with associated contents. It is important to notice that the development content may be subject to change due to unforeseen complexity in implementing features or priority changes.

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

In case of any question or feedback, please feel free to contact us at the following e-mail adress: rte-r-d-raccordement@rte-france.com

