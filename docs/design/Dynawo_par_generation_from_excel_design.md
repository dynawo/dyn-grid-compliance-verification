## Dynawo PAR Generation from Excel - Design

### 1. Purpose

This document describes the design of a simple Python tool to generate Dynawo PAR file fragments from Excel specifications.

The tool focuses exclusively on parameter extraction and formatting. It does not perform any validation or interpretation of the model.

---

### 2. Scope

The tool:
- Reads parameter values from an Excel file
- Preserves the structure and ordering defined in the Excel specification
- Generates formatted PAR fragments ready for copy/paste into Dynawo models

The tool does NOT:
- Validate parameter completeness
- Validate parameter consistency
- Perform model-specific logic or mappings

---

### 3. Input

#### 3.1 Excel file (Input)

The Excel file is the **single source of truth**, defining both:
- Model structure
- Parameter values

The only required input is the Excel file:

```bash
python generate_par.py --excel input.xlsx [--outdir DIR]
```

`--outdir` is optional (defaults to the folder containing the Excel file) and
selects where `zone1.par` / `zone3.par` are written.

***

#### 3.1.1 Excel structure overview

The Excel file contains different types of sheets:

* **Structured parameter sheets (parsed by the tool)**:
  * REPC, REEC, REGC, Mechanical Part, etc.
  * These contain parameter tables following the required structure

* **Configuration sheet**:
  * Sheet: `Général`
  * Contains:
    * Block selection (e.g. REEC\_A, REGC\_A, etc.)
    * Global parameters (SnZone1, SnZone3, and the converter count —
      `Nombre de convertisseur`)

* **Descriptive sheets (ignored by the tool)**:
  * Topologie zone 1 / zone 3
  * Signaux zone 1 / zone 3
  * Separator / index sheets (e.g. `Infos générales ->`, `Paramétrage modèle ->`)
  * Any documentation-oriented content

Descriptive sheets are ignored implicitly: any sheet that does not contain a
`Parameter | Type | Value` header simply yields no tables.

Only structured parameter sheets and the configuration sheet are used.

***

#### 3.1.2 Model definition

The model configuration is defined in the sheet **"Général"**.

It provides:

* Selected variant for each block (`Aucun` / empty = block disabled)
* Global parameters (SnZone1, SnZone3, `Nombre de convertisseur`)

The Excel file fully defines the model.  
No external configuration is required.

***

### 3.2 Excel Design Requirements

#### 3.2.1 Table Structure

Each parameter table is anchored on its header row (the row that contains
`Parameter | Type | Value`) and spans **two label rows above it**:

```
Row N-2 : Table name        (e.g. "Plant Controller", "Drive-Train")
Row N-1 : Variant name(s)    (e.g. "REEC_A"  |  "REEC_C")
Row N   : Header row(s)      (Parameter | Type | Value, repeated per variant)
Row N+1+: Data rows
```

* The **table name** (row N-2) is a descriptive label placed at the first
  column of the table block.
* The **variant name** (row N-1) sits directly above each variant's
  `Parameter` column.

Tables may include **multiple variants** in parallel column groups, and a
single sheet may contain **several tables side by side**. For example, the
`Mechanical Part` sheet holds four tables in parallel — `Drive-Train`,
`Pitch Control`, `Aerodynamic`, `Torque Control` — each with its own table
name, variant(s) and header.

***

#### 3.2.2 Variant tables

Each column group (`Parameter | Type | Value`) represents one variant, named in
the row above its `Parameter` column.

Example:

* REEC\_A
* REEC\_C

The selected variant is defined in the **"Général" sheet**.

***

#### 3.2.3 Optional columns

Optional columns:

* `Comment`
* `Base unit`

If both exist:

```
<Comment> | Base unit: <value>
```

Examples of Base unit values:

* Physical units: `s`, `Un`
* Model bases: `SnZone1`, `SnZone3`, `Un, SnZone1`

The tool:

* Does not interpret Base unit
* Only propagates it as metadata in comments

Additional columns are ignored.

***

#### 3.2.4 Non-structured content

Sheets or sections that do not follow the defined table structure are ignored.

***

### 4. Data Model

```python
{
  "<sheet_name>": {
    "<table_name>": {
      "<variant_name>": [
        {
          "name": str,
          "type": str,
          "value": str | None,
          "comment": str | None,
          "base_unit": str | None
        }
      ]
    }
  }
}
```

Key principles:

* Order is preserved at:
  * sheet level
  * table level
  * parameter level
* Parameters stored as lists (order preservation)
* Values handled as strings — **no value conversion**
* The `type` field is stored verbatim from Excel; the mapping to the Dynawo
  convention happens only at output time (see §8.3)

***

### 5. Table Detection

A table is detected by its header cells:

```
Parameter | Type | Value
```

Each `Parameter` header cell starts one variant column group. Context is
derived from the surrounding rows:

* Row directly above the header → **variant name**
* Two rows above the header → **table name** (nearest label at or to the left)
* Sheet → grouping context

Several `Parameter` headers on the same row therefore yield several variants,
and several table-name labels on the same sheet yield several tables.

***

### 6. Handling of Variants

* All variants are parsed independently
* The selected variant is defined in the **"Général" sheet**
* Only the selected variant is used for generation

A block whose selection is `Aucun` (or an empty cell) is **disabled** and
produces no output.

If a selected variant (other than `Aucun`) is not present in any parameter
sheet:

```
→ explicit error
```

The set of enabled blocks depends on the technology, and is driven entirely by
the `Général` selection. For example, a wind turbine enables the mechanical
blocks (Drive-Train, Pitch Control, Aerodynamic, Torque Control), whereas a PV
or BESS plant leaves them on `Aucun` (a BESS additionally selects the battery
variant, e.g. `REEC_C`).

> **Selection vs. order.** The `Général` sheet decides *which* variant each
> block uses, **not** the output order. Blocks are emitted in the order their
> sheets and tables appear in the workbook (§4), regardless of the order of the
> rows in the `Général` selection table.

***

### 7. Parameter Extraction Rules

A row is valid if:

* Parameter is not empty
* Type is not empty

Value handling:

* Empty → ignored
* Non-empty → exported

Sparse variant tables

When multiple variants are defined in parallel columns, some rows may contain parameters for only a subset of variants.

In such cases:
- Each variant must be parsed independently
- A missing parameter in a row for a given variant does not indicate the end of the table
- Rows with empty Parameter cells for a given variant are ignored for that variant only

Parsing continues until the end of the table structure, regardless of intermediate empty rows.

***

### 8. Output Generation

The tool produces **two outputs**:

***

#### 8.1 Zone 1 Output

* Includes all blocks **except REPC**
* Adds header:

```xml
<!-- SnZone1 = <value> -->
```

Where:

* `<value>` is taken directly from Excel (`SnZone1`)

***

#### 8.2 Zone 3 Output

* Includes all blocks
* Adds header:

```xml
<!-- SnZone3 = <value> -->
```

Where:

```
<value> = SnZone3 × Number of converters
```

This value is **only contextual information**.

***

#### 8.3 Parameter Output Format

```xml
  <!-- Sheet name -->
  <!-- Table name | variant -->
  <!-- Optional comment -->
  <par type="..." name="..." value="..."/>
```

Rules:

* Order preserved
* Only parameters with values are included
* Comment + Base unit merged if present (`<comment> | Base unit: <value>`)
* Values are emitted **verbatim** (no value transformation)
* The `type` is mapped to the Dynawo convention: `double → DOUBLE`,
  `boolean → BOOL`, `int → INT`, `string → STRING`; any other value is
  upper-cased. This keeps the fragments valid Dynawo PAR.
* All emitted lines (the SnZone header included) share the same indentation, so
  the fragment can be pasted directly inside a `<set>`.

***

#### 8.4 Important constraint

The tool:

* Does NOT compute model parameters
* Does NOT interpret Base units
* ONLY applies limited, explicit transformations:
  * the SnZone3 output-context value (§8.2), and
  * the Excel-to-Dynawo `type` mapping (§8.3).

***

### 9. Design Principles

* Deterministic behavior
* Excel as single source of truth
* No implicit assumptions
* No validation logic
* No model interpretation
* Limited and explicit transformations only (output context)

***

### 10. Tool Positioning

This tool is an external preprocessing utility.

It:

* Generates PAR content
* Does not simulate models
* Does not validate models

Benefits:

* Keeps DyCoV clean
* Maintains separation of responsibilities
* Enables reproducible workflows
