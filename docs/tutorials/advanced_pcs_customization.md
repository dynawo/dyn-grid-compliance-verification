## Advanced PCS customization

**DyCoV version:** 1.1.0  
**Scope:** Advanced user‑side customization of Performance Checking Sheets (PCS)
within existing DyCoV workflows, without modifying DyCoV source code.

---

### 1. Overview

This tutorial explains how to adapt and extend **existing PCS behavior**
by customizing:
- operating conditions (OC),
- and associated report templates.

It is intended for advanced users who need to run controlled variants of
existing tests while preserving the standard DyCoV workflows.

This tutorial does **not** cover:
- DyCoV source code development,
- PCS logic changes,
- workflow orchestration or algorithms.

---

### 2. Prerequisites

The following assumptions are made:

- DyCoV is installed and accessible from the command line.
- You are familiar with the standard DyCoV tutorials.
- You understand what a PCS and an Operating Condition (OC) are.
- You already know how to run validations and inspect results.

---

### 3. Customizing PCS execution scope

When iterating on PCS customization, it is recommended to restrict execution
to a single PCS.

**CLI entry point:**

```bash
dycov validate ... -p PCS_RTE-I16z1
```

This reduces execution time and simplifies result analysis.

---

### 4. Where PCS customizations are defined

Advanced PCS customization is performed through the **user configuration
directory**.

On Linux, this directory is typically:

```text
~/.config/dycov/
```

The relevant substructure is:

```text
~/.config/dycov/
├── config.ini
└── templates/
    ├── PCS/
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

Conceptually:

*   `templates/PCS/` contains user‑defined PCS operating conditions.
*   `templates/reports/` contains LaTeX report templates rendered using Jinja.

---

### 5. Operating Conditions (OC)

> **Note**  
> To understand the distinction between an *Operating Condition* and an
> *Operating Point*, refer to **Chapter 2.1 of the User Manual**.

An Operating Condition defines:

*   the initial operating point (typically V, P, Q),
*   event characteristics (type, timing, duration, magnitude),
*   grid‑side parameters (e.g. SCR).

Each PCS includes a predefined set of operating conditions.
User‑side customization can:

*   override parameters of an existing OC,
*   or introduce a new OC derived from an existing one.

---

### 6. Overriding an existing operating condition

When only a small number of parameters must change, an existing OC can be
overridden.

Example:

```ini
[PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800]
pdr_Q = Qmin
```

Only the parameters defined in the section are overridden.

> Important:
> Changing an OC affects the simulation results but may not automatically update
> the textual description in the final PDF report unless the report template is
> also adapted.

---

### 7. Adding a new operating condition

Adding a new OC is appropriate when:

*   the variation must be explicitly identified,
*   separate reporting is required,
*   or multiple variants are compared systematically.

This process involves:

1.  extending the PCS configuration,
2.  adding a matching report template.

#### 7.1 Extending the PCS configuration

Create a PCS directory under the appropriate category.
Example (model validation, PPM):

```text
~/.config/dycov/templates/PCS/model/PPM/PCS_RTE-I16z1/
```

Create a configuration file:

```bash
touch ~/.config/dycov/templates/PCS/model/PPM/PCS_RTE-I16z1/PCSDescription.ini
```

Copy an existing OC definition and adapt it.
Then:

*   rename the OC consistently (e.g. `Rise` → `RiseQ0`),
*   add it to the benchmark OC list.

Example:

```ini
[PCS-OperatingConditions]
PCS_RTE-I16z1.GridVoltageStep = Rise,Drop,RiseQ0
```

---

#### 7.2 Adding the report template

Create a LaTeX template for the new OC under:

```text
~/.config/dycov/templates/reports/model/PPM/PCS_RTE-I16z1/
```

A practical approach is to copy an existing template:

```bash
cp report.GridVoltageStep.Rise.tex report.GridVoltageStep.RiseQ0.tex
```

Then update:

*   all placeholders embedding the OC name,
*   titles and descriptions,
*   internal links and Jinja variables referencing OC‑specific tables.

---

### 8. Best practices

*   Prefer overriding an existing OC for minor variations.
*   Add a new OC when traceability and reporting matter.
*   Use descriptive OC names.
*   Ensure consistent renaming of all OC‑specific report placeholders.

---

### 9. When not to use this mechanism

User‑side PCS customization is not appropriate when:

*   new PCS semantics are required,
*   new metrics or criteria must be introduced,
*   computation logic or workflows must change.

In those cases, DyCoV must be extended in code.
Refer to the developer documentation.

