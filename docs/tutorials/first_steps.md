# First steps with DyCoV

**DyCoV version:** 1.1.0  
**Scope:** Conceptual and practical overview of DyCoV workflows and usage,
from installation to running first studies.

---

## 1. Overview

This tutorial provides a high‑level overview of how DyCoV is used once it is
installed and available in your environment.

Its goal is to help you understand:
- what DyCoV can do,
- which execution modes are available,
- how inputs and outputs are organized,
- and which tutorials you should follow next.

This document does not explain installation steps, detailed input preparation,
PCS configuration, or advanced workflows.

---

## 2. Prerequisites

The following assumptions are made:
- DyCoV is installed and accessible from the command line.
- The `dycov` command is available.
- Dynawo may be available but is not mandatory for all workflows.

---

## 3. DyCoV workflows at a glance

DyCoV validates the dynamic behavior of electrical installations using
three main workflows.

---

### 3.1 RMS model validation

**Objective:**  
Compare the dynamic response of a model against a reference behavior.

**Mandatory inputs:**
- Reference curves
- One of the following:
  - a Dynawo RMS model (DYD / PAR / INI), or
  - producer curves representing the model response

**CLI entry point:**
```bash
dycov validate
````

**Outputs:**

*   PDF validation reports summarizing compliance results.
*   HTML plots showing producer or simulated curves versus reference curves.
*   A structured Results directory with intermediate data and logs.

***

### 3.2 Electrical performance verification

**Objective:**  
Verify compliance with grid‑code electrical performance requirements.

**Mandatory inputs:**
- One of the following:
  - a Dynawo RMS model, or
  - producer curves

Electrical performance verification does not use reference curves
and does not distinguish between Zone 1 and Zone 3.

**CLI entry point:**
```bash
dycov performance
````

**Outputs:**

*   PDF performance reports aligned with PCS requirements.
*   HTML plots illustrating electrical performance behavior.
*   A structured Results directory for traceability and debugging.

***

### 3.3 Grid‑Forming (GFM) analysis

**Objective:**  
Compute analytical envelopes defining admissible dynamic responses
for Grid‑Forming units.

**Mandatory inputs:**
- Analytical configuration parameters only.

**CLI entry point:**
```bash
dycov generateEnvelopes
````

**Outputs (current status):**

*   CSV files containing computed envelopes and numerical results.
*   PNG plots showing envelopes and associated signals.

This workflow does not generate PDF reports or HTML plots at this stage.

***

## 4. Typical DyCoV workflow

A typical DyCoV workflow consists of:
1. preparing the inputs required for the selected validation mode,
2. running DyCoV using the appropriate command,
3. analyzing the generated results.

Depending on the workflow, DyCoV produces:
- PDF summary reports and HTML plots (RMS model validation and electrical performance verification),
- CSV result dumps and PNG plots (Grid‑Forming analysis),
- a structured Results directory for traceability and debugging.


***

## 5. Next steps

Depending on your objective, continue with:

*   Quick start (run a minimal example),
*   Preparing inputs,
*   RMS model validation,
*   Electrical performance verification,
*   GFM analysis.

