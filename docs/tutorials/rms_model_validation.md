# RMS model validation with DyCoV

**DyCoV version:** 1.1.0  
**Scope:** RMS (phasor) model validation according to RTE PCS‑I16, including
Zone 1 / Zone 3 validation, required inputs, execution workflow and result
interpretation for both PPM and BESS installations.

---

## 1. Overview

RMS model validation in DyCoV verifies that the **dynamic response of an
installation**, represented by an open RMS (phasor) model, matches a
**reference behavior** within the tolerances defined by RTE.

This workflow implements the validation process defined in **RTE PCS‑I16**
(Fiche I16), used during **Phase 1 (ION)** of the RTE process.

DyCoV always compares two sets of time‑domain responses:
- **Reference curves**, representing the expected or “real” behavior.
- **Producer response curves**, representing the model behavior.

The producer response can be obtained:
- by running Dynawo RMS simulations, or
- by providing producer curves directly.

This tutorial explains:
- the validation zones defined by PCS‑I16,
- the required inputs for RMS model validation,
- the execution workflow,
- and the interpretation of validation results.

This document does **not** cover how input data is structured or prepared.
It assumes that input data has been prepared following the conventions
described in the **“Preparing inputs”** tutorial.

---

## 2. Validation zones (PCS‑I16)

PCS‑I16 defines two mandatory and independent validation perimeters:

- **Zone 1**
- **Zone 3**

Both zones must be validated as part of RMS model validation.

---

### 2.1 Zone 1 — Unit‑level validation

Zone 1 validates the **intrinsic dynamic behavior of the generating or storage
unit**, without any plant‑level control.

Examples:
- turbine and converter for PPM,
- storage element and converter for BESS.

Typical objectives:
- validate current, voltage and power dynamics,
- assess response to faults, steps and ramps,
- verify compliance independently of aggregation effects.

---

### 2.2 Zone 3 — Plant‑level validation

Zone 3 validates the **complete installation at the Point of Delivery (PDR)**,
including plant‑level or supervisory control.

Typical objectives:
- validate aggregated active and reactive power response,
- assess voltage and frequency behavior at the PDR,
- validate interaction between plant control and the grid.

---

## 3. Applicability of PCS‑I16: PPM vs BESS

RTE defines two variants of PCS‑I16 depending on the installation type:

- **PCS‑I16 for PPM**  
  Applicable to power park modules (wind, photovoltaic, etc.).

- **PCS‑I16 for BESS**  
  Applicable to battery energy storage systems.

Both variants:
- use the same Zone 1 / Zone 3 structure,
- apply the same comparison methodology,
- rely on the same families of compliance indicators.

However, the **set of tests and operating points differs**, notably to account
for **bidirectional power operation in BESS installations**.

DyCoV supports RMS validation for both variants.

---

## 4. Inputs required for RMS model validation

RMS model validation always requires:

1. **Reference curves** (mandatory).
2. **A producer response**, provided either:
   - by Dynawo RMS models, or
   - by producer curves.

---

### 4.1 Reference curves

Reference curves represent the expected dynamic behavior against which the
model is validated.

Their organization is **identical to that of producer curves**, except that:
- no `Zone*` subdirectories exist,
- no `Producer.ini` files are associated.

Typical structure:

```text
ReferenceCurves/
└── <Technology>/
    └── Producer/
        ├── CurvesFiles.ini
        ├── PCS_RTE-I16z1*.csv
        ├── PCS_RTE-I16z1*.dict
        ├── PCS_RTE-I16z3*.csv
        └── PCS_RTE-I16z3*.dict
````

Notes:

*   The validation zone is encoded in the PCS identifier (`z1`, `z3`).
*   DICT files are mandatory and provide signal mapping and event metadata.
*   Reference curves do not require electrical or nominal parameters.

Reference curves and producer curves can be provided using different
supported formats (e.g. COMTRADE, EUROSTAG EXP ASCII or CSV).

The supported formats and their detailed requirements are described
in the “Preparing inputs” tutorial.

***

### 4.2 Dynawo‑based producer response

When using Dynawo, **one RMS model must be provided per zone**.

Typical structure:

```text
Dynawo/
├── Zone1/
│   ├── Producer.dyd
│   ├── Producer.par
│   └── Producer.ini
└── Zone3/
    ├── Producer.dyd
    ├── Producer.par
    └── Producer.ini
```

Each zone is simulated independently and compared against the same reference
curves.

***

### 4.3 Producer‑curve‑based response

When Dynawo is not used, the producer response is provided directly as curves.

The curves are **not split by zone**. Zone separation is handled via:

*   the PCS identifier, and
*   a `Producer.ini` file per zone.

Exact structure:

```text
ProducerCurves/
└── <Technology>/
    └── Producer/
        ├── CurvesFiles.ini
        ├── PCS_RTE-I16z1*.csv
        ├── PCS_RTE-I16z1*.dict
        ├── PCS_RTE-I16z3*.csv
        └── PCS_RTE-I16z3*.dict
    ├── Zone1/
    │   └── Producer.ini
    └── Zone3/
        └── Producer.ini
```

***

## 5. Role of `Producer.ini`

`Producer.ini` is a **fundamental input** for RMS model validation.

DyCoV validation tests require a set of **electrical and nominal parameters**
regardless of how the producer response is obtained.
Therefore, these parameters must be available even when no Dynawo model is used.

Some parameters may also appear in Dynawo `Producer.par`.
When this is the case:

*   the parameter must be provided in both files,
*   the value in `Producer.ini` must be **more restrictive**,
*   DyCoV stops with an error if this condition is not satisfied.

### Zone specificity

Zone 1 and Zone 3 correspond to different physical systems and assumptions.
Each zone therefore requires its **own `Producer.ini` file**.

Providing a single `Producer.ini` for multiple zones is not supported.

***

## 6. PCS‑I16 test coverage

### 6.1 Zone 1 tests

Zone 1 tests validate the intrinsic dynamic behavior of the unit.

For **PPM**, this includes:

*   transient and permanent three‑phase faults,
*   voltage dips with defined depth and duration,
*   active and reactive power steps,
*   voltage steps and frequency ramps,
*   tests under different SCR conditions.

For **BESS**, the same structure applies, with operating points that explicitly
include **positive and negative power injection** to reflect bidirectional
operation.

***

### 6.2 Zone 3 tests

Zone 3 tests validate the complete installation at the PDR.

They reuse dynamic performance tests defined in other PCS fiches
(e.g. voltage, frequency and post‑fault behavior), with reference signals
provided in previous submissions.

Additional tests are required to validate plant‑level or supervisory control,
including large active and reactive power setpoint variations.

***

## 7. Comparison methodology

For all PCS‑I16 tests:

*   only the positive‑sequence component is considered,
*   signals are filtered, resampled and windowed according to IEC
    recommendations,
*   discrepancies are evaluated using:
    *   dynamic indicators (activation, rise, settling times, overshoot),
    *   error metrics: ME, MAE and MXE.

Compliance is assessed against the thresholds defined in PCS‑I16.

***

## 8. Running RMS model validation

### CLI entry point

```bash
dycov validate
```

### Example using Dynawo

```bash
dycov validate ReferenceCurves/ -m Dynawo/
```

### Example using producer curves

```bash
dycov validate ReferenceCurves/ -c ProducerCurves/
```

***

## 9. Outputs

A successful RMS model validation produces:

*   a consolidated **PDF report** summarizing compliance results,
*   **HTML plots** comparing producer response and reference curves,
*   a structured **Results** directory ensuring full traceability.

***

## 10. Next steps

After RMS model validation, you may proceed with:

*   model tuning and re‑validation,
*   **electrical performance verification**,
*   advanced analysis workflows.

***

## References

*   RTE — Fiche I16 (PCS‑I16) for PPM installations
*   RTE — Fiche I16 (PCS‑I16) for BESS installations
*   IEC 61400‑21‑1:2019
*   IEC 61400‑27‑2:2020
*   Dynawo documentation

