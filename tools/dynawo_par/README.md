# Dynawo PAR generation from Excel

A standalone preprocessing utility that reads an Excel model specification and
emits two Dynawo PAR fragments, ready to paste into your models:

- `zone1.par` — every selected block **except** REPC
- `zone3.par` — every selected block

It is an external helper that keeps DyCoV clean: it only extracts and formats
parameters. It does **not** validate, interpret, or compute model parameters.
See the full design in
[`docs/design/Dynawo_par_generation_from_excel_design.md`](../../docs/design/Dynawo_par_generation_from_excel_design.md).

## Requirements

Python 3 only — **no third-party dependencies**. `.xlsx` files are parsed
directly with the standard library (`zipfile` + `xml.etree`).

## Usage

```bash
python tools/dynawo_par/generate_par.py --excel input.xlsx [--outdir DIR]
```

- `--excel` — path to the input workbook (required).
- `--outdir` — where to write `zone1.par` / `zone3.par`
  (default: the folder containing the Excel file).

The command also prints a summary of the selected blocks and the SnZone values.

## Expected Excel structure

The workbook is the single source of truth. Three kinds of sheet are recognised:

- **`Général`** (configuration) — two tables:
  - block selection: a `Type de bloc | Choix` table mapping each block to the
    chosen variant (e.g. `REEC → REEC_A`). `Aucun` (or an empty cell) disables
    a block.
  - globals: a `Grandeur | … | Valeur | …` table providing `SnZone1`,
    `Nombre de convertisseur` and `SnZone3`.
- **Parameter sheets** (`REPC`, `REEC`, `REGC`, `Mechanical Part`, …) — one or
  more table blocks laid out as:

  ```
  Row N-2 : table name      (e.g. "Drive-Train", at the block's first column)
  Row N-1 : variant name(s) (e.g. "WTGT_A" | "WTGT_B", above each column group)
  Row N   : Parameter | Type | Value   [ ... repeated per variant ... ] | Base unit
  Row N+1+: data rows
  ```

  Variants run in parallel three-column groups (`Parameter | Type | Value`).
  Optional `Base unit` / `Base` and `Comment` columns (in any order) apply, per
  row, to every variant in the same table block. Variants are parsed
  independently, so sparse rows (a parameter present for only some variants) are
  handled correctly.
- **Descriptive sheets** (`Topologie …`, `Signaux …`, separators) have no
  `Parameter | Type | Value` header and are ignored automatically.

## Output format

Bare fragments (no `<parametersSet>` / `<set>` wrappers), per the design §8.3:

```xml
<!-- SnZone1 = 100 -->

  <!-- REEC -->
  <!-- Electrical Controller | REEC_A -->
  <!-- Base unit: Un -->
  <par type="DOUBLE" name="VDipPu" value="0.9"/>
  <par type="BOOL" name="PfFlag" value="true"/>
```

Behaviour:

- Order is preserved at sheet, table, and parameter level.
- Only parameters that carry a value are emitted.
- The Excel `Type` is mapped to the Dynawo convention
  (`double → DOUBLE`, `boolean → BOOL`, `int → INT`, `string → STRING`;
  anything else is upper-cased). Values are never transformed.
- `Comment` and `Base unit`, when present, are merged into a single comment:
  `<!-- <comment> | Base unit: <value> -->`.
- Zone 3's header value is the only computed quantity:
  `SnZone3 × Nombre de convertisseur` (contextual information only). When either
  input is missing, a clear placeholder is emitted instead.

If a selected variant is not found in any parameter sheet, the tool fails with
an explicit error.

## Example

`examples/WECCSample.xlsx` is a committed, fully-populated example: a complete
wind-turbine case (REPC + REEC + REGC + the four mechanical blocks). The values
are invented (representative, not certified) and exist only to exercise the
tool:

```bash
python tools/dynawo_par/generate_par.py --excel tools/dynawo_par/examples/WECCSample.xlsx
```

`examples/fill_wecc_example.py` is the helper that (re)builds that file from a
WECC template, preserving its structure and the optional `Base unit` /
`Comment` columns, and never modifying the source. Unlike the generator, it
requires `openpyxl` (`uv pip install openpyxl`):

```bash
# regenerate examples/WECCSample.xlsx (default --dst):
python tools/dynawo_par/examples/fill_wecc_example.py --src "Description_modèle_et_courbes (WECC) v0.xlsx"
```

## Tests

Tests live under `tests/tools/test_dynawo_par.py` so they are collected by the
project's standard `pytest` run:

```bash
pytest tests/tools/test_dynawo_par.py
python tests/tools/test_dynawo_par.py        # or standalone
```

Coverage includes synthetic in-memory workbooks (parsing, variants, output
format) and `test_real_example_import`, which imports the committed
`examples/WECCSample.xlsx` to validate the actual Excel reading path (shared
strings, Excel layout) end to end.
