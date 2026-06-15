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

The tool uses this configuration to select the default parameter set when multiple variants are defined.

### 3.2 Excel file (Input)

The Excel file is the single source of truth for parameter values and must contain:
- Parameter names
- Parameter types
- Parameter values
- Optional comments
- Optional Base units

The Excel structure may contain:
- One or more sheets
- One or more parameter tables per sheet
- Parameter tables defining one or more Dynawo variants (e.g. REEC_A, REEC_B, WTGT_A, WTGP_A)

#### 3.2.1 Excel Design Requirements (Mandatory)

The Excel file structure is a hard requirement for the tool to function correctly.

The tool performs a simple structural parsing based on fixed positional rules.
Therefore, the Excel layout must strictly follow the pattern described below.

##### Table Structure (Mandatory Pattern)

Each parameter table must follow this exact vertical structure:

```text
Row N-1 : Table name
Row N   : Header row        (Parameter | Type | Value)
Row N+1+: Data rows
```

Example:

Sheet: Inverter - Control

Table: Electrical Controller

Variants: REEC_A, REEC_B

| **REEC_A** | | | **REEC_B** | | | |
|--|--|--|--|--|--|--|
| _Parameter_ | _Type_ | _Value_ | _Parameter_ | _Type_ | _Value_ | Comment | Base unit |
| PFFLAG | BOOL | 0 | PFFLAG | BOOL | 0 | Set to 0 in normal operation. | |
| PQFLAG | BOOL | 1 | PQFLAG | BOOL | 1 | Reactive priority during FRT. | |
| Vdip | DOUBLE | 0.9 | Vdip | DOUBLE | 0.9 | LVRT threshold. | Unit in p.u. |
| Vup | DOUBLE | 1.1 | Vup | DOUBLE | 1.1 | HVRT threshold. | Unit in p.u. |
| Vref0 | DOUBLE |  | Vref0 | DOUBLE |  | Reference voltage. | |

In this example:
- `Inverter - Control` is the Excel sheet name
- `Electrical Controller` is the table name
- `REEC_A` and `REEC_B` define the Dynawo model variants
- The header row defines the start of the table
- Each subsequent row defines a parameter

This structure is mandatory and must be strictly respected.

##### Example with multiple variants

Sheet: Mechanical Part

Table: Drive-Train / Pitch Control

Variants: WTGT_A, WTGP_A

| **WTGT_A** | | | **WTGP_A** | | | |
|--|--|--|--|--|--|--|
| _Parameter_ | _Type_ | _Value_ | _Parameter_ | _Type_ | _Value_ |
| H | DOUBLE | 4 | Kiw | DOUBLE | 0.1 |
| DAMP | DOUBLE | 1.5 | Kpw | DOUBLE | 3 |
| Htfrac | DOUBLE | 5 | Kic | DOUBLE | 0.1 |
| Freq1 | DOUBLE | 1 | Kpc | DOUBLE | 2 |
| DSHAFT | DOUBLE | 200 | Kcc | DOUBLE | 0 |

Each column group represents a different Dynawo variant.

### 3.2.2 Optional columns

A `Comment` column may be present.
A `Base unit` column may also be present.

If both are present, they are combined in a single comment line in the generated output.

The format is:
- `comment. Base unit: xxx`

If only one of them is present, only that one is written.

Additional columns are ignored.

### 3.2.3 Variant tables (parallel structures)

A single table may contain multiple variants in parallel.

A single sheet may contain multiple tables, each parsed independently as a separate table.
In this case, the same pattern applies, but repeated in parallel columns.

Each variant is parsed independently.

The configuration file (INI) determines which variant is used by default for output generation.

If the required variant is not found in the Excel table, the tool must raise an explicit error.

### 3.2.4 Input examples

The following examples illustrate valid input structure.

Example 1:

Sheet: Inverter - Control

Table: Electrical Controller

Variants: REEC_A, REEC_B

```text
Parameter | Type | Value | Parameter | Type | Value | Comment | Base unit
PFFLAG | BOOL | 0 | PFFLAG | BOOL | 0 | Set to 0 in normal operation. |
PQFLAG | BOOL | 1 | PQFLAG | BOOL | 1 | Reactive priority during FRT. |
Vdip | DOUBLE | 0.9 | Vdip | DOUBLE | 0.9 | LVRT threshold. | Un
Vup | DOUBLE | 1.1 | Vup | DOUBLE | 1.1 | HVRT threshold. | Un
Vref0 | DOUBLE |  | Vref0 | DOUBLE |  | Reference voltage. |
```

Example 2:

Sheet: Inverter - Generator

Table: Generator / Converter

Variants: REGCA1

```text
Parameter | Type | Value | Comment | Base unit
Tg | DOUBLE | 0.02 | Converter time constant. | s
Lvplsw | BOOL | 0 | LVPL switch. |
Iqrmax | DOUBLE | 1 | Max reactive current. | Sn
Iqrmin | DOUBLE | -1 | Min reactive current. | Sn
Accel | INTEGER | 2 | Acceleration mode. |
```

Example 3:

Sheet: Mechanical Part

Table: Drive-Train

Variants: WTGT_A

```text
Parameter | Type | Value
H | DOUBLE | 4
DAMP | DOUBLE | 1.5
Htfrac | DOUBLE | 5
Freq1 | DOUBLE | 1
DSHAFT | DOUBLE | 200
```

Table: Pitch Control

Variants: WTGP_A

```text
Parameter | Type | Value
Kiw | DOUBLE | 0.1
Kpw | DOUBLE | 3
Kic | DOUBLE | 0.1
Kpc | DOUBLE | 2
Kcc | DOUBLE | 0
```

---

## 4. Data Model

The extracted data is represented as a nested dictionary structure:

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
- The order is preserved at all levels:
  - Sheets are processed in the order they appear in the Excel file
  - Tables and variants are processed in the order they appear in each sheet
  - Parameters are processed in the order they appear in each table
- Parameter collections are stored as lists (not dictionaries) to preserve ordering
- Values are handled as strings
- No type conversion is performed
- The order is preserved by construction and must not be altered during processing

---

## 5. Table Detection

A table is identified by the presence of a header row:

```text
Parameter | Type | Value
```

Context is derived from previous rows according to the rules defined in section 3.2.1.

- Row N-1 → Table name
- Row N → Header row
- The sheet name is taken from the Excel sheet tab and used for documentation and output grouping

---

## 6. Handling of Variants

Some tables contain multiple variants in parallel (e.g. REEC_A, REEC_B, WTGT_A, WTGP_A).

In this case:
- Each variant is extracted independently
- The INI configuration determines the default variant used during generation

The tool does not infer or select variants automatically.

If the required variant is not found in the Excel table, the tool must raise an explicit error.

---

## 7. Parameter Extraction Rules

A row is considered valid for extraction if:
- `Parameter` is not empty
- `Type` is not empty

Value handling:
- If `Value` is empty, `value = None`
- If `Value` is not empty, it is stored as string

Export rule:
- Only parameters with `value != None` are included in the output

---

## 8. Output Generation

The output is a plain text fragment compatible with Dynawo PAR files.

### 8.1 Structure

```text
<!-- Sheet name -->
<!-- Table name | selected variant -->
<!-- Optional comment -->
<par type="..." name="..." value="..."/>
```

### 8.2 Rules

- Parameters are generated in the same order as in Excel
- Only parameters with a value are included
- Comments are included only if a parameter is generated
- If both `Comment` and `Base unit` are present, they are written in a single comment line
- The combined format is `comment. Base unit: xxx`
- No transformation is applied to names, types or values

### 8.3 Output examples

```text
<!-- Inverter - Control -->
<!-- Electrical Controller | REEC_A -->
<!-- Set to 0 in normal operation. -->
<par type="BOOL" name="PFFLAG" value="0"/>
<!-- Reactive priority during FRT. -->
<par type="BOOL" name="PQFLAG" value="1"/>
<!-- LVRT threshold. Base unit: Un. -->
<par type="DOUBLE" name="Vdip" value="0.9"/>
<!-- HVRT threshold. Base unit: Un. -->
<par type="DOUBLE" name="Vup" value="1.1"/>

<!-- Inverter - Generator -->
<!-- Generator / Converter | REGCA1 -->
<!-- Converter time constant. Base unit: s -->
<par type="DOUBLE" name="Tg" value="0.02"/>
<!-- LVPL switch. -->
<par type="BOOL" name="Lvplsw" value="0"/>
<!-- Max reactive current. Base unit: Sn. -->
<par type="DOUBLE" name="Iqrmax" value="1"/>
<!-- Min reactive current. Base unit: Sn. -->
<par type="DOUBLE" name="Iqrmin" value="-1"/>
<!-- Acceleration mode. -->
<par type="INTEGER" name="Accel" value="2"/>

<!-- Mechanical Part -->
<!-- Drive-Train / Pitch Control -->
<!-- WTGT_A | WTGP_A -->
<par type="DOUBLE" name="H" value="4"/>
<par type="DOUBLE" name="Kiw" value="0.1"/>
<par type="DOUBLE" name="DAMP" value="1.5"/>
<par type="DOUBLE" name="Kpw" value="3"/>
<par type="DOUBLE" name="Htfrac" value="5"/>
<par type="DOUBLE" name="Kic" value="0.1"/>
<par type="DOUBLE" name="Freq1" value="1"/>
<par type="DOUBLE" name="Kpc" value="2"/>
<par type="DOUBLE" name="DSHAFT" value="200"/>
<par type="DOUBLE" name="Kcc" value="0"/>
```

---

## 9. Design Principles

The tool follows these principles:
- Deterministic behavior
- No implicit assumptions
- No validation logic
- Excel as single source of truth for parameter data
- Separation between configuration selection and data generation logic

---

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

```text
tools/
excel_to_par/
generate_par.py
config.ini
README.md
```

### Usage

The tool is executed independently from DyCoV, typically before running validation workflows.

Example:

```text
python generate_par.py --excel input.xlsx --model model1
```

### Benefits of this approach

- Keeps DyCoV core clean and focused on validation
- Keeps Excel-specific parsing logic isolated from DyCoV core
- Allows independent evolution of the tool as Excel formats change
- Enables reuse outside of DyCoV if needed