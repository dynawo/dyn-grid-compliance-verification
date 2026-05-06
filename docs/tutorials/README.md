# DyCoV tutorials — Reading guide

This directory contains the user‑facing tutorials for DyCoV.

These tutorials explain how to use DyCoV once it is installed and are
designed to be read in the following order.

---

## Prerequisites

Before following the tutorials in this directory, make sure that DyCoV is
installed using one of the supported installation methods:

- Using the prebuilt distribution image (recommended)
- Native Linux installation (advanced users only)

---

## 1. First steps

Start here to understand:
- what DyCoV does,
- the available workflows,
- the meaning of Zone 1 and Zone 3 validations.

➡️ `first_steps.md`

---

## 2. Preparing inputs

Read this tutorial to learn:
- how to organize input directories,
- supported curve formats (COMTRADE, EUROSTAG, CSV),
- required metadata and DICT files.

➡️ `preparing_inputs.md`

---

## 3. RMS model validation

This tutorial explains:
- RMS validation according to PCS‑I16,
- differences between PPM and BESS,
- Zone 1 / Zone 3 validation logic,
- interpretation of results.

➡️ `rms_model_validation.md`

---

## 4. Electrical performance verification

This tutorial focuses on:
- grid‑code performance validation,
- PCS execution without reference curves,
- simulation‑based and curve‑based workflows.

➡️ `electrical_performance_verification.md`

---

## 5. Grid‑Forming (GFM) analysis

This tutorial explains:
- analytical Grid‑Forming envelope calculation,
- supported disturbance scenarios,
- interpretation of admissible envelopes,
- standard and hybrid configurations.

➡️ `grid_forming_analysis.md`

---

## 6. Advanced topics

The following tutorial covers advanced usage scenarios and is intended for
experienced users.

### Advanced PCS customization

Learn how to:
- customize existing PCS behavior,
- override operating conditions,
- add new operating conditions,
- adapt report templates,

**without modifying DyCoV source code**.

➡️ `advanced_pcs_customization.md`

### Advanced configuration

Learn how to:
- select which PCS, benchmarks and operating conditions are executed,
- adjust compliance thresholds used in model validation,
- control logging verbosity for diagnostics and debugging,

**without modifying DyCoV source code**.

➡️ `advanced_configuration.md`
