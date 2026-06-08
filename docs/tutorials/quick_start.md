# Quick start with DyCoV

**DyCoV version:** 1.1.0  
**Scope:** Run your first DyCoV studies in a few minutes using the provided examples.

---

## 1. Objective

This tutorial shows how to **run DyCoV immediately** using the examples
bundled with the project.

The goal is to:
- verify that DyCoV is correctly installed,
- execute the main workflows once,
- inspect the generated outputs.

No prior knowledge of PCSs, zones or internal concepts is required to run these examples.

At this stage, you are not expected to analyze results in depth.
The goal is to verify that DyCoV runs correctly and to become familiar
with the type of outputs it generates.

---

## 2. Prerequisites

Before starting, the following is assumed:

- DyCoV is installed and accessible from the command line.
- The `dycov` command is available.
- You are working in a terminal with access to the DyCoV repository.

This tutorial does **not** explain installation steps
or input preparation details.

---

## 3. Repository structure

All examples used in this tutorial are located under the `examples/` directory.

Typical structure:

```text
examples/
├── Model/
├── Performance/
└── GFM/
```

Each subdirectory contains **ready‑to‑run cases**.

---

## 4. Quick RMS model validation

This section demonstrates a complete **RMS model validation** workflow using a 
ready-to-run Dynawo example.

### 4.1 Go to an RMS example

From the root of the DyCoV repository:

```bash
cd examples/Model/Wind/WECC4B
```

This directory contains:

- a `Dynawo/` model,
- a `ReferenceCurves/` folder.

---

### 4.2 Run the validation

```bash
dycov validate ReferenceCurves/ -m Dynawo/
```

DyCoV will:

- run RMS simulations,
- compare results against reference curves,
- generate validation reports.

---

### 4.3 Inspect the outputs

After completion:

- a `Results/` directory is created,
- PDF reports summarize the validation results,
- HTML plots visualize the responses.

You have successfully completed your first RMS model validation.

**Expected result:**

- A `Results/` directory is created
- PDF reports summarize the validation results (including compliance indicators)
- HTML plots show simulated curves against reference curves
- Each test is classified as:
  - **Compliant**
  - **Non-compliant**

At this stage, focus on:
- whether the workflow executed correctly,
- how results are structured,
- how compliance indicators are reported.

---

## 5. Quick electrical performance verification

This section runs an **electrical performance verification**
using a single Dynawo model.

### 5.1 Go to a performance example

From the repository root:

```bash
cd examples/Performance/Single/WECC4B
```

Note:  
The directory name `Single` refers to the **producer‑side electrical topology**,
not to a specific DyCoV workflow.

---

### 5.2 Run the verification

```bash
dycov performance -m Dynawo/
```

DyCoV will:

- execute the applicable PCS test cases,
- evaluate electrical performance criteria.

---

### 5.3 Inspect the outputs

After completion:

- results are written under `Results/`,
- PDF reports summarize PCS compliance,
- HTML plots show relevant electrical quantities.

You have successfully completed your first electrical performance verification.

**Expected result:**

- A `Results/` directory is created
- Each PCS test scenario is evaluated
- PDF reports summarize compliance results
- Each test is marked as:
  - **Compliant**
  - **Non-compliant**

At this stage, focus on:
- understanding how PCS tests are organized,
- where compliance results are reported,
- how to identify pass/fail outcomes.

---

## 6. Quick Grid‑Forming (GFM) analysis

This section runs a **Grid‑Forming envelope calculation**.

No RMS simulation or reference curves are involved.

---

### 6.1 Go to a GFM example

From the repository root:

```bash
cd examples/GFM/Overdamped
```

This directory contains a single `Producer.ini` file.

---

### 6.2 Generate envelopes

```bash
dycov generateEnvelopes -i Producer.ini
```

DyCoV will compute:

- admissible upper and lower envelopes,
- analytical time‑domain results.

---

### 6.3 Inspect the outputs

After completion:

- CSV files contain the envelope data,
- PNG plots visualize the admissible regions

You have successfully completed your first GFM analysis.

**Expected result:**

- CSV files contain the envelope data
- PNG plots visualize the admissible regions
- Interactive HTML plots (when available) allow detailed inspection

At this stage, focus on:
- understanding the envelope structure,
- how results differ from time-domain simulations,
- how output files are organized.

---

## 7. What you have achieved

By following this tutorial, you have:

- run **all main DyCoV workflows**:
    - RMS model validation,
    - electrical performance verification,
    - Grid‑Forming analysis,
- verified that DyCoV is correctly installed,
- generated representative outputs for each workflow.

---

## 8. Next steps

Depending on your objective, continue with:

- [**Preparing inputs**](docs/tutorials/preparing_inputs.md) 
    to understand how to build your own cases.

- [**RMS model validation**](docs/tutorials/rms_model_validation.md) 
    for detailed explanation of zones and PCS‑I16.

- [**Electrical performance verification**](docs/tutorials/electrical_performance_verification.md) 
    for PCS‑based grid‑code compliance.

- [**Grid‑Forming analysis**](docs/tutorials/grid_forming_analysis.md) 
    for in‑depth understanding of GFM envelopes.

Each workflow is documented in a dedicated tutorial.

