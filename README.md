# DyCoV — Dynamic grid Compliance Verification

[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Documentation](https://readthedocs.org/projects/sphinx/badge/?version=master)](https://dycov.github.io/index.html)

A tool for automating the verification of dynamic grid compliance requirements
for solar and wind farms (Power Park Modules — PPM), battery energy
storage systems (BESS), and synchronous machines (SM), from model validation
to grid-code compliance assessment. As an end-to-end framework, DyCoV supports
both model validation and compliance assessment workflows used during grid
connection studies.

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

Additionally:

- **Grid‑Forming (GFM) envelope calculation** — computes analytical bounds
  for GFM unit responses (optional workflow)

---

## Getting started

This section helps you choose how to begin with DyCoV depending on your objective.
It acts as a navigation guide to the most relevant workflows and documentation depending 
on your use case (exploration, validation, or study design).

- To run DyCoV quickly and see results → go to **Quick start**
- To validate a real installation → run both validation and performance workflows in sequence
- To build your own study → see input preparation tutorials

Example cases are available in the `examples/` directory and can be copied
and adapted to your own projects.

---

## Inputs and outputs

This section summarizes the typical data exchanged with DyCoV across its workflows.
DyCoV works with time-domain dynamic responses from simulations or measurements.

Typical inputs:

- **Dynawo models** — RMS simulation models of the installation
- **Reference curves** — expected behaviour (used for validation)
- **Producer curves** — simulated responses (used when simulations are provided externally instead of being run through Dynawo)

Typical outputs:

- PDF compliance reports
- Interactive HTML plots
- A structured `Results/` directory (organized per study and scenario)

For full details, see:  
[Preparing inputs](docs/tutorials/preparing_inputs.md)

---

## Installation

This section summarizes the supported installation modes. Choose the one that 
best fits your environment and usage (native, WSL, or development setup).
Once installed, DyCoV is accessed through the `dycov` command-line interface.

For detailed procedures and advanced setups, see:  
[Linux native](docs/installation/linux_native.md)

> **For developers** building from source, see:  
> [Setup](docs/developer/setup.md)

### Linux

DyCoV requires a Linux environment with system dependencies
(e.g. Python ≥ 3.13, build tools, LaTeX).

```bash
# Download and install DyCoV
curl -L https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest/download/linux_install.sh | bash

# Activate environment
source dycov/activate_dycov

# Check CLI
dycov -h
```

---

### Windows (WSL)

DyCoV runs inside a preconfigured WSL (Windows Subsystem for Linux) environment.

**Prerequisite:** WSL must be enabled:  
https://learn.microsoft.com/en-us/windows/wsl/install

Download the following files:

- [dycov_rawimage.tar.gz](https://github.com/dynawo/dynation/releases/latest/download/dycov_rawimage.tar.gz)
- [import_wsl.bat](https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest/download/import_wsl.bat)
- [import_wsl.ps1](https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest/download/import_wsl.ps1)
- [run_dycov_wsl.ps1](https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest/download/run_dycov_wsl.ps1)

Run:

```bash
import_wsl.bat
```

This will import and configure the DyCoV environment automatically.

For details, see:  
[Using the provided image](docs/installation/using_the_provided_image.md)

---

## Quick start

This section demonstrates how to run the main DyCoV workflows on bundled example 
cases, allowing you to quickly verify the installation and explore outputs.

> **Note:** On native installations, ensure the DyCoV environment is activated
> (e.g. `source dycov/activate_dycov`). In WSL and Docker environments,
> it may already be active.

### RMS model validation

This workflow focuses on validating that a dynamic model reproduces expected reference behaviour.

Run:

```bash
dycov validate examples/Model/Wind/WECC4B/ReferenceCurves/ -m examples/Model/Wind/WECC4B/Dynawo/
```

This will:
- run RMS simulations
- compare results against reference curves
- generate validation reports

---

### Electrical performance verification

Here, the system response is evaluated under predefined grid disturbance scenarios.

Run:

```bash
dycov performance -m examples/Performance/Single/WECC4B/Dynawo/
```

This will:
- execute PCS test scenarios
- evaluate compliance with grid‑code requirements

---

### Grid‑Forming analysis (optional)

This optional workflow targets GFM units and computes admissible response envelopes.

Run:

```bash
dycov generateEnvelopes -i examples/GFM/Overdamped/Producer.ini
```

This will:
- compute admissible envelopes
- generate CSV data and plots

For a guided walkthrough, see:  
[Quick start](docs/tutorials/quick_start.md)

---

## Documentation

The documentation is organized to guide users from conceptual understanding to 
detailed workflow execution.

- [Conceptual overview](docs/tutorials/first_steps.md)

- [Preparing inputs](docs/tutorials/preparing_inputs.md)

- Workflow details:
  - [RMS validation](docs/tutorials/rms_model_validation.md)
  - [Performance verification](docs/tutorials/electrical_performance_verification.md)
  - [GFM analysis](docs/tutorials/grid_forming_analysis.md)

These documents provide detailed explanations of each workflow and complement the use of the CLI in real studies.

Developer documentation is available separately.

---

## Reference manuals

In addition to this repository documentation, detailed reference manuals are generated 
and installed locally with DyCoV.

| Installation | Location |
|--------------|----------|
| Linux native | `~/dycov/manual/` |
| Docker / WSL | `~/manual/` |

---

## Workshop

This section provides recorded sessions illustrating DyCoV workflows and usage in practice.

> **Note:** These videos were recorded with version **0.8.1**. They remain valid,
> although some interface elements may have changed in more recent versions.

Workshop held on 2025-03-11 (English subtitles available on download):

Part 1:

https://github.com/user-attachments/assets/d8c0bcd8-339f-47e4-9f26-e452b2e87980

Part 2:

https://github.com/user-attachments/assets/ff219478-f3d2-4790-bc45-39a11e227b5b

---

## Contributing

Contributions are welcome. Please read  
[CONTRIBUTING.md](CONTRIBUTING.md) for branching conventions, code style,
CI requirements, and the PR workflow.

---

## Roadmap

The items below outline the main development axes currently guiding DyCoV evolution.

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
