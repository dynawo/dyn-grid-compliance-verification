# DyCoV — Dynamic grid Compliance Verification

[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Documentation](https://readthedocs.org/projects/sphinx/badge/?version=master)](https://dycov.github.io/index.html)

DyCoV is an engineering-oriented framework designed to support grid connection
studies through automated dynamic simulations and compliance checks.  
It automates the verification of dynamic grid compliance requirements for solar 
and wind farms (Power Park Modules — PPM), battery energy storage systems (BESS), 
and synchronous machines (SM), covering workflows from model validation to 
grid-code compliance assessment. As an end-to-end framework, DyCoV supports 
both model validation and compliance assessment workflows used during grid 
connection studies.  

DyCoV is not a simulation tool itself — it leverages Dynawo to perform simulations
and focuses on automated validation and compliance assessment workflows.


---

## How DyCoV works

DyCoV follows a structured validation pipeline where dynamic behaviour is
evaluated against defined compliance criteria:

```
Inputs (Model / Curves)
          ↓
   Simulation (Dynawo)
          ↓
   Signal Processing
          ↓
   Validation (PCS)
          ↓
       Reports
```

Depending on the workflow, DyCoV either:
- compares simulated results against reference curves (**model validation**), or
- evaluates system behaviour under predefined disturbances (**performance verification**)

This pipeline is fully automated and produces structured reports and plots.

---

## About DyCoV

This section provides a high-level overview of the core studies supported by DyCoV
and how they contribute to grid connection validation workflows.

DyCoV automates two independent and mandatory studies required
for grid connection validation:

- **RMS model validation** — verifies that a dynamic model reproduces a reference
  behaviour within defined tolerances (PCS‑I16, Zones 1 and 3)

- **Electrical performance verification** — evaluates the installation response
  under grid disturbances and checks compliance with grid‑code requirements
  (PCS‑I2, I3, I4, I5, I6, I7, I8, I10)

Both studies must be successfully completed to formally validate an installation 
for grid connection.
These studies are independent but complementary, and together form the basis for 
validating a generation unit prior to grid connection.

Additionally:

- **Grid‑Forming (GFM) envelope calculation** — computes analytical bounds
  for GFM unit responses (optional workflow)

The following terms are used throughout the documentation:

### Key concepts

- **PCS**: Performance Checking Sheet — set of validation tests defined in the RTE grid code (DTR)
- **PPM**: Power Park Module — wind, solar or aggregated generation installation
- **RMS model validation** — model validation workflow (PCS I16)
- **Electrical performance verification** — compliance assessment workflow (PCS I2–I10)
- **GFM**: Grid‑Forming — control mode for inverter-based resources (optional workflow)

### Acronyms

- **EMT**: Electromagnetic Transients
- **OC**: Operating Condition
- **OP**: Operating Point
- **PDR**: Point of Delivery (Point de raccordement)
- **SCR**: Short Circuit Ratio
- **CCT**: Critical Clearing Time
- **TSO**: Transmission System Operator

---

## Getting started

This section serves both as an entry point and as a guide to the documentation structure:

- **Quick start** → minimal working examples
- **Tutorials** → step-by-step workflows (recommended entry point)
- **Installation** → environment setup
- **Reference manuals** → detailed technical documentation
- **Developer docs** → extension and internal architecture

Depending on your objective:

- To run DyCoV quickly and see results → go to **[Quick start](#quick-start)**
- To validate a real installation → run both validation and performance workflows in sequence
- To build your own study → see [input preparation tutorials](docs/tutorials/preparing_inputs.md)

Example cases are available in the `examples/` directory and can be copied
and adapted to your own projects.

For a hands-on introduction, proceed to the [Quick start](#quick-start) section.  
For detailed workflow explanations, refer to the [Documentation](#documentation) section.

---

## Inputs and outputs

This section describes the data exchanged with DyCoV and how it is used across different workflows.
DyCoV works with time-domain dynamic responses obtained from simulations or field measurements.

Typical inputs:

- **Dynawo models** — RMS simulation models of the installation
- **Reference curves** — expected behaviour (used for validation)
- **Producer curves** — simulated responses (used when simulations are provided externally instead of being run through Dynawo)  
  These are typically used when simulations are generated outside DyCoV and need to be assessed without rerunning Dynawo.

Typical outputs:

- PDF compliance reports
- Interactive HTML plots
- A structured `Results/` directory (organized per study and scenario)

For full details, see: [Preparing inputs](docs/tutorials/preparing_inputs.md)

---

## Installation

This section describes the supported installation options and points to detailed setup guides. 
Choose the one that best fits your environment and usage (native, WSL, or development setup).
Once installed, DyCoV is accessed through the `dycov` command-line interface.

> **For developers** building from source, see: [Setup](docs/developer/setup.md)

### Linux

The following steps install DyCoV in a native Linux environment.

For detailed procedures and advanced setups, see: [Linux native](docs/installation/linux_native.md)

DyCoV requires a Linux environment with system dependencies
(e.g. Python ≥ 3.13, build tools, LaTeX).

#### Install DyCoV

```bash
# Download and install DyCoV
curl -L https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest/download/linux_install.sh | bash
```

#### Activate and check the environment

After installation, activate the environment and verify that the CLI is available:
```bash
# Activate environment
source dycov/activate_dycov

# Check CLI
dycov --version
```

---

### Windows (WSL)

The following steps install DyCoV in a Windows Subsystem for Linux environment.

DyCoV runs inside a preconfigured WSL (Windows Subsystem for Linux) environment.
The following steps assume this environment is used as provided.

For detailed procedures and advanced setups, see: [Using the provided image](docs/installation/using_the_provided_image.md)

**Prerequisite:** WSL must be enabled:  
https://learn.microsoft.com/en-us/windows/wsl/install

Download the following files:

- [dycov_rawimage.tar.gz](https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest/download/dycov_rawimage.tar.gz)
- [import_wsl.bat](https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest/download/import_wsl.bat)
- [import_wsl.ps1](https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest/download/import_wsl.ps1)
- [run_dycov_wsl.ps1](https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest/download/run_dycov_wsl.ps1)

Run:

```bash
import_wsl.bat
```

This will import and configure the DyCoV environment automatically.

---

## Quick start

This section provides minimal working examples to quickly execute each main workflow 
using bundled cases, allowing you to quickly verify the installation and explore the 
generated outputs.

> **Note:** On native installations, ensure the DyCoV environment is activated
> (e.g. `source dycov/activate_dycov`). In WSL and Docker environments,
> it may already be active.

For a more detailed walkthrough of these steps and expected outputs, see: [Quick start](docs/tutorials/quick_start.md)

### RMS model validation

This workflow focuses on validating that a dynamic model reproduces expected reference behaviour.

For a detailed description of this workflow and its expected outputs, see: [RMS validation](docs/tutorials/rms_model_validation.md)

Run:

```bash
dycov validate examples/Model/Wind/WECC4B/ReferenceCurves/ -m examples/Model/Wind/WECC4B/Dynawo/
```

This will:
- run RMS simulations
- compare results against reference curves
- generate validation reports

**Expected result:**
- A `Results/Model/` directory is created
- A PDF report summarizing compliance is generated
- HTML plots show simulated vs reference curves
- Some tests may be marked as:
  - Compliant
  - Non-compliant (depending on the example and model behaviour)

---

### Electrical performance verification

Here, the system response is evaluated under predefined grid disturbance scenarios.

For detailed explanations and result interpretation, see: [Performance verification](docs/tutorials/electrical_performance_verification.md)

Run:

```bash
dycov performance -m examples/Performance/Single/WECC4B/Dynawo/
```

This will:
- execute PCS test scenarios
- evaluate compliance with grid‑code requirements

**Expected result:**
- PCS test cases are executed
- Compliance is evaluated for each test scenario
- Tests are marked as:
  - Compliant
  - Non-compliant
- A summary report highlights pass/fail status per PCS, benchmark and operating condition

---

### Grid‑Forming analysis (optional)

This optional workflow targets GFM units and computes admissible response envelopes.

For a complete description of this analysis workflow, see: [Grid‑Forming (GFM) analysis](docs/tutorials/grid_forming_analysis.md)

Run:

```bash
dycov generateEnvelopes -i examples/GFM/Overdamped/Producer.ini
```

This will:
- compute admissible envelopes
- generate CSV data and plots

**Expected result:**
- CSV files with envelope data
- Static PNG plots
- Interactive HTML plots for detailed inspection

---

## Documentation

The documentation is structured to progressively guide users from high-level concepts to detailed workflow configuration.

- Installation guides:
  - [Installation overview](docs/installation/README.md)

- Tutorials (guided learning path):
  - [Reading guide](docs/tutorials/README.md)
  - [Conceptual overview](docs/tutorials/first_steps.md)
  - [Preparing inputs](docs/tutorials/preparing_inputs.md)
  - [Understanding reports](docs/tutorials/understanding_reports.md)
  - Workflow-specific tutorials:
    - [RMS validation](docs/tutorials/rms_model_validation.md)
    - [Performance verification](docs/tutorials/electrical_performance_verification.md)
    - [Grid‑Forming (GFM) analysis](docs/tutorials/grid_forming_analysis.md)

These documents are intended to be used once you are familiar with the basic execution flow provided in the [Quick start](#quick-start) section.

Developer documentation is available separately and provides guidance on building, extending, and contributing to DyCoV:

- Key developer resources:
  - [Overview](docs/developer/README.md)
  - [Setup](docs/developer/setup.md)
  - [Project structure](docs/developer/project_structure.md)
  - [Extending DyCoV](docs/developer/extending_dycov.md)
  - [Add new PCS](docs/developer/add_new_pcs.md)

---

## Reference manuals

In addition to the online documentation, DyCoV provides local reference manuals installed 
with the software.

| Installation | Location |
|--------------|----------|
| Linux native | `~/dycov/manual/` |
| Docker / WSL | `~/manual/` |

---

## Workshop

This section provides recorded sessions illustrating real usage of DyCoV workflows in 
practical studies.

> **Note:** These videos were recorded with version **0.8.1**. They remain valid,
> although some interface elements may have changed in more recent versions.

Workshop held on 2025-03-11 (English subtitles available in the download):

Part 1:

https://github.com/user-attachments/assets/d8c0bcd8-339f-47e4-9f26-e452b2e87980

Part 2:

https://github.com/user-attachments/assets/ff219478-f3d2-4790-bc45-39a11e227b5b


These sessions are particularly useful after completing the Quick start section.

---

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for branching 
conventions, code style, CI requirements, and the PR workflow.

---

## Roadmap

The following roadmap outlines the main development directions currently guiding DyCoV evolution.

### Axis 1 — Stabilization and model support

* Ongoing bug fixes and robustness improvements
* Complete support for WECC and IEC models (PV, wind, BESS)
* Support for multi-generator topologies
* On-site measurement support for RMS model validation

### Axis 2 — Ease of use and long-term maintenance

* Windows and Docker installation improvements
* Migration of initialization layer to pypowsybl
* Dynamic generation of topology schematics in reports
* Expanded test coverage and typing enforcement
* Documentation and tutorials

### Axis 3 — Consistency with DTR updates

* Support for multiple DTR versions
* Update of fiches according to DTR 2025 revisions (I5)
* Implementation of fiche F16
* New GFM-related fiches (I18) with PPM/BESS differentiation

---

## Contact

For questions, support, or contributions, please refer to the project repository or contact the maintainers.

* Electrical modeling inquiries (RTE): <rte-r-d-raccordement@rte-france.com>
* Software issues and questions (AIA): <dycov@aia.es>
