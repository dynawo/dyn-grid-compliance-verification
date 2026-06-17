# Electrical performance verification with DyCoV

**DyCoV version:** 1.1.0  
**Scope:** Electrical performance verification according to RTE dynamic PCSs,
including applicable PCSs by technology, required inputs, execution workflows,
and result interpretation using Dynawo simulations or producer curves.

---

## 1. Overview

At a high level, this workflow focuses on system-level compliance with grid-code dynamic
performance requirements. Electrical performance verification in DyCoV evaluates the
compliance of an electrical installation with **RTE-defined dynamic performance requirements**
as specified in the applicable PCSs (e.g. I2, I5, I6, I7, I10).

Unlike RMS model validation:
- **reference curves are not used**,
- **there is no distinction between Zone 1 and Zone 3**.

Validation is always performed at the **installation level**, typically at the
Point of Delivery (PDR).

This document explains:
- which PCSs apply depending on the installation technology,
- the required inputs for electrical performance verification,
- the supported execution modes (Dynawo or producer curves),
- how to run DyCoV and interpret the results.

This document does **not** explain how input data is structured or prepared.
It assumes that input data has been prepared following the conventions
described in the **“Preparing inputs”** tutorial.

At this stage, it is important to understand that electrical performance verification
does not rely on curve-to-curve comparison. Each test evaluates whether the installation 
response satisfies the corresponding grid-code requirements, and results are classified as
compliant or non-compliant based on PCS-defined thresholds.

---

## 2. Supported PCSs by technology

Electrical performance verification in DyCoV is based on the 
**RTE dynamic performance PCSs**.
The set of applicable PCSs depends on the **technology of the installation**,
as defined in the RTE Technical Reference Documentation (DTR).

---

### 2.1 Synchronous machines (SM)

For synchronous machines, the following PCSs are defined:

- **PCS‑I2** — Dynamic behavior of voltage regulation and small‑signal stability
- **PCS‑I3** — Stability under load transfer
- **PCS‑I4** — Stability under short circuit
- **PCS‑I6** — Voltage dip ride‑through
- **PCS‑I7** — Overvoltage ride‑through
- **PCS‑I8** — Voltage control under frequency variation
- **PCS‑I10** — Islanded network operation

---

### 2.2 Power Park Modules (PPM)

For Power Park Modules, the following PCSs are defined:

- **PCS‑I2** — Dynamic behavior of voltage regulation and small‑signal stability
- **PCS‑I5** — Reactive current injection during faults
- **PCS‑I6** — Voltage dip ride‑through
- **PCS‑I7** — Overvoltage ride‑through
- **PCS‑I10** — Islanded network operation

---

### 2.3 Battery Energy Storage Systems (BESS)

For Battery Energy Storage Systems, the following PCSs are defined:

- **PCS‑I2** — Dynamic behavior of voltage regulation and small‑signal stability
- **PCS‑I5** — Reactive current injection during faults
- **PCS‑I6** — Voltage dip ride‑through
- **PCS‑I7** — Overvoltage ride‑through
- **PCS‑I10** — Islanded network operation

---

## 3. Conceptual model

This workflow can be understood through the following high-level questions:
- *Does the installation remain connected and stable during grid disturbances?*
- *Does it provide the expected active and reactive power response?*
- *Does it comply with voltage, frequency and ride‑through requirements?*

DyCoV evaluates these criteria by:
- executing PCS‑defined test scenarios,
- computing the required performance indicators,
- evaluating the results against PCS‑defined compliance thresholds.

The producer response is obtained from:
- RMS simulations (Dynawo), or
- producer‑provided curves.

---

## 4. Inputs required

Electrical performance verification requires a **producer response**.

No reference curves are involved.

The producer response can be provided using one of the two methods described
in the following sections.

---

## 5. Using Dynawo

When Dynawo is used, electrical performance verification relies on 
**RMS simulations generated from a single Dynawo model**.

There is no separation by zone.

### 5.1 Directory organization

This organization is illustrated by the project examples under
`examples/Performance/Single/`.

```text
examples/
└── Performance/
    └── Single/
        └── <ModelName>/
            └── Dynawo/
                ├── Producer.dyd
                ├── Producer.par
                └── Producer.ini
```

In this context, **“Single” refers to the electrical topology**
used on the producer side (single generator / WT / PV),
not to a specific DyCoV workflow.

Other producer‑side topologies are supported in DyCoV
depending on the use case and the applicable PCS.

Notes:

- A **single Dynawo model** is used for the entire verification.
- `Producer.ini` provides the electrical and nominal parameters
    required by DyCoV performance tests.
- The Dynawo model is executed independently for each PCS test scenario.

---

## 6. Using producer curves

Instead of Dynawo simulations, electrical performance verification
can be performed using **producer‑provided curves**.

In this case, DyCoV evaluates PCS criteria directly on the provided curves.

### 6.1 Directory organization

This organization is illustrated by the project examples under
`examples/Performance/ProducerCurves/`.

```text
examples/
└── Performance/
    └── ProducerCurves/
        └── <Technology>/
            ├── Producer/
            │   ├── CurvesFiles.ini
            │   ├── PCS_RTE-I*.csv
            │   └── PCS_RTE-I*.dict
            └── Producer.ini
```

Important points:

- Curves are grouped by **PCS identifier**.
- A **single `Producer.ini`** is used for the entire installation.
- The supported curve formats are identical to those used in RMS validation
    (COMTRADE, EUROSTAG EXP, CSV).

---

## 7. PCS execution

For each applicable PCS:

- DyCoV executes the corresponding test scenario,
- computes the required performance indicators,
- evaluates compliance against PCS‑defined thresholds.

Depending on the PCS, evaluated quantities may include:

- voltage and frequency response,
- active and reactive power behavior,
- fault ride‑through and recovery performance,
- islanded operation capabilities.

DyCoV applies PCS definitions **as specified by RTE**,
without reinterpretation or simplification, ensuring that results are consistent
with the official grid-code requirements.


---

## 8. Running electrical performance verification

### 8.1 CLI entry point

```bash
dycov performance
```

---

### 8.2 Example using Dynawo

```bash
dycov performance -m Dynawo/
```

---

### 8.3 Example using producer curves

```bash
dycov performance -c ProducerCurves/
```

---

## 9. Outputs

A successful electrical performance verification produces:

- **PDF reports**
    summarizing compliance per PCS and test case,
- **HTML plots**
    illustrating key electrical quantities and responses,
- a structured **`Results/`** directory
    ensuring full traceability of execution and calculations.

Each PCS and its associated tests are evaluated and reported independently.

In the report:
- each test is evaluated independently,
- results are classified as:
  - **Compliant**
  - **Non-compliant**
- compliance is determined based on PCS-defined thresholds.

---

## 10. Understanding the verification report

Electrical performance verification reports follow a standardized structure
shared across all DyCoV workflows.

For a detailed description of the report structure, see:

→ [Understanding DyCoV reports](understanding_reports.md)

The key specificities of electrical performance verification reports are:

- No reference curves are used  
- Compliance is based on absolute performance criteria  
- Indicators are physical (e.g. response times, settling times, stability)  
- Each PCS defines its own criteria and thresholds  

Results should always be interpreted using both:

- time-domain plots (for qualitative behavior),  
- compliance checks (for quantitative validation)

---

## 11. Common clarifications

- Reference curves must **not** be provided.
- Zone 1 / Zone 3 separation does **not** apply.
- A single `Producer.ini` is always used.
- Dynawo and producer curves are mutually exclusive within a case.

---

## 12. Next steps

After electrical performance verification, you may:

* refine model parameters and re‑run verification
* generate compliance reports for submission
* proceed with additional validation or analysis workflows, such as:
  - [RMS model validation](rms_model_validation.md)

---

## References

- RTE — Technical Reference Documentation (DTR)
- IEC standards referenced by the RTE PCSs
- Dynawo documentation

