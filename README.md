# DyCoV &mdash; Dynamic grid Compliance Verification

[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Documentation](https://readthedocs.org/projects/sphinx/badge/?version=master)](https://dycov.github.io/index.html)

A tool for automating the verification of dynamic grid compliance requirements
for solar and wind farms (Power Park Modules — PPM), battery energy
storage systems (BESS), and synchronous machines (SM), from model validation
to grid-code compliance assessment.

DyCoV supports three main workflows:

- **[RMS model validation](docs/tutorials/rms_model_validation.md)** — verifies
  that a dynamic model matches a reference behavior within the tolerances defined
  by RTE (PCS-I16, Zones 1 and 3), ensuring the model accurately reproduces expected dynamics.

- **[Electrical performance verification](docs/tutorials/electrical_performance_verification.md)** —
  verifies compliance with grid-code dynamic performance requirements
  (PCS-I2, I3, I4, I5, I6, I7, I8, I10), by running standard disturbance test scenarios.

- **[Grid-Forming (GFM) analysis](docs/tutorials/grid_forming_analysis.md)** —
  computes admissible dynamic envelopes for Grid-Forming units analytically,
  providing theoretical bounds on their expected dynamic response.

Each workflow produces results in a structured `Results/` directory:
- RMS model validation and electrical performance verification produce **PDF
  compliance reports** and **interactive HTML plots**.
- GFM analysis produces **CSV files** with the envelope data, **PNG plots**,
  and **interactive HTML plots**.

The tool is pre-configured for the French connection network code
([RTE DTR](https://www.services-rte.com/files/live//sites/services-rte/files/documentsLibrary/20240729_DTR_5867_fr)
Fiches "I"), but can be configured and extended to run other tests.

(c) 2023&ndash;2024 RTE — Developed by Grupo AIA

---

## Table of Contents

- [Installation](#installation)
  - [Linux](#linux)
  - [Windows](#windows)
- [Quick start](#quick-start)
- [Documentation](#documentation)
- [Reference manuals](#reference-manuals)
- [Workshop](#workshop)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Contact](#contact)

---

## Installation

> **For developers** who want to build from source, see
> [docs/developer/setup.md](docs/developer/setup.md).

### Linux

The following commands download and install the latest DyCoV release, activate the environment, and verify that the CLI is available:

```bash
curl -L https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest/download/linux_install.sh | bash
source dycov/activate_dycov
dycov -h
```

For system requirements, Docker installation, and environment activation details,
see [docs/installation/linux_native.md](docs/installation/linux_native.md).

### Windows

This installation deploys DyCoV inside a pre-configured WSL environment.

> **Prerequisite:** WSL (Windows Subsystem for Linux) must be enabled.
> If it is not, follow the
> [official Microsoft instructions](https://learn.microsoft.com/en-us/windows/wsl/install)
> before proceeding.

Download the following files from the
[latest release](https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest)
and place them all in the same folder:

| File | Description |
|------|-------------|
| [`dycov_rawimage.tar.gz`](https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest/download/dycov_rawimage.tar.gz) | Application image — do not unzip manually |
| [`import_wsl.bat`](https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest/download/import_wsl.bat) | Double-click installer |
| [`import_wsl.ps1`](https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest/download/import_wsl.ps1) | Installation logic, called automatically by `import_wsl.bat` |
| [`run_dycov_wsl.ps1`](https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest/download/run_dycov_wsl.ps1) | Launcher, called automatically by the desktop shortcut |

Then double-click `import_wsl.bat`. A desktop shortcut and a Start Menu entry
are created automatically.

For Docker installation, manual procedures (restricted environments), and update
instructions, see [docs/installation/using_the_provided_image.md](docs/installation/using_the_provided_image.md).

---

## Quick start

The commands below run one example from each workflow using the bundled
`examples/` directory and generate results in a `Results/` folder
(reports, plots, or CSV files depending on the workflow).

```bash
# RMS model validation
dycov validate examples/Model/Wind/WECC4B/ReferenceCurves/ \
               -m examples/Model/Wind/WECC4B/Dynawo/

# Electrical performance verification
dycov performance -m examples/Performance/Single/WECC4B/Dynawo/

# Grid-Forming envelope calculation
dycov generateEnvelopes -i examples/GFM/Overdamped/Producer.ini
```

Each workflow requires different inputs (reference curves, models, or configuration files).  
See [docs/tutorials/preparing_inputs.md](docs/tutorials/preparing_inputs.md) for details.

For a guided walkthrough, see  
[docs/tutorials/quick_start.md](docs/tutorials/quick_start.md).

To restrict execution scope or adjust compliance thresholds without touching
source code, see  
[docs/tutorials/advanced_configuration.md](docs/tutorials/advanced_configuration.md).

---

## Documentation

The tutorials below are listed in the recommended reading order.
The developer docs are independent and can be consulted at any time.

**User tutorials** (recommended reading order):

| Topic | Document |
|-------|----------|
| First steps and workflow overview | [docs/tutorials/first_steps.md](docs/tutorials/first_steps.md) |
| Preparing inputs | [docs/tutorials/preparing_inputs.md](docs/tutorials/preparing_inputs.md) |
| RMS model validation | [docs/tutorials/rms_model_validation.md](docs/tutorials/rms_model_validation.md) |
| Electrical performance verification | [docs/tutorials/electrical_performance_verification.md](docs/tutorials/electrical_performance_verification.md) |
| Grid-Forming analysis | [docs/tutorials/grid_forming_analysis.md](docs/tutorials/grid_forming_analysis.md) |
| Advanced configuration | [docs/tutorials/advanced_configuration.md](docs/tutorials/advanced_configuration.md) |
| Advanced PCS customization | [docs/tutorials/advanced_pcs_customization.md](docs/tutorials/advanced_pcs_customization.md) |

**Developer documentation**:

| Topic | Document |
|-------|----------|
| Developer setup | [docs/developer/setup.md](docs/developer/setup.md) |
| Project structure | [docs/developer/project_structure.md](docs/developer/project_structure.md) |
| Extending DyCoV | [docs/developer/extending_dycov.md](docs/developer/extending_dycov.md) |
| Adding a new PCS | [docs/developer/add_new_pcs.md](docs/developer/add_new_pcs.md) |

---

## Reference manuals

DyCoV includes two reference manuals built automatically during installation
for detailed usage and API-level information beyond the tutorials.

**User manual** — covers input file formats, CLI reference, configuration
options, and workflow details.

**Developer manual** — covers internal architecture, extension points,
and contribution guidelines.

Both manuals are available in HTML and PDF formats. Their location depends
on the installation method:

| Installation method | Location |
|---------------------|----------|
| Linux native | `~/dycov/manual/` |
| Docker (Linux or Windows) | `~/manual/` inside the container session |
| WSL (Windows) | `~/manual/` inside the DyCoV session |

---

## Workshop

> **Note:** These videos were recorded with version **0.8.1**. They remain valid,
> although some interface elements may have changed in more recent versions.

Workshop held on 11/03/2025 (English subtitles available on download):

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

The items below represent the main development axes identified for DyCoV.
Contents and priorities may evolve as the project progresses.

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

* Electrical modeling inquiries (RTE): <rte-r-d-raccordement@rte-france.com>
* Software issues and questions (AIA): <dycov@aia.es>
