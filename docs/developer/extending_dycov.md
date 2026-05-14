# Extending DyCoV

This document describes how DyCoV can be extended at the **code level**.

It is intended for developers and contributors who want to add new PCS logic,
extend workflows, or modify internal processing components.

User‑side customization of PCS via configuration files or report templates
is intentionally out of scope and is covered by the usage tutorials.

---

## 1. Overview

DyCoV is designed to be extensible at the **code level** to support:
- new grid‑code requirements,
- new Performance Checking Sheets (PCS),
- new analysis workflows,
- internal improvements and refactors.

This document explains **where and how DyCoV can be extended in code**, and
defines the boundaries between:
- user‑side customization (tutorials),
- and developer‑side extensions (this document).

---

## 2. Extension philosophy

DyCoV extensions follow these principles:

- extensions are explicit and structured,
- PCS logic is separated from workflow orchestration,
- input handling and reporting are centralized,
- duplication of logic across workflows should be avoided.

Extensions should be implemented by:
- reusing existing abstractions,
- extending well‑defined components,
- keeping PCS‑specific logic isolated.

> Important:
> This document focuses exclusively on **code‑level extensions** of DyCoV.
> Some aspects of DyCoV behavior can be altered through user configuration
> (e.g. selecting which PCS or operating conditions are executed, adjusting
> compliance thresholds, or changing log verbosity) without modifying the
> codebase.
>
> These configuration‑level customizations are intentionally out of scope
> of this document and are covered by the advanced usage tutorials.

---

## 3. What can be extended in code

Typical code‑level extension points include:

- adding a new PCS implementation,
- modifying the logic of an existing PCS,
- extending or creating workflows (Model Validation, Performance, GFM),
- introducing new analytical computations,
- adding new internal metrics or criteria,
- refactoring core components for maintainability.

Not all internal components are intended to be extended directly.

---

## 4. Adding or modifying a PCS (code‑level)

This section describes the **conceptual responsibilities and structure** of a PCS
implementation in DyCoV.

It explains what a PCS is expected to define and where its logic belongs,
but does not provide a step‑by‑step implementation guide.

For a complete procedural walkthrough, see section 4.3 and the linked guide.

It does **not** cover:
- overriding operating conditions,
- adding user‑defined operating conditions,
- customizing report templates.

Those topics are covered in the *Advanced PCS customization* tutorial.

---

### 4.1 Scope of a PCS in code

A PCS implementation typically defines:
- the set of tests to be executed,
- how simulations are instantiated,
- which signals are extracted,
- how metrics are computed,
- how compliance is evaluated.

PCS logic is **domain‑specific** and should not include:
- generic workflow orchestration,
- command‑line parsing,
- reporting infrastructure.

---

### 4.2 Recommended development approach

When adding or modifying a PCS, the typical development process is:

1. Identify an existing PCS with similar behavior.
2. Reuse common utilities and abstractions.
3. Keep PCS logic focused and self‑contained.
4. Validate behavior using example cases.
5. Add or update tests where applicable.

Avoid embedding PCS‑specific behavior:
- in CLI code,
- in generic workflow controllers.

(Note: a complete step-by-step implementation guide is provided in section 4.3.)

---

### 4.3 Step-by-step guide

If you want to implement a new PCS in practice, follow the dedicated guide linked below.

The previous sections describe *where* PCS logic is implemented and how it
fits into the DyCoV architecture.

For a complete, step-by-step guide on how to implement a new PCS — including:
- modifying the validation pipeline,
- updating configuration,
- adding templates,
- creating examples,
- and writing tests,

→ Start here: [add_new_pcs.md](add_new_pcs.md)

This guide is recommended for new contributors who want to implement
their first PCS in DyCoV.

---

## 5. Extending workflows

DyCoV workflows (e.g. RMS Model Validation, Electrical Performance,
Grid‑Forming analysis) are structured pipelines.

When extending a workflow:
- preserve its overall execution contract,
- introduce new steps explicitly and locally,
- avoid side effects on other workflows.

If a new workflow is required:
- implement it as a clearly separated pipeline,
- reuse existing input handling and reporting mechanisms,
- document its assumptions and limitations.

---

## 6. Input formats and compatibility (code‑level)

DyCoV supports multiple input formats (e.g. COMTRADE, EUROSTAG, CSV)
through internal abstraction layers.

Extending input formats in code should be considered only when:
- existing formats cannot be adapted,
- backward compatibility can be preserved,
- the added complexity is justified.

User‑side input customization through configuration files does **not**
require code‑level changes and is covered by usage tutorials.

---

## 7. Examples and validation

Any code‑level extension **must be validated**.

Use the `examples/` directory to:
- demonstrate new behavior,
- validate correctness,
- provide regression references.

Examples are part of DyCoV’s functional reference and should evolve together
with the code.

---

## 8. Testing considerations

- Unit and functional tests should be added under `tests/`.
- Integration and end‑to‑end validation may be added under
  `tests_integration/` if required.

Integration tests are:
- environment‑dependent,
- potentially long‑running,
- not part of the regular development loop.

They should not be the only validation mechanism.

For practical examples of how DyCoV workflows are executed in tests, see:
- `tests/dycov/utils.py`

In particular, new contributors are encouraged to study how the
`execute_tool` helper is used in existing tests before creating new ones.

---

### Running tests

To execute the test suite, run:

```bash
uv run pytest
```

Alternatively, if your virtual environment is already activated:

```bash
pytest
```

**Note:**

*   Some tests rely on Dynawo being correctly configured (via PATH or `DYNAWOPATH`).
*   If Dynawo is not available, certain tests may fail or be skipped depending on configuration.

---

## 9. When to extend vs. refactor

If adding new functionality requires:
- duplicated logic,
- complex conditional behavior,
- cross‑cutting changes,

a **refactor** may be more appropriate than a direct extension.

Maintaining clarity and long‑term maintainability takes precedence over
short‑term feature additions.

If your goal can be achieved by modifying operating conditions or report
templates **without changing DyCoV logic**, you should **not** extend DyCoV
in code and should instead use the appropriate usage tutorial.

---

## 10. Documentation responsibilities

Any code‑level extension that affects:
- user behavior,
- available workflows,
- inputs or outputs,

must be reflected in the documentation by:
- updating existing tutorials,
- adding new examples,
- or extending reference documentation.

Developer‑only refactors with no user impact may be documented in code only.