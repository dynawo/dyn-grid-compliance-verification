## Advanced configuration

**DyCoV version:** 1.1.0  
**Scope:** Advanced user configuration of DyCoV execution scope, compliance
thresholds and logging behavior, without modifying DyCoV source code.

---

### 1. Overview

This tutorial describes advanced configuration mechanisms available to
DyCoV users through configuration files.

It focuses on:
- selecting which PCS, benchmarks, and operating conditions are executed,
- adjusting compliance thresholds used in validations,
- controlling logging verbosity for diagnostics and debugging.

This tutorial does **not** cover:
- PCS customization via templates (see *Advanced PCS customization*),
- DyCoV source code modifications,
- developer workflows.

---

### 2. Configuration files and precedence

DyCoV is configured primarily through a `config.ini` file located in the
user configuration directory.

Typical locations are:
- Linux: `~/.config/dycov/`
- Windows: `%APPDATA%\Local\dycov\`

The distributed `config.ini` contains all available options commented out,
together with their default values. Users are encouraged to:
- uncomment only the parameters they want to change,
- duplicate lines when modifying values to keep track of defaults.

In addition to `config.ini`, alternative files such as
`config.ini_BASIC` and `config.ini_ADVANCED` may be provided to distinguish
between common and advanced usage profiles.

Regardless of the configuration file used, user-defined values override the 
defaults provided in the distributed configuration files.

> Note on Dynawo‑related parameters:
>  
> Some configuration options (for example system constants such as nominal
> frequency, base power, or simulation time limits) are expected to match the
> underlying Dynawo installation.
>
> These parameters should only be modified if Dynawo itself has been customized
> and the implications are fully understood. Changing them inconsistently may
> lead to invalid simulation results.

---

### 3. Selecting which PCS are executed

By default, DyCoV executes **all PCS** relevant to the selected workflow.

The execution scope can be restricted globally by editing the `config.ini`
file.

Examples of global selection parameters:

```ini
[Global]
# model_ppm_validation_pcs =
# model_bess_validation_pcs =
# electric_performance_verification_pcs =
```

To validate only a specific PCS:

```ini
[Global]
model_ppm_validation_pcs = PCS_RTE-I16z1
```

Only the listed PCS will be executed; all others are skipped.

This mechanism applies independently to:

*   RMS model validation,
*   electrical performance verification,
*   different technology families (PPM, BESS, SM).

---

### 4. Selecting benchmarks and operating conditions

Each PCS is internally organized as:

*   PCS
    *   Benchmark(s)
        *   Operating Condition(s)

Advanced users can further restrict execution by explicitly selecting:

*   which benchmarks of a PCS are executed,
*   which operating conditions belong to each benchmark.

This is done using the following configuration sections:

```ini
[PCS-Benchmarks]
# PCS_RTE-I16z1 = ThreePhaseFault,SetPointStep,GridFreqRamp,GridVoltageStep

[PCS-OperatingConditions]
# PCS_RTE-I16z1.ThreePhaseFault = TransientBoltedSCR3,TransientBoltedSCR10
```

Example: restrict PCS `PCS_RTE-I16z1` to only two benchmarks:

```ini
[PCS-Benchmarks]
PCS_RTE-I16z1 = ThreePhaseFault,GridVoltageStep
```

Then restrict operating conditions of one benchmark:

```ini
[PCS-OperatingConditions]
PCS_RTE-I16z1.ThreePhaseFault = TransientBoltedSCR3,TransientBoltedSCR10
```

Only the configured PCS, benchmarks and operating conditions will appear
in the execution and reports.

---

### 5. Modifying compliance thresholds (GridCode)

For RMS model validation, compliance thresholds are defined through the
`[GridCode]` section.

These thresholds control the maximum allowed deviation between simulated
curves and reference curves.

Example:

```ini
[GridCode]
# thr_P_mxe_before = 0.05
# thr_P_mxe_during = 0.08
# thr_P_mxe_after  = 0.05
```

To override a threshold:

```ini
[GridCode]
thr_P_mxe_during = 0.002
```

Changing these thresholds directly impacts:

*   compliance results,
*   pass/fail status of PCS,
*   interpretation of validation reports.

No code modification is required.

---

### 6. Adjusting log verbosity

DyCoV logging is controlled via global parameters:

```ini
[Global]
# file_log_level = INFO
# console_log_level = INFO
```

Available levels are:
`CRITICAL`, `FATAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`

Example: enable debug output on the console:

```ini
[Global]
console_log_level = DEBUG
```

This is particularly useful for:

*   understanding which PCS or operating condition is being executed,
*   diagnosing failed simulations,
*   inspecting parameter instantiation during execution.

---

### 7. Best practices

*   Restrict execution scope early when debugging or iterating.
*   Adjust compliance thresholds deliberately and document deviations.
*   Use `DEBUG` logging only when needed; it is verbose by design.
*   Combine configuration‑level filtering with CLI options (e.g. `-p`)
    for faster iteration.

---

### 8. When configuration is not enough

Configuration mechanisms are intended to **adapt execution**, not to
change DyCoV logic.

If your use case requires:

*   new compliance criteria,
*   new KPIs,
*   different validation algorithms,
*   new PCS definitions,

then DyCoV must be extended at the code level.
Refer to the developer documentation for that purpose.

> Note:
> DyCoV also provides an advanced configuration profile intended for expert
> tuning. This profile exposes internal tuning and solver parameters and is
> intentionally not documented as part of the tutorials.
