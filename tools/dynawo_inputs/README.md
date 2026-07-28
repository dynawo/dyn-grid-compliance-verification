# DyCoV input generation from Excel

A standalone tool that reads a WECC Excel model specification and generates a
complete DyCoV `Model` input set — both zones, ready to drop into a producer
model directory:

```
Dynawo/Zone1/Producer.{dyd,par,ini}   # the turbine unit (NoPlantControl)
Dynawo/Zone3/Producer.{dyd,par,ini}   # the aggregated plant (with plant control)
```

Where the sibling [`dynawo_par`](../dynawo_par/README.md) emits only PAR
*fragments*, this tool produces the full `dyd` / `par` / `ini` triad by reusing
DyCoV's own per-topology builders (`src/dycov/files/producer_*_file.py`) and
filling the parts DyCoV cannot know beforehand: the concrete model `lib`s and
prefix, the electrical values, and the topology wiring.

The architecture is **standard-agnostic**: only a thin WECC front-end (parse the
Excel + resolve the variant selection to a Dynawo model) is family-specific;
everything downstream is shared. See the full design in
[`docs/design/DyCoV_input_generation_from_excel_design.md`](../../docs/design/DyCoV_input_generation_from_excel_design.md)
and the open points for RTE in
[`docs/design/DyCoV_input_generation_RTE_questions.md`](../../docs/design/DyCoV_input_generation_RTE_questions.md).

## Requirements

Unlike `dynawo_par` (standard library only), this tool **reuses the installed
`dycov` package** and therefore needs it on the path (the repository's editable
install is enough) plus its `lxml` dependency. The `.xlsx` itself is read with
the stdlib reader borrowed from `dynawo_par`. Only the example builder
(`examples/build_sample.py`) needs `openpyxl`.

## Usage

```bash
python tools/dynawo_inputs/generate_inputs.py --excel input.xlsx --outdir DIR
```

- `--excel` — path to the input workbook (required).
- `--outdir` — where the `Dynawo/Zone1` and `Dynawo/Zone3` trees are written
  (required).

The command also prints a **submodel report**: the resolved Zone3/Zone1 `lib` +
prefix and which control submodels (`REPC`, `REEC`, `REGC`, `WTGT`, `WTGP`,
`WTGA`, `WTGQ`) are present or missing.

## Expected Excel structure

The workbook is the single source of truth. The tool reads:

- **`Général`** — the block variant selection (`Type de bloc | Choix`), the same
  table `dynawo_par` uses.
- **`Model Map`** — a table mapping the variant combination to the Dynawo model:
  `Key | Zone3_lib | Zone3_prefix | Zone1_lib | Zone1_prefix`, where `Key` is
  `REGC|REEC|WTGT|WTGP|WTGA|WTGQ`. This makes model resolution
  **install-independent** (RTE decision Q1, path *b*): the tool reads the `lib`s
  from the sheet rather than from a Dynawo installation.
- **`Zone1a`** — the generator, its internal `LvTr` (`Z_cc_LvTr`,
  `R_cc_LvTr / X_cc_LvTr`) and its external step-up transformer (`Z_cc_TG`,
  `r_TG`), plus `ConverterLVControl`, `Un1`, `Un2`, `SnZone1`, …; name in col A,
  value in col C.
- **`Zone3`** — the aggregated plant (`Topologie`, PDR limits, the main
  transformer `Z_cc_TP`/`N_prises`, the optional auxiliary load and collector
  line); name in col B, value in col D.
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
  per-unit values on `SnRef = 100 MVA` (see design §9). Per Zone1 unit it emits
  **two** transformers from separate `Zone1a` fields — the converter's internal
  `LvTr` (`RLvTrPu`/`XLvTrPu` from `Z_cc_LvTr`) and the external `StepUp_Xfmr`
  (`TransformerFixedRatio` from `Z_cc_TG`/`r_TG`). `ConverterLVControl` sets the
  converter's nominal voltage in the INI (`u_nom_at_PDR` = `Un2` if `True`,
  `Un1` if `False`). Each parameter carries the Excel-derived comments of the
  `dynawo_par` format (its origin sheet, the `table | variant`, and any
  per-parameter comment / base unit — see that tool's design §8.3), and the
  Excel `type` is mapped to the Dynawo convention (`double → DOUBLE`,
  `boolean → BOOL`).
- **INI** — the filled `Producer.ini` (PDR limits, per-generator P/Q sharing,
  topology).

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

## Example

`examples/WECCSample_full.xlsx` is a committed, fully-populated example — a
90 MVA PV `S+Aux` case built to mirror `examples/Model/Photovoltaics/`
`WECCCurrentSource`: its control parameters and network values are taken from
that example's `Producer.par`, so the generated tree resembles it closely (the
values are representative, not certified). It exists only to exercise the tool
end to end:

```bash
python tools/dynawo_inputs/generate_inputs.py \
  --excel tools/dynawo_inputs/examples/WECCSample_full.xlsx --outdir /tmp/out
```

`examples/build_sample.py` is the helper that rebuilds that workbook
deterministically (requires `openpyxl`):

```bash
python tools/dynawo_inputs/examples/build_sample.py
```

## Tests

Tests live under `tests/tools/` so they are collected by the project's standard
`pytest` run:

```bash
pytest tests/tools/test_dynawo_inputs_electrical.py \
       tests/tools/test_dynawo_inputs_parse.py \
       tests/tools/test_dynawo_inputs_generate.py \
       tests/tools/test_dynawo_inputs_golden.py
```

Coverage: the pure electrical helpers (§9), the front-end parsing/resolution,
the PAR-set builders + an end-to-end smoke test on a synthetic workbook, and an
id-agnostic **structural golden** comparing the tool's output against the
authoritative `examples/Model/**` (the wiring DyCoV validates, plus the
data-driven transformer `lib`).
