# Dynawo → PyPowsybl execution backend

> **ℹ️ Feasibility status (2026-07-08): BLOCKED today by a Dynawo release-cycle mismatch.**
> powsybl-dynawo pins to official Dynawo *releases* (latest = 1.7.0); DyCoV runs Dynawo
> 1.8.0 *development* (master), so pypowsybl 1.15 generates connections for the 1.7.0
> interface and **no dynamic simulation completes** (not even pypowsybl's own example). A
> powsybl-dynawo PR for 1.8.0 exists but ships only after Dynawo 1.8.0 is released — so this
> is a release-cycle blocker, not architectural. Separately: the model catalog is
> runtime-extensible via `additionalModelsFile`, but `Measurements`/PCC wiring, the missing
> `IEC` category, and numerical parity remain open. See
> [`Dynawo_PyPowsybl_feasibility.md`](Dynawo_PyPowsybl_feasibility.md).

## 1. Context

Currently, DyCoV runs dynamic simulations through the Dynawo command-line interface (CLI). Execution is performed by calling `subprocess`, creating working directories where DyCoV stores the PAR, DYD, JOBS, and CRV files, which serve as inputs for Dynawo. Dynawo then writes the results to the outputs directory within the same working directory.

This approach has proven **robust and dependable over time**. In particular, it already supports relatively advanced workflows:

- Solver retry strategies (time-step reduction, tolerance tuning, solver switching)
- Iterative algorithms such as bisection (HIZ, bolted fault, CCT)
- Explicit persistence of the final solver configuration to ensure reproducibility

PyPowsybl offers a Python-native API on top of Dynawo that makes it possible to execute dynamic simulations programmatically, while still relying on **exactly the same Dynawo backend** under the hood.

---

## 2. Goals

The goal of this evolution is to **introduce PyPowsybl as an alternative execution backend**, replacing Dynawo CLI invocations while strictly maintaining DyCoV's current behavior.

More specifically, this work aims to:

- Run dynamic Dynawo simulations through PyPowsybl
- Preserve the same physical modeling and numerical results
- Maintain the existing retry strategy unchanged, both logically and semantically

---

## 3. Non-goals

To maintain a controlled scope and avoid unwanted side effects, the following are explicitly excluded from this evolution:

- ❌ Rewriting or modifying Dynawo's dynamic models
- ❌ Removing filesystem persistence from the solver configuration
- ❌ Refactoring or redesigning `SolverRetryStrategy`

In this context, PyPowsybl is used strictly as an execution backend, not as a modeling or numerical abstraction layer.

---

## 4. Architectural principles

The design is built around a **clear separation between structural aspects of the case and numerical execution aspects**.

### 4.1 Single reexpression of the Dynawo case

- The Dynawo case (PAR / DYD / JOBS / CRV tree) is **reexpressed exactly once** into PyPowsybl objects:
    - a minimal synthetic IIDM network
    - dynamic models derived from DYD files
    - dynamic interconnections
    - events and curves definitions
- This reexpression step is **never repeated** as part of:
    - solver retries
    - bisection iterations
    - parameter sweeps
- This constraint is particularly important for **bisection-based algorithms** (HIZ, bolted fault, CCT), where the same structural model is typically executed many times with small numerical or event-level variations.

### 4.2 Reuse of the in-memory model

Once the structural in-memory representation is created, it is reused in all subsequent executions. Some parameters may vary between executions, related to the solver in the retry strategy, or to the event in bisection searches.

### 4.3 Numerical layer mutability (retry strategy or bisection)

The following elements are considered purely numerical and may change between runs without any impact on the structural model:

- Solver choice (IDA / SIM)
- Solver parameters (time step limits, tolerances, etc.)
- Event parameters 

These changes must be persisted to disk for PyPowsybl to effectively take them into account during execution.

---

## 5. Execution model

The overall execution model can be summarised as follows:

```
Structural level (executed once per case)
----------------------------------------
DYD / PAR / JOBS / CRV → in-memory PyPowsybl model

Numerical level (executed many times)
------------------------------------
solver + solver parameters + event parameters → simulation run
```

This mirrors Dynawo’s own conceptual separation between model definition and numerical integration strategy.

---

## 6. Retry strategy handling

The existing `SolverRetryStrategy` remains **unchanged and unrefactored**.

In particular:

- Retry ordering and stopping conditions are preserved
- Solver mutations follow the same sequence as today:
    - minimum step reduction
    - accuracy tightening
    - insertion of parameters for small networks
    - solver flip (SIM ↔ IDA)

The only behavioural change concerns the execution backend used inside `_attempt()`:

- previously: Dynawo CLI via `subprocess`
- now: PyPowsybl API

`SolverRetryStrategy` remains the **single authoritative component** responsible for solver mutation logic.

---

## 7. Persistence and reproducibility

Filesystem persistence is a **mandatory and non-negotiable requirement** of the design.

### 7.1 PAR and JOBS as the authoritative configuration interface

PyPowsybl does **not** provide an in-memory representation of PAR files. Dynamic model parameters and solver parameters are read by Dynawo from PAR files **exactly as they are in CLI-based execution**.

As a direct consequence:

- Any modification of parameters (whether related to equipment or to the solver)
- **must be written to disk** in the corresponding PAR files
- otherwise, the modification **will not be applied** by the Dynawo backend

Writing to PAR files is therefore **not a matter of convenience or design preference**, but a **hard technical requirement imposed by the Dynawo / PyPowsybl execution model**.

### 7.2 Solver retry persistence

- During retries, solver parameters are updated both:
    - in memory (to steer the retry logic)
    - on disk (PAR/JOBS) to ensure they are effectively applied
- Once a simulation converges successfully:
    - the final solver parameters are persisted to `solvers.par`
    - the selected solver is persisted to `TSOModel.jobs`

This ensures:

- Full reproducibility of the final solution
- Continued compatibility with Dynawo CLI re-execution
- Clear traceability for debugging and audit purposes

The filesystem representation (PAR/JOBS) is therefore considered the **contractual interface** of the simulation, even when execution is orchestrated in memory.

### 7.3 Bisection persistence

- During bisection iterations, event parameters are updated both:
    - in memory (to monitor the current event state)
    - on disk (PAR) to ensure their correct implementation
- Once the search is complete:
    - The final event parameters are saved in `TSOModel.par`

This ensures:

- Full reproducibility of the final solution
- Continued compatibility with Dynawo CLI re-execution
- Clear traceability for debugging and audit purposes

Therefore, the filesystem representation (PAR) is considered the **contractual interface** of the simulation, even when execution is orchestrated in memory.

---

## 8. Design invariants

The following invariants must hold for any future evolution of the execution backend:

- The structural Dynawo case is built once per execution context
- Solver retry logic remains fully centralized in `SolverRetryStrategy`
- Changes to solver or numerical parameters must never trigger a rebuild of the structural model
- Any parameter modification must always be persisted to file (PAR/JOBS)
- PyPowsybl must not evolve into a modelling or numerical abstraction layer
