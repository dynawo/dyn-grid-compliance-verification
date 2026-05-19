# First steps with DyCoV

**DyCoV version:** 1.1.0  
**Scope:** Conceptual and practical overview of DyCoV workflows and usage,
from installation to running first studies.

---

## 1. Overview

This document provides a high‑level overview of how DyCoV is used once it is
installed and available in your environment.

In particular, it helps you understand:
- what DyCoV can do,
- which execution modes are available,
- how inputs and outputs are organized,
- and which tutorials you should follow next.

This document does not explain installation steps, detailed input preparation,
PCS configuration, or advanced workflows.

---

## 2. Prerequisites

This section outlines the minimal assumptions required to follow this document.

The following assumptions are made:
- DyCoV is installed and accessible from the command line.
- The `dycov` command is available.
- Dynawo may be available but is not mandatory for all workflows.

---

## 3. DyCoV workflows at a glance

The DyCoV CLI exposes three main workflows, each targeting a specific validation objective.

---

### 3.1 RMS model validation

**Objective:**  
Compare the dynamic response of a model against a reference behavior.

**Mandatory inputs:**
- Reference curves
- One of the following:
  - a Dynawo RMS model (DYD / PAR / INI), or
  - producer curves representing the model response

**CLI entry point:** `dycov validate`

**Outputs:**

*   PDF validation reports summarizing compliance results.
*   HTML plots showing producer or simulated curves versus reference curves.
*   A structured Results directory with intermediate data and logs.

---

### 3.2 Electrical performance verification

**Objective:**  
Verify compliance with grid‑code electrical performance requirements.

**Mandatory inputs:**
- One of the following:
  - a Dynawo RMS model, or
  - producer curves

Electrical performance verification does not use reference curves
and does not distinguish between Zone 1 and Zone 3.

**CLI entry point:** `dycov performance`

**Outputs:**

*   PDF performance reports aligned with PCS requirements.
*   HTML plots illustrating electrical performance behavior.
*   A structured Results directory for traceability and debugging.

---

### 3.3 Grid‑Forming (GFM) analysis

**Objective:**  
Compute analytical envelopes defining admissible dynamic responses
for GFM units.

**Mandatory inputs:**
- Analytical configuration parameters only.

**CLI entry point:** `dycov generateEnvelopes`

**Outputs (current status):**

*   CSV files containing computed envelopes and numerical results.
*   PNG plots showing envelopes and associated signals.

This workflow does not generate PDF reports or HTML plots at this stage.

---

## 4. Typical DyCoV workflow

Regardless of the selected validation mode, DyCoV workflows generally follow a common execution pattern:
1. Preparing the inputs required for the selected validation mode,
2. Running DyCoV using the appropriate command,
3. Analyzing the generated results.

Depending on the workflow, DyCoV produces:
- PDF summary reports and HTML plots (RMS model validation and electrical performance verification),
- CSV result dumps and PNG plots (Grid‑Forming analysis),
- a structured Results directory for traceability and debugging.


---

## 5. Next steps

The following documents expand on each aspect of DyCoV usage:
- [Quick start](docs/tutorials/quick_start.md)
- [Preparing inputs](docs/tutorials/preparing_inputs.md)
- [RMS model validation](docs/tutorials/rms_model_validation.md)
- [Electrical performance verification](docs/tutorials/electrical_performance_verification.md)
- [GFM analysis](docs/tutorials/grid_forming_analysis.md)
