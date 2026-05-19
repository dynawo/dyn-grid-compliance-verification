# Grid‑Forming (GFM) analysis with DyCoV

**DyCoV version:** 1.1.0  
**Scope:** Generation and analysis of Grid‑Forming (GFM) admissible envelopes
using analytical methods, as supported by DyCoV.

---

## 1. Overview

At a high level, this workflow provides an analytical characterization of Grid‑Forming 
dynamic capabilities. Grid‑Forming (GFM) analysis in DyCoV is a **purely analytical workflow** 
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
**four predefined disturbance families**.

Each case corresponds to a well-defined analytical formulation
and a specific class of grid disturbance:

- **Amplitude Step** — reactive current and reactive power envelopes
  in response to a grid voltage amplitude step.
- **Phase Jump** — active power response to a sudden change
  in the grid voltage phase angle.
- **RoCoF** (Rate of Change of Frequency) — active power response to a
  frequency ramp; finite-duration events are modeled by superimposing
  step responses.
- **SCR Jump** — stability and power response following a sudden change
  in the Short Circuit Ratio (grid impedance), differentiated between
  overdamped and underdamped responses.

The supported cases are implemented directly in DyCoV
and exposed through the GFM workflow.

---

## 4. Inputs required

GFM analysis requires **only analytical input parameters**.
No network model and no time-domain simulation is involved.

Inputs describe:
- nominal electrical quantities,
- GFM control parameters,
- disturbance definition.

### 4.1 Input files

GFM inputs are provided through a `Producer.ini` file containing
a dedicated `[GFM Parameters]` section.

Multiple parameter sets can also be evaluated by supplying a CSV file;
the exact format depends on the supported GFM case.

The structure of the inputs is illustrated in the project examples
under `examples/GFM/`.

---

### 4.2 GFM parameters reference

The following parameters are defined inside the `[GFM Parameters]` section
of `Producer.ini`:

**Nominal quantities:**

| Parameter | Description |
|-----------|-------------|
| `Snom` | Nominal apparent power (MVA) |
| `Unom` | Nominal voltage (kV) |

**Standard control parameters** (used when operating in Standard mode):

| Parameter | Description |
|-----------|-------------|
| `D` | Damping coefficient |
| `H` | Inertia constant (s) |
| `Xeff` | Effective reactance |

**Hybrid control parameters** (used when operating in Hybrid mode):

| Parameter | Description |
|-----------|-------------|
| `D_Overdamped` | Damping coefficient for the overdamped case |
| `H_Overdamped` | Inertia constant for the overdamped case (s) |
| `D_Underdamped` | Damping coefficient for the underdamped case |
| `H_Underdamped` | Inertia constant for the underdamped case (s) |

**Operating limits:**

| Parameter | Description |
|-----------|-------------|
| `p_max_injection` | Maximum active power injection |
| `p_min_injection` | Minimum active power injection (negative for absorption) |
| `q_max` | Maximum reactive power |
| `q_min` | Minimum reactive power |

**Output and sensitivity settings:**

| Parameter | Description |
|-----------|-------------|
| `save_all_envelopes` | If `true`, the CSV output includes all intermediate envelopes (individual overdamped and underdamped traces) in addition to the final merged envelope |
| `RatioMin` | Lower bound for sensitivity analysis on parameter variations |
| `RatioMax` | Upper bound for sensitivity analysis on parameter variations |

---

### 4.3 Standard mode vs. Hybrid mode

DyCoV automatically detects the operating mode based on which parameters
are present in `[GFM Parameters]`:

**Standard mode** — uses `D` and `H`.
DyCoV calculates a single set of upper and lower envelopes.

**Hybrid mode** — activated when both overdamped and underdamped parameter
sets are defined (`D_Overdamped`, `H_Overdamped`, `D_Underdamped`,
`H_Underdamped`).
DyCoV then:
1. Computes independent envelopes for the overdamped and underdamped cases.
2. Constructs a **merged envelope** by taking the maximum of the upper limits
   and the minimum of the lower limits across both cases.

The merged envelope provides a robust validation range that covers
both dynamic regimes simultaneously.

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
```

Each subdirectory represents:

*   a specific GFM configuration,
*   a particular damping regime or envelope processing method.

---

## 6. Generating GFM envelopes

### 6.1 CLI entry point

GFM analysis is executed using the dedicated command:

```bash
dycov generateEnvelopes
```

---

### 6.2 Example execution

From a directory containing a valid GFM input file:

```bash
dycov generateEnvelopes -i Producer.ini
```

DyCoV computes:

*   the admissible upper and lower envelopes,
*   derived quantities required by the selected GFM case.

---

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
```

Where:

- `PCS_RTE-IGFMx` identifies the GFM PCS family.
- `S_<Scenario>` identifies the disturbance scenario
  (e.g. voltage angle step, voltage amplitude step, SCR variation, RoCoF).
- `OC<k>` identifies a specific operating condition for that scenario.

---

### 7.2 Generated artifacts

For each combination of PCS, scenario and operating condition, DyCoV generates:

- **CSV file** containing the numerical time series of the admissible
  envelopes (upper and lower bounds for the relevant signal: $P$, $Q$, or $I_q$).
  When `save_all_envelopes = true`, the file also includes the intermediate
  overdamped and underdamped traces.
- **PNG figure** providing a static visualization of the envelopes alongside
  the PCC signal. In Hybrid mode, individual over/underdamped traces can also
  be shown.
- **HTML file** providing an interactive visualization of the same content.

For **hybrid GFM cases only**, DyCoV also generates:

- **INI dump file (`*_ini_dump.txt`)** containing the exact set of input
  parameters used for that calculation, including internally derived values
  such as the damping ratio $\varepsilon$. Intended for full traceability
  when hybrid configurations are used.

---

### 7.3 Interpretation

Each envelope represents the **admissible dynamic response bounds**
for a given disturbance and operating condition.

GFM analysis does not provide a pass/fail verdict.
Interpretation of envelopes depends on the applicable
engineering or regulatory framework.

---

## 8. Interpreting results

These envelopes can be used in engineering analyses to:

*   assess control robustness,
*   compare design alternatives,
*   support certification or internal validation processes.

Interpretation of envelopes is the responsibility of the user
and depends on the applicable regulatory or engineering framework.

---

## 9. Common clarifications

*   GFM analysis does **not** execute Dynawo.
*   Reference curves are **not** used.
*   Zone 1 / Zone 3 logic does **not** apply.
*   Results are analytical and deterministic.
*   Multiple configurations may be evaluated independently.

---

## 10. Next steps

After GFM analysis, you may:

* refine GFM control parameters,
* compare envelopes across scenarios,
* proceed with RMS or performance studies using validated control assumptions,
  such as:
  - [RMS model validation](docs/tutorials/rms_model_validation.md)
  - [electrical performance verification](docs/tutorials/electrical_performance_verification.md)


---

## References

*   RTE — Technical Reference Documentation (DTR)
*   Analytical Grid‑Forming control theory
*   Dynawo documentation