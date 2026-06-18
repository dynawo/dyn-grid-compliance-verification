# Preparing inputs for DyCoV

**DyCoV version:** 1.1.0  
**Scope:** How to prepare and organize input data for DyCoV workflows,
including directory organization, reference and producer curves,
supported curve formats, and workflow‑specific differences.

---

## 1. Overview

This document explains how to prepare the **input data required by DyCoV**.

It focuses on:
- how inputs are organized in practice,
- reference curves and producer curves,
- supported curve formats,
- mandatory metadata files (DICT),
- differences between DyCoV workflows.

This document applies to:
- RMS model validation,
- electrical performance verification.

It does **not** explain:
- PCS definitions or validation criteria,
- Zone 1 / Zone 3 logic,
- result interpretation.

Those topics are covered in dedicated tutorials.

---

## 2. General principles

DyCoV processes **time‑domain dynamic responses**.

Depending on the workflow, these responses can be:
- **Reference curves**, representing expected or real behaviour,
- **Producer response**, obtained either:
  - from Dynawo RMS simulations, or
  - directly as producer curves.

Dynawo is an open‑source time‑domain simulation tool used to generate
dynamic responses from RMS network models. When using this approach,
DyCoV relies on Dynawo outputs as the producer response.

For details on building Dynawo models and input files (`.dyd`, `.par`, `.jobs`),
see the official documentation: https://dynawo.github.io

Regardless of their origin:
- curves must follow a consistent organization,
- mandatory metadata must be provided,
- supported formats must be respected.

These requirements apply consistently across all DyCoV workflows.

---

## 3. Inputs and project examples

All input formats described in this document are illustrated in the `examples/`
directory of the DyCoV repository. Users are encouraged to inspect these
files and use them as a starting point when preparing their own cases.

DyCoV inputs are always organized **within a concrete example case**.

These examples should be understood as reference implementations of the 
expected structure, not as strict templates that must be reproduced verbatim.

The directory structures described in this tutorial represent
**functional roles**, not mandatory flat layouts.

### Practical recommendation

The easiest way to prepare valid inputs is to start from an existing example:

- copy a case from `examples/`,
- modify curves, parameters and metadata as needed,
- adapt the structure incrementally.

This approach helps avoid common formatting and consistency issues.

---

### 3.1 Examples in the DyCoV repository

Typical RMS model validation examples using Dynawo:

```text
examples/
└── Model/
    └── Wind/
        └── WECC4B/
            ├── Dynawo/
            └── ReferenceCurves/
```

Producer‑curve‑based RMS model validation examples:

```text
examples/
└── Model/
    └── ProducerCurves/
        └── PPM/
            ├── Producer/
            ├── Zone1/
            └── Zone3/
```

Typical electrical performance verification examples using Dynawo:

```text
examples/
└── Performance/
    └── Single/
        └── WECC4B/
            └── Dynawo/
```

Producer‑curve‑based electrical performance verification examples:

```text
examples/
└── Performance/
    └── ProducerCurves/
        └── PPM/
            ├── Producer/
            └── Producer.ini
```

---

## 4. Reference curves

Reference curves represent the **baseline dynamic behaviour**
against which DyCoV validates the producer response.

They are required for:

*   RMS model validation.

They are **not used** in electrical performance verification.

---

### 4.1 Directory organization

Reference curves are always stored **within a concrete validation case**.
In practice, their organization is illustrated by the cases available
under the `examples/` directory of the DyCoV repository.

The structure described below corresponds to the **internal organization
of a `ReferenceCurves/` directory inside a case**, not to a standalone layout.

```text
ReferenceCurves/
└── <Technology>/
    └── Producer/
        ├── CurvesFiles.ini
        ├── PCS_RTE-I*.csv
        └── PCS_RTE-I*.dict
```
**Example:**
`examples/Model/Wind/WECC4B/ReferenceCurves/Producer/CurvesFiles.ini`

Notes:

*   `<Technology>` depends on the installation type (e.g. PPM, BESS).
*   The validation zone (Zone 1 or Zone 3) is encoded directly in the
    **PCS identifier**.
*   Each curve file must have an associated `.dict` file.
*   Reference curves do **not** require electrical or nominal parameters and
    therefore do not use `Producer.ini`.

For example:

```text
examples/
└── Model/
    └── Wind/
        └── WECC4B/
            └── ReferenceCurves/
                └── Producer/
                    ├── CurvesFiles.ini
                    ├── PCS_RTE-I16z1*.csv
                    ├── PCS_RTE-I16z1*.dict
                    ├── PCS_RTE-I16z3*.csv
                    └── PCS_RTE-I16z3*.dict
```

**Examples:**

- CSV:
  `examples/Model/Wind/WECC4B/ReferenceCurves/Producer/PCS_RTE-I16z1*.csv`

- DICT:
  `examples/Model/Wind/WECC4B/ReferenceCurves/Producer/PCS_RTE-I16z1*.dict`

---

### 4.2 Supported curve formats

DyCoV accepts curves in **three formats**:

*   **COMTRADE**
*   **EUROSTAG EXP (ASCII)**
*   **CSV**

All formats are internally normalized by DyCoV
before being used in validation workflows.

The same formats are supported for **reference curves**
and **producer curves**.

---

#### 4.2.1 COMTRADE

*   All COMTRADE versions up to IEEE C37.111‑2013 are accepted.
*   Curves may be provided as:
    *   `CFG` + `DAT`, or
    *   a single `CFF` file.
*   Required metadata must be provided using a `.dict` file.

COMTRADE is typically used when curves originate from:

*   EMT simulations,
*   factory or field measurements.

---

#### 4.2.2 EUROSTAG EXP (ASCII)

*   The EUROSTAG `EXP ASCII` format is supported.
*   Time‑domain RMS signals are extracted by DyCoV.
*   A `.dict` file is mandatory.

This format is commonly used for RMS simulations performed with EUROSTAG.

---

#### 4.2.3 CSV

*   CSV files must use **semicolon (`;`) as delimiter**.
*   A column representing **time** is mandatory.
*   Signal meaning and units are not inferred from the CSV file.

All required metadata must be provided through the `.dict` file.

---

### 4.3 DICT files (mandatory)

For every curve file, DyCoV requires a **DICT** file.

The DICT file:

*   shares the same base name as the curve file,
*   uses the `.dict` extension,
*   follows an INI‑style syntax.

It contains:

1.  **Curves‑Metadata**  
    (signal type, event timing, sampling frequency, etc.)
2.  **Curves‑Dictionary**  
    (mapping between DyCoV‑expected quantities and curve columns)

DyCoV cannot process curves without DICT files.
DICT files are mandatory for all supported curve formats and workflows.

**Example:**
`examples/Model/Wind/WECC4B/ReferenceCurves/Producer/PCS_RTE-I16z1*.dict`

---

## 5. Producer curves

Producer curves represent the **producer response**
when Dynawo simulations are not used.

They may be used in:

*   RMS model validation,
*   electrical performance verification.

---

### 5.1 Directory organization

Producer curves are also always organized within a **concrete example case**.
The structure shown below directly corresponds to the layout used in the
`examples/Model/ProducerCurves/` directory of the DyCoV repository.

Producer curves share the same curve organization
as reference curves, but additionally require
**`Producer.ini` files**, whose usage depends on the workflow.

```text
ProducerCurves/
└── <Technology>/
    └── Producer/
        ├── CurvesFiles.ini
        ├── PCS_RTE-I*.csv
        └── PCS_RTE-I*.dict
    ├── Zone1/
    │   └── Producer.ini
    └── Zone3/
        └── Producer.ini
```

Important points:

*   Curve files are **not separated by zone**.
*   The zone (when applicable) is identified through:
    *   the PCS identifier, and
    *   the associated `Producer.ini` file.
*   In RMS model validation, a distinct `Producer.ini` is required for each zone.
*   In electrical performance verification, a **single** `Producer.ini` is used.

**Examples:**

- Per-zone (RMS):
  `examples/Model/ProducerCurves/PPM/Zone1/Producer.ini`
  `examples/Model/ProducerCurves/PPM/Zone3/Producer.ini`

---

### 5.2 Supported formats

Producer curves support the **same formats**
as reference curves:

*   COMTRADE
*   EUROSTAG EXP
*   CSV

The same DICT and metadata requirements apply.

---

## 6. Workflow‑specific input differences

The input organization described above depends on the **DyCoV workflow**
being executed.

In particular, **RMS model validation** and
**electrical performance verification** differ
in how Dynawo models and producer curves are provided.

---

### 6.1 RMS model validation

RMS model validation introduces additional constraints due to the Zone 1 / Zone 3 separation.

RMS model validation is performed on **two independent zones**:
**Zone 1** and **Zone 3**.
Inputs must therefore explicitly distinguish between these two zones.

This impacts both the Dynawo‑based workflow
and the producer‑curve‑based workflow.

---

#### Using Dynawo

When Dynawo is used for RMS model validation:
- **two separate Dynawo models are required**, one per zone,
- each model has its own `Producer.ini`.

This is illustrated by the project examples, for instance:

```text
examples/
└── Model/
    └── Wind/
        └── WECC4B/
            ├── Dynawo/
            │   ├── Zone1/
            │   │   ├── Producer.dyd
            │   │   ├── Producer.par
            │   │   └── Producer.ini
            │   └── Zone3/
            │       ├── Producer.dyd
            │       ├── Producer.par
            │       └── Producer.ini
            └── ReferenceCurves/
```

Each zone is simulated independently and validated
against the same set of reference curves.

**Examples**:

- RMS (Dynawo, per zone):
  `examples/Model/Wind/WECC4B/Dynawo/Zone1/Producer.ini`
  `examples/Model/Wind/WECC4B/Dynawo/Zone3/Producer.ini`

- RMS (producer curves):
  `examples/Model/ProducerCurves/PPM/Zone1/Producer.ini`
  `examples/Model/ProducerCurves/PPM/Zone3/Producer.ini`

- Performance (Dynawo):
  `examples/Performance/Single/WECC4B/Dynawo/Producer.ini`

- Performance (producer curves):
  `examples/Performance/ProducerCurves/PPM/Producer.ini`

---

#### Using producer curves

When producer curves are used for RMS model validation:

*   a **single set of curves** is provided,
*   but **one `Producer.ini` file per zone is mandatory**.

This organization is illustrated by the examples under
examples/Model/ProducerCurves/, for example:

```text
examples/
└── Model/
    └── ProducerCurves/
        └── PPM/
            ├── Producer/
            │   ├── CurvesFiles.ini
            │   ├── PCS_RTE-I16z1*.csv
            │   ├── PCS_RTE-I16z1*.dict
            │   ├── PCS_RTE-I16z3*.csv
            │   └── PCS_RTE-I16z3*.dict
            ├── Zone1/
            │   └── Producer.ini
            └── Zone3/
                └── Producer.ini
```

In this case:

*   curves are **not separated by zone**,
*   the zone is identified through:
    *   the PCS identifier (`…z1…`, `…z3…`),
    *   and the corresponding `Producer.ini` file.

---

### 6.2 Electrical performance verification

Electrical performance verification uses a **simpler organization**.

There is **no concept of Zone 1 / Zone 3** in this workflow.

#### Using Dynawo

When Dynawo is used:

*   a **single Dynawo model** is provided,
*   a single `Producer.ini` is required.

**Example:**

```text
examples/
└── Performance/
    └── Single/
        └── WECC4B/
            └── Dynawo/
                ├── Producer.dyd
                ├── Producer.par
                └── Producer.ini
```

#### Using producer curves

When producer curves are used:

*   curves are provided in a single `Producer/` directory,
*   a **single `Producer.ini`** is used for the entire case.

Example:

```text
examples/
└── Performance/
    └── ProducerCurves/
        └── PPM/
            ├── Producer/
            │   ├── CurvesFiles.ini
            │   ├── PCS_RTE-I*.csv
            │   └── PCS_RTE-I*.dict
            └── Producer.ini
```

This reflects the fact that electrical performance verification
evaluates grid‑code performance at the **installation level**,
without unit‑level versus plant‑level separation.

---

## 7. Common issues and recommendations

*   Missing `.dict` files always result in an error.
*   Mixing curve formats within the same case is discouraged.
*   Ensure consistent sampling and correct event alignment.
*   Prefer COMTRADE or EUROSTAG formats when curves originate
    from EMT or RMS tools.
*   Misalignment between PCS identifiers and curve content leads 
    to incorrect validation results.

---

## 8. Next steps

Once inputs are prepared:

*   proceed to [**RMS model validation**](rms_model_validation.md), or
*   proceed to [**electrical performance verification**](electrical_performance_verification.md).

