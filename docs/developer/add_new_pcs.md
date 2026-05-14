# Adding a new PCS to DyCoV

**Scope:** Developer guide for adding a new Performance Checking Sheet (PCS)
to the DyCoV codebase.

---

## 1. Overview

This document explains how to add a new PCS at the **code level**.

There are two scenarios depending on whether the new PCS requires a new
validation test or only reuses existing ones:

- **Scenario A** — The new PCS uses only existing validation tests.
  Only configuration files and report templates need to be added.
- **Scenario B** — The new PCS requires a new validation test that is not
  yet implemented. Scenario A must be completed first, then the new test
  is added in code.

If your goal is to customize an existing PCS **without modifying DyCoV
source code** (e.g. overriding operating conditions or adding a new OC),
see [advanced_pcs_customization.md](../tutorials/advanced_pcs_customization.md)
instead.

---

## 2. Where PCS definitions live

DyCoV maintains two separate template trees:

| Location | Purpose |
|----------|---------|
| `src/dycov/templates/` | Built-in PCS definitions shipped with the code |
| `~/.config/dycov/templates/` | User-side overrides and additions (not in source control) |

When adding a new PCS to the codebase, all changes go under
`src/dycov/templates/`.

The tree under `src/dycov/templates/` is organized as follows:

```text
src/dycov/templates/
├── PCS/
│   ├── model/
│   │   ├── BESS/
│   │   └── PPM/
│   └── performance/
│       ├── BESS/
│       ├── PPM/
│       └── SM/
├── inputs/
│   ├── model/
│   │   ├── BESS/
│   │   └── PPM/
│   └── performance/
│       ├── BESS/
│       ├── PPM/
│       └── SM/
└── reports/
    ├── model/
    │   ├── BESS/
    │   └── PPM/
    └── performance/
        ├── BESS/
        ├── PPM/
        └── SM/
```

---

## 3. Scenario A — New PCS using existing tests

### 3.1 Create the PCS configuration

Create a directory for the new PCS under the appropriate category in
`src/dycov/templates/PCS/`. For example, for a new model validation PCS
for PPM:

```text
src/dycov/templates/PCS/model/PPM/PCS_RTE-I16zX/
```

Inside it, create `PCSDescription.ini` following the structure of an existing
PCS (e.g. `PCS_RTE-I16z1/PCSDescription.ini`).

The file defines:
- the benchmarks belonging to the PCS,
- the operating conditions (OC) for each benchmark,
- the validation tests to execute (referencing existing test names),
- the curves required for each OC report.

If a benchmark requires a network impedance table
(`TableInfiniteBus.txt`, `TableVariableImpedance.txt`), place them
in a subdirectory named after the benchmark:

```text
src/dycov/templates/PCS/model/PPM/PCS_RTE-I16zX/
├── PCSDescription.ini
└── GridVoltageDip/
    ├── TableInfiniteBus.txt
    └── TableVariableImpedance.txt
```

### 3.2 Add reference curve DICT files

For each OC of the new PCS, add a `.dict` file under the appropriate
`inputs/` path:

```text
src/dycov/templates/inputs/model/PPM/ReferenceCurves/Producer/
    PCS_RTE-I16zX.<Benchmark>.<OC>.dict
```

DICT files map DyCoV-expected signal names to curve columns and provide
event metadata. Use an existing `.dict` file from the same benchmark
family as a reference.

### 3.3 Create the report templates

Create a directory for the PCS under `src/dycov/templates/reports/`:

```text
src/dycov/templates/reports/model/PPM/PCS_RTE-I16zX/
```

Inside it, add:

- One LaTeX template per OC:
  `report.<Benchmark>.<OC>.tex`
- A top-level summary template:
  `report.RTE-I16zX.tex`
- A `Makefile` (copy from an existing PCS and update the report name).

Templates use Jinja2 syntax with Jinja delimiters adapted for LaTeX
compatibility (see existing templates for the exact syntax).

The substitution variables available in templates are generated
automatically by `_pcs_replace` in `src/dycov/report/report.py`.
The available Jinja prefixes and their content are described in
section 4.3 below.

---

## 4. Scenario B — New PCS with a new validation test

Complete all steps in Scenario A first. Then follow the steps below to
implement the new test.

### 4.1 Register the test in `benchmark.py`

Open `src/dycov/model/benchmark.py` and locate
`__initialize_validation_by_benchmark`.

Register the new test by adding a call to `compliance_list.append`:

```python
# For a performance test:
compliance_list.append(
    validations, pcs_benchmark_name, "Performance-Validations", "my_new_test"
)

# For a model validation test:
compliance_list.append(
    validations, pcs_benchmark_name, "Model-Validations", "my_new_test"
)
```

The string `"my_new_test"` must match the key used in `PCSDescription.ini`
to associate the test with the PCS.

### 4.2 Implement the test logic

Depending on the test type, add the implementation to the appropriate
validator class:

| Test type | File | Class |
|-----------|------|-------|
| Performance | `src/dycov/validation/performance.py` | `PerformanceValidator` |
| Model validation | `src/dycov/validation/model.py` | `ModelValidator` |
| Shared utilities | `src/dycov/validation/common.py` | (module-level functions) |

Add a private method to the appropriate class following the existing
patterns (e.g. `__check_*` for checks, `__calculate_*` for computations).

Call the new method from `__check` (for checks) or `__calculate`
(for computations) within the same class, guarded by
`compliance_list.contains_key`, following the pattern used for existing
tests:

```python
if compliance_list.contains_key(["my_new_test"], self._validations):
    self.__check_my_new_test(results)
```

Store all outputs in the `results` dict using descriptive keys:

```python
results["my_new_test_value"] = computed_value
results["my_new_test_check"] = computed_value < threshold
results["compliance"] &= results["my_new_test_check"]
```

### 4.3 Expose the result in the report

The `_pcs_replace` function in `src/dycov/report/report.py` assembles
the substitution maps that populate the LaTeX templates. Results stored
in the `results` dict are made available to templates through these maps.

The existing map modules and their Jinja prefixes are:

| Module | Prefix | Content |
|--------|--------|---------|
| `results.py` | `rm<OC>` | Overall pass/fail and computed values |
| `compliance.py` | `cm<OC>` | Per-criterion compliance checks |
| `thresholds.py` | `thm<OC>` | Threshold values |
| `signal_error.py` | `em<OC>` | MAE / ME / MXE per signal |
| `steady_state_error.py` | `ssem<OC>` | Steady-state error |
| `characteristics_response.py` | `tem<OC>` | Reaction / rise / settling times |
| `active_power_recovery.py` | `apr<OC>` | Active power recovery indicators |

Where `<OC>` is derived from the operating condition name by removing the
case separator and `_RTE-` (e.g. `PCS_RTE-I16z1.Benchmark.Rise` →
`I16z1BenchmarkRise`).

Check whether the new result fits naturally into one of these existing
modules. If it does, add it there. If the result introduces a genuinely
new category, create a new map module and register it in `_pcs_replace`
following the pattern of the existing ones:

```python
my_new_map = my_new_module.create_map(oc_results)
subst_dict = subst_dict | {"mynew" + operating_condition_: my_new_map}
```

Then reference the new Jinja variable in the LaTeX template using the
corresponding prefix.

---

## 5. Validation

After adding the new PCS:

1. Run the existing test suite to verify no regressions:
   ```bash
   pytest tests/
   ```

2. Add an example case under `examples/` that exercises the new PCS.

3. Run DyCoV against the example to verify end-to-end behavior:
   ```bash
   dycov validate examples/<your_new_case>/ReferenceCurves/ \
                  -m examples/<your_new_case>/Dynawo/ \
                  -p PCS_RTE-I16zX
   ```

4. Inspect the generated PDF report and HTML plots for correctness.

5. Add unit tests under `tests/` covering the new test logic.