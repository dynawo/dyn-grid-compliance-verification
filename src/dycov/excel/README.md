# DyCoV input generation from Excel

Reads an RTE workbook and writes a complete DyCoV `Model` input set — both zones,
ready to drop into a producer model directory — plus the reference-curve tree:

```
Dynawo/Zone1/Producer.{dyd,par,ini}   # the turbine unit (NoPlantControl)
Dynawo/Zone3/Producer.{dyd,par,ini}   # the aggregated plant (with plant control)
ReferenceCurves/Producer/             # CurvesFiles.ini, one .dict per test, the .csv files
```

It produces the full `dyd` / `par` / `ini` triad by reusing DyCoV's own
per-topology builders (`dycov/files/producer_*_file.py`) and filling the parts
DyCoV cannot know beforehand: the concrete model `lib`s and prefix, the
electrical values, and the topology wiring.

The architecture is **standard-agnostic**: only a thin WECC front-end (parse the
Excel + resolve the variant selection to a Dynawo model) is family-specific;
everything downstream is shared. See the full design in
[`docs/design/DyCoV_input_generation_from_excel_design.md`](../../../docs/design/DyCoV_input_generation_from_excel_design.md).

## Usage

```bash
python -m dycov.excel --excel input.xlsx --outdir DIR
```

- `--excel` — path to the input workbook (required).
- `--outdir` — where the `Dynawo/Zone1` and `Dynawo/Zone3` trees are written
  (required).

The command also prints a **submodel report**: the resolved Zone3/Zone1 `lib` +
prefix and, for every block listed in `Général`, whether its parameter sheet
contributed a selected variant (present/missing), and a **reference-curve
report**: how many tests were described, how many `.csv` were copied, and which
ones — or which metadata columns — are still to be filled in.

The `.xlsx` is read with the package's own stdlib parsing engine
(`workbook.py`: workbook reader, variant tables, `Général` config), which the
legacy `tools/dynawo_par` also imports until its retirement.

## Names live in a configuration file

Every sheet, row, header and marker the generator looks for is an entry of
`dictionary/excel_names.ini`, so a renamed sheet or row is a change there and
not in the code. Two files are read, as with the rest of DyCoV's configuration:
the one shipped here and the user's own copy under the configuration directory
(`~/.config/dycov/excel_names.ini`, `%LOCALAPPDATA%\dycov` on Windows), which
wins key by key. The copy arrives with every line commented out, so
uncommenting a name is what makes the tool read your spelling instead of the
one shipped.

## Expected Excel structure

The workbook is the single source of truth — the generator carries **no
knowledge of the model family** (which blocks exist, which zones they belong to,
or how the `Model Map` key is formed). It reads:

- **`Général`** — the block variant selection (`Type de bloc | Choix | Zone`).
  `Zone` declares, per block, which zone(s) the block's parameters go to
  (`;`-separated, e.g. `Zone1;Zone3`; the plant controller declares `Zone3`
  only). Next to it, a horizontal derived table computed by Excel holds the
  `Model Map` lookup key and the resolved libs; the tool reads the **key cell**
  (located as the column left of the `Zone3 lib` header) verbatim — it never
  reconstructs the key. A workbook saved without cached formula values (by a
  non-Excel writer) is rejected with a message asking to re-save it in Excel.
- **`Model Map`** — a table mapping the key to the Dynawo model:
  `Key | Zone3_lib | Zone3_prefix | Zone1_lib | Zone1_prefix` (the key column is
  located as the column left of `Zone3_lib`, so its header name is free). This
  makes model resolution **install-independent** (RTE decision Q1, path *b*):
  the tool reads the `lib`s from the sheet rather than from a Dynawo
  installation.
- **`Zone1a`** — the generator, its internal `LvTr` (`Z_cc_LvTr`,
  `R_cc_LvTr / X_cc_LvTr`) and its external step-up transformer (`Z_cc_TG`,
  `r_TG`), plus `ConverterLVControl`, `Un1`, `Un2`, `SnZone1`, …; name in col A,
  value in col C.
- **`Zone3`** — the aggregated plant (`Topologie`, PDR limits, the main
  transformer `Z_cc_TP`/`N_prises`, the optional auxiliary load and collector
  line); name in col B, value in col D.
- **`Signaux zone 1` / `Signaux zone 3`** — per zone: the quantities to provide
  with the `.csv` column holding each, the DTR cases to run with the `.csv` file
  of each and its curve metadata, and the folder those files live in.
- **Control sheets** (`REPC`, `REEC`, `REGC`, …) — the selected variant's
  parameters (bare names; the model prefix is prepended on output).

## What it produces

- **DYD** — the topology skeleton from the DyCoV builders, with the concrete
  converter `lib` + terminal injected and the generator given a
  technology-specific, sanity-check-valid id (`PV_Array` / `Wind_Turbine` /
  `Bess`). Laid out like the reference examples: models, then a blank line, then
  the model connections, the remote voltage control, and the remote P/Q control,
  each separated by a blank line.
- **PAR** — written directly from the Excel (no Dynawo install read): control
  parameters (prefixed), the converter, and the network elements with their
  per-unit values on `SnRef = 100 MVA` (see design §9). Each zone's PAR carries
  the control parameters of the blocks that declare that zone in `Général`'s
  `Zone` column, **in the workbook's own order** (sheet → table → parameter), so
  the output is reproducible and diffs stay stable; a run where no block
  declares `Zone1` is refused rather than emitting an incomplete `Zone1`. Per
  Zone1 unit it emits **two** transformers from separate `Zone1a` fields — the
  converter's internal `LvTr` (`RLvTrPu`/`XLvTrPu` from `Z_cc_LvTr`) and the
  external `StepUp_Xfmr` (`TransformerFixedRatio` from `Z_cc_TG`/`r_TG`).
  `ConverterLVControl` sets the converter's nominal voltage in the INI
  (`u_nom_at_PDR` = `Un2` if `True`, `Un1` if `False`). Each parameter carries
  the Excel-derived comments of the `dynawo_par` format (its origin sheet, the
  `table | variant`, and any per-parameter comment / base unit), and the Excel
  `type` is mapped to the Dynawo convention (`double → DOUBLE`,
  `boolean → BOOL`).
- **INI** — the filled `Producer.ini` (PDR limits, per-generator P/Q sharing,
  topology).
- **Reference curves** — `CurvesFiles.ini`, one `.dict` per test with the
  metadata of its own row, and the `.csv` files copied from the folder the sheet
  names. A storage plant runs every DTR case twice, so one results-file cell
  yields two tests and two files, with the suffixes of `[Storage]`
  (`…ActiveInjection.csv`, `…ActiveConsumption.csv`).

Transformer `lib` is **data-driven**: a fixed ratio (`r_TG`/`r_TA`, no tap data)
→ `TransformerFixedRatio`; tap data (`N_prises`/`r_min`/`r_max`, the main
transformer) → `TransformerRatioTapChanger`.

## Scope and non-goals

- **In scope now:** the single-`Zone1` topologies — `S`, `S+Aux`, `S+i`,
  `S+Aux+i` — for PV, wind and BESS WECC models.
- **Deferred:** the multi-generator `M` family. The builders are already
  parametrized to *N* generators, but the Excel cannot yet say *which model*
  each duplicated `Zone1<x>` is (RTE questions Q5).
- **No parameter validation.** RTE ships a complete template; the tool does not
  check values or completeness. Empty control cells are omitted (Dynawo applies
  its default); the tool only reports which submodels are present/missing.

## Example workbooks

Every example under `examples/` carries the workbook it is generated from, next
to its `Dynawo/` and `ReferenceCurves/` directories:

```bash
python -m dycov.excel \
  --excel examples/Model/Wind/WECC4B/Excel/Producer.xlsx \
  --outdir examples/Model/Wind/WECC4B
```

A `Model-*` example describes both zones plus its reference curves; a
`Performance-*` one describes a single tree, and only its Zone 3 half is used.
The performance examples carry no reference curves, so their workbooks keep the
template's placeholder in the results-folder cell.

Regenerating an example reproduces its files, with one known exception: the
auxiliary transformer's `transformer_RPu`/`XPu` differ in the last bit
(`1.0000000000000008e-05` vs `…004e-05`), because the workbook holds the
short-circuit impedance and the R/X ratio and splitting them again is not
bit-exact. It is float noise, not a modelling difference.

## Tests

Tests live under `tests/dycov/excel/`, one module per module of the package,
plus the golden test and the synthetic workbook they share:

```bash
pytest tests/dycov/excel
```

Coverage: the pure electrical helpers, the front-end parsing/resolution, the
PAR-set builders, the reference curves, an end-to-end smoke test on a synthetic
workbook, and an id-agnostic **structural golden** comparing the output against
the authoritative `examples/Model/**` (the wiring DyCoV validates, plus the
data-driven transformer `lib`).

`WECCSample_full.xlsx`, next to the tests, is the AIA-authored fixture they run
on: a 90 MVA PV `S+Aux` case mirroring `examples/Model/Photovoltaics/`
`WECCCurrentSource`, with representative — not certified — values.
`build_sample.py` rebuilds it deterministically and needs `openpyxl`.
