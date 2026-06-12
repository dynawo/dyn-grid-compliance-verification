# Dynawo PAR Generation from Excel - Design

## 1. Purpose

This document describes the design of a simple Python tool to generate Dynawo PAR file fragments from Excel specifications.

The tool focuses exclusively on parameter extraction and formatting. It does not perform any validation or interpretation of the model.

---

## 2. Scope

The tool:
- Reads parameter values from Excel files
- Preserves the structure and ordering defined in the Excel specification
- Generates formatted PAR fragments ready for copy/paste into Dynawo models

The tool does NOT:
- Validate parameter completeness
- Validate parameter consistency
- Perform model-specific logic or mappings

---

## 3. Inputs and Configuration

### 3.1 Tool Configuration (INI)

The tool includes an internal configuration file (INI format) that defines the selected variant for each model for a given target model.

This configuration is part of the tool and is not considered a primary input.

However, the user may modify it if needed to match the target Dynawo model configuration.

Example:

```ini
[model1]
PREFIX = WPP
REEC = REEC_A
REGC = REGC_A
REPC = REPC_A

[model2]
PREFIX = WT
REEC = REEC_B
REGC = REGC_A
REPC = REPC_A
```

Each section represents a complete target Dynawo model.

When generating a PAR file for a given model `X`, the corresponding section `[X]` must exist in the configuration file.

If the required section is missing, the tool must raise an explicit error.

The tool uses this configuration to select the appropriate parameter set when multiple variants are defined.

---

### 3.2 Excel file (Input)

The Excel file is the single source of truth and must contain:
- Parameter names
- Parameter types
- Parameter values
- Optional comments
- Optional Base units

The Excel structure may contain:
- One or more sheets
- One or more parameter tables per sheet
- Parameter tables defining one or more Dynawo variants (e.g. REEC_A, REEC_C, REEC_D)

---

#### 3.2.1 Excel Design Requirements (Mandatory)

The Excel file structure is a **hard requirement** for the tool to function correctly.

The tool performs a simple structural parsing based on fixed positional rules.  
Therefore, the Excel layout must strictly follow the pattern described below.

##### Table Structure (Mandatory Pattern)

Each parameter table must follow this exact vertical structure:

```

Row N-2 : Block name        (e.g. Electrical Controller, Drive-Train)
Row N-1 : Dynawo name       (e.g. REEC_A, WTGT_A)
Row N   : Header row        (Parameter | Type | Value)
Row N+1+: Data rows

```

Example:

| **Electrical Controller** | | | |
|--|--|--|--|
| **REEC_A**| | | |
| _Parameter_ | _Type_   | _Value_   | Comment |
| PFFLAG    | BOOL   | 0       | ...     |
| Vdip      | DOUBLE | 0.9     | ...     |

##### Example of a valid table

The following example illustrates a valid table structure:

| **Electrical Controller** | | | |
|--|--|--|--|
| **REEC_A** | | | |
| _Parameter_ | _Type_   | _Value_   | Comment |
| PFFLAG    | BOOL   | 0       | This parameter should be set to 0... |
| VFLAG     | BOOL   | 1       |                           |
| Vdip      | DOUBLE | 0.9     | The transition to LVRT... |
| Vup       | DOUBLE | 1.1     | The transition to HVRT... |


In this example:

- `Electrical Controller` (Row N-2) defines the block name
- `REEC_A` (Row N-1) defines the Dynawo model variant
- The header row defines the start of the table
- Each subsequent row defines a parameter

This structure is mandatory and must be strictly respected.

##### Example with multiple variants

| **Electrical Controller** | | | | | | | | |
|--|--|--|--|--|--|--|--|--|
| **REEC_A** | | | **REEC_C** | | | **REEC_D** | | |
| _Parameter_ | _Type_ | _Value_ | _Parameter_ | _Type_ | _Value_ | _Parameter_ | _Type_ | _Value_ |
| PFFLAG    | BOOL | 0     | PFFlag    | BOOL | 0     | PFFLAG    | BOOL | 0     |
| Vdip      | DOUBLE | 0.9 | Vdip      | DOUBLE | 0.9 | Vdip      | DOUBLE | 0.9 |

Each column group represents a different Dynawo variant.

##### Key rules

- The header row must contain exactly:

```

Parameter | Type | Value

```

- The row immediately above the header (**Row N-1**) must contain the **Dynawo model or variant name**:
- Examples: `REEC_A`, `REGC_B`, `WTGT_A`

- The row above (**Row N-2**) must contain the **block or component name**:
- Examples: `Electrical Controller`, `Drive-Train`, `Pitch Control`

- These two rows are **mandatory** and are used to identify:
  - The block structure in the output
  - The mapping between variants and configuration

##### Parameter Naming

The parameter name defined in the Excel file must correspond to the Dynawo parameter name without the model prefix.

For simple parameters:
    PQFlag → PREFIX_PQFlag

For complex or hierarchical parameters:
    wPPControl2015_pControl_omegaWPPu → PREFIX_wPPControl2015_pControl_omegaWPPu

The tool does not construct or interpret hierarchical parameter names.  
It directly applies the model prefix to the provided parameter name.

Therefore:
- The Excel file must provide the exact Dynawo parameter naming (excluding the prefix)
- No transformation or reconstruction of parameter names is performed

##### Multiple tables in the same sheet

A single sheet may contain multiple tables.

Each table is independently detected using the same pattern:

```

(Block name)
(Dynawo name)
Parameter | Type | Value

```

The tool scans the entire sheet and processes all matching tables in order.

### Variant tables (parallel structures)

Some blocks may contain multiple variants (e.g. REEC_A, REEC_C, REEC_D).

In this case, the same pattern applies, but repeated in parallel columns:

```

Electrical Controller
REEC_A                     | REEC_C                     | REEC_D
Parameter |  Type |  Value | Parameter |  Type |  Value | Parameter |  Type |  Value

```

Each variant is parsed independently.

The configuration file (INI) determines which variant is used for output generation.

If the required variant (e.g. REEC_A) is not found in the Excel table, the tool must raise an explicit error.

##### Optional columns

- A `Comment` column may be present
- Additional columns are ignored

Example:

```

Parameter | Type | Value | Comment

```

##### Non-supported structures

The tool does not support:

- Missing "Dynawo name" row
- Missing "Block name" row
- Tables without the exact header `Parameter | Type | Value`
- Free-form layouts without positional consistency
- Automatic inference of structure

---

## 4. Data Model

The extracted data is represented as a nested dictionary structure:

```python
{
  "<sheet_name>": {
    "<block_name>": {
      "<variant_name>": [
        {
          "name": str,
          "type": str,
          "value": str | None,
          "comment": str | None
        }
      ]
    }
  }
}
```

Key principles:

* The order is preserved at all levels:
  * Sheets are processed in the order they appear in the Excel file
  * Tables (blocks and variants) are processed in the order they appear in each sheet
  * Parameters are processed in the order they appear in each table
* Parameter collections are stored as lists (not dictionaries) to preserve ordering
* Values are handled as strings
* No type conversion is performed
* The order is preserved by construction and must not be altered during processing (e.g. no sorting or reordering operations)


***

## 5. Table Detection

A table is identified by the presence of a header row:

```
Parameter | Type | Value
```

Context is derived from previous rows according to the rules defined in section 3.2.1.:

* Row -1 → Dynawo model name (e.g. REEC_A, WTGT_A)
* Row -2 → Block name (e.g. Electrical Controller, Drive-Train)

***

## 6. Handling of Variants

Some tables contain multiple variants in parallel (e.g. REEC_A, REEC_C, REEC_D).

In this case:

* Each variant is extracted independently
* The INI configuration determines which variant is used during generation

The tool does not infer or select variants automatically.

***

## 7. Parameter Extraction Rules

A row is considered valid for extraction if:
- `Parameter` is not empty
- `Type` is not empty

Value handling:
- If `Value` is empty → `value = None`
- If `Value` is not empty → stored as string

Export rule:
- Only parameters with `value != None` are included in the output

***

## 8. Output Generation

The output is a plain text fragment compatible with Dynawo PAR files.

### 8.1 Structure

```
<!-- Sheet name -->
<!-- Block name + selected variant -->

<!-- Optional comment -->
<par type="..." name="..." value="..."/>
```

### 8.2 Rules

* Parameters are generated in the same order as in Excel
* Only parameters with a value are included
* Comments are included only if a parameter is generated
* No transformation is applied to names, types or values

***

## 9. Design Principles

The tool follows these principles:

* Deterministic behavior
* No implicit assumptions
* No validation logic
* Excel as single source of truth
* Separation between data (Excel) and selection logic (INI)

***

## 10. Tool Positioning

This tool is designed as an external utility and is not part of the DyCoV core functionality.

### Rationale

The tool performs a simple transformation from Excel to Dynawo PAR format. It does not involve:

- Simulation
- Validation logic
- Model interpretation

As such, it is considered a preprocessing step rather than part of the DyCoV workflow.

### Integration approach

The tool is implemented as a standalone script located under the `tools/` directory.

Example structure:

```

tools/
excel_to_par/
generate_par.py
config.ini
README.md

```

### Usage

The tool is executed independently from DyCoV, typically before running validation workflows.

Example:

```

python generate_par.py --excel input.xlsx --model model1

```

### Benefits of this approach

- Keeps DyCoV core clean and focused on validation
- Keeps Excel-specific parsing logic (table structure, variant selection, positional interpretation) isolated from the DyCoV core, which focuses on data processing (curves, DataFrames, CSVs)
- Allows independent evolution of the tool as Excel formats change
- Enables reuse outside of DyCoV if needed
