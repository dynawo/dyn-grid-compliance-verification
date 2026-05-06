# Grid‑Forming (GFM) analysis with DyCoV

**DyCoV version:** 1.1.0  
**Scope:** Generation and analysis of Grid‑Forming (GFM) admissible envelopes
using analytical methods, as supported by DyCoV.

---

## 1. Overview

Grid‑Forming (GFM) analysis in DyCoV is a **purely analytical workflow**
used to compute **admissible dynamic envelopes** for Grid‑Forming units.

Unlike other DyCoV workflows:
- no RMS simulations are executed,
- no reference curves are required,
- no comparison against PCS thresholds is performed.

This workflow produces **analytical envelopes** that characterize
the admissible dynamic response of a Grid‑Forming unit
for specific disturbance families.

The GFM workflow is independent from:
- RMS model validation,
- electrical performance verification.

---

## 2. Conceptual objective

GFM analysis aims to determine whether a Grid‑Forming unit can operate
safely and stably under specific dynamic disturbances by computing
**upper and lower admissible response bounds**.

Typical questions addressed by GFM analysis include:
- *Is the unit robust against a sudden voltage angle step?*
- *What is the admissible active‑power response envelope?*
- *How do inertia and damping parameters constrain the response?*

The result is not a “pass/fail” verdict but a **quantitative envelope**
that may be:
- examined visually,
- compared against external requirements,
- reused in engineering studies.

---

## 3. Supported GFM cases in DyCoV

DyCoV currently supports GFM envelope generation for
**specific predefined disturbance cases**.

Each case corresponds to:
- a well‑defined analytical formulation,
- a specific class of grid disturbance,
- a set of required GFM parameters.

The supported cases are implemented directly in DyCoV
and exposed through the GFM workflow.

---

## 4. Inputs required

GFM analysis requires **only analytical input parameters**.
No network model and no time‑domain simulation is involved.

Inputs describe:
- nominal electrical quantities,
- GFM control parameters,
- disturbance definition.

### 4.1 Input files

GFM inputs are typically provided using:
- `Producer.ini` files containing nominal and control parameters, or
- CSV files allowing multiple parameter sets to be evaluated.

The exact format and accepted parameters depend on the supported GFM case.

The structure of the inputs is illustrated in the project examples
under `examples/GFM/`.

GFM‑specific parameters are provided through a dedicated
`[GFM Parameters]` section inside the `Producer.ini` file,
as illustrated by the examples under `examples/GFM/`.

---

## 5. Examples and directory organization

The DyCoV repository provides ready‑to‑run GFM examples structured as:

```text
examples/
└── GFM/
    ├── Overdamped/
    │   └── Producer.ini
    ├── Underdamped/
    │   └── Producer.ini
    └── Fusion/
        └── Producer.ini
````

Each subdirectory represents:

*   a specific GFM configuration,
*   a particular damping regime or envelope processing method.

***

## 6. Generating GFM envelopes

### 6.1 CLI entry point

GFM analysis is executed using the dedicated command:

```bash
dycov generateEnvelopes
```

***

### 6.2 Example execution

From a directory containing a valid GFM input file:

```bash
dycov generateEnvelopes -i Producer.ini
```

DyCoV computes:

*   the admissible upper and lower envelopes,
*   derived quantities required by the selected GFM case.

***

## 7. Results and outputs

GFM analysis results are written to a structured `Results/` directory.

The output hierarchy reflects:
- the GFM PCS family,
- the disturbance scenario,
- the operating condition.

### 7.1 Results directory structure

A typical structure is:

```text
Results/
└── PCS_RTE-IGFMx/
    └── S_<Scenario>/
        └── OC<k>/
            ├── *.csv
            ├── *.png
            ├── *.html
            └── *_ini_dump.txt   (only for hybrid cases)
````

Where:

*   `PCS_RTE-IGFMx` identifies the GFM PCS family.
*   `S_<Scenario>` identifies the disturbance scenario
    (e.g. voltage angle step, voltage amplitude step, SCR variation, RoCoF).
*   `OC<k>` identifies a specific operating condition for that scenario.

***

### 7.2 Generated artifacts

For each combination of PCS, scenario and operating condition, DyCoV generates:

*   📄 **CSV file**  
    containing the numerical values of the admissible envelopes.
*   📈 **PNG figure**  
    providing a static visualization of the envelopes.
*   🌐 **HTML file**  
    providing an interactive visualization of the envelopes.

For **hybrid GFM cases only**, DyCoV also generates:

*   🧾 **INI dump file (`*_ini_dump.txt`)**  
    containing the exact set of input parameters used for that calculation.

The INI dump is intended to ensure full traceability
when hybrid input configurations are used.

***

### 7.3 Interpretation

Each envelope represents the **admissible dynamic response bounds**
for a given disturbance and operating condition.

GFM analysis does not provide a pass/fail verdict.
Interpretation of envelopes depends on the applicable
engineering or regulatory framework.

***

## 8. Interpreting results

The generated envelopes represent **admissible dynamic response bounds**.

They can be used to:

*   assess control robustness,
*   compare design alternatives,
*   support certification or internal validation processes.

Interpretation of envelopes is the responsibility of the user
and depends on the applicable regulatory or engineering framework.

***

## 9. Common clarifications

*   ❌ GFM analysis does **not** execute Dynawo.
*   ❌ Reference curves are **not** used.
*   ❌ Zone 1 / Zone 3 logic does **not** apply.
*   ✅ Results are analytical and deterministic.
*   ✅ Multiple configurations may be evaluated independently.

***

## 10. Next steps

After GFM analysis, you may:

*   refine GFM control parameters,
*   compare envelopes across scenarios,
*   proceed with RMS or performance studies
    using validated control assumptions.

***

## References

*   RTE — Technical Reference Documentation (DTR)
*   Analytical Grid‑Forming control theory
*   Dynawo documentation

