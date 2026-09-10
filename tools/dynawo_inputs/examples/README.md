# Example workbooks

One workbook per WECC example shipped in `examples/`, each named after the example it regenerates.
They are filled-in copies of the RTE template, so they double as worked examples of what a complete
input workbook looks like and as the tool's end-to-end test set.

| Workbook | Regenerates | Topology |
| :--- | :--- | :--- |
| `Model-BESS-WECC.xlsx` | `examples/Model/BESS/WECC` | `S+Aux` |
| `Model-Photovoltaics-WECCCurrentSource.xlsx` | `examples/Model/Photovoltaics/WECCCurrentSource` | `S+Aux` |
| `Model-Photovoltaics-WECCVoltageSource1.xlsx` … `4` | `examples/Model/Photovoltaics/WECCVoltageSource1` … `4` | `S+Aux` |
| `Model-Wind-WECC31.xlsx`, `-WECC32`, `-WECC4A`, `-WECC4B` | `examples/Model/Wind/WECC31`, `WECC32`, `WECC4A`, `WECC4B` | `S+Aux` |
| `Performance-Single-WECC4B.xlsx` | `examples/Performance/Single/WECC4B` | `S` |
| `Performance-SingleI-WECC4B.xlsx` | `examples/Performance/SingleI/WECC4B` | `S+i` |
| `Performance-SingleAux-WECC4B.xlsx` | `examples/Performance/SingleAux/WECC4B` | `S+Aux` |
| `Performance-SingleAuxI-WECC4B.xlsx` | `examples/Performance/SingleAuxI/WECC4B` | `S+Aux+i` |

`WECCSample_full.xlsx` is not one of these: it is the small AIA-authored fixture the unit tests
run on, rebuilt by `build_sample.py` (needs `openpyxl`).

## Regenerating an example

Run from the repository root — the signal sheets name each example's reference curves as a path
relative to it:

```bash
python tools/dynawo_inputs/generate_inputs.py \
  --excel tools/dynawo_inputs/examples/Model-Wind-WECC4B.xlsx \
  --outdir examples/Model/Wind/WECC4B
```

A `Model-*` workbook writes `Dynawo/Zone1` and `Dynawo/Zone3` plus `ReferenceCurves/Producer`; a
`Performance-*` one describes a single tree, and only its Zone 3 half is used. The performance
examples carry no reference curves, so those workbooks keep the template's placeholder in the
results-folder cell.

The `[Curves-Metadata]` section of each generated `.dict` is written with its keys empty on
purpose: their values describe the recorded `.csv` files, which only whoever produced them knows.

## Storage: two directions per case

A storage plant runs every DTR case twice, injecting and consuming, and records one `.csv` for
each. The tests table has one results-file cell per case, so `Model-BESS-WECC.xlsx` carries the
**base** name (`PCS_RTE-I16z1.SetPointStep.Active.csv`) and the generator appends the suffixes of
`[Storage]` in `excel_names.ini` to both the operating condition and the file name
(`…ActiveInjection.csv`, `…ActiveConsumption.csv`).

## Two known limits

- **Auxiliary transformer, last bit.** Regenerating a `+Aux` example reproduces its files except
  for the auxiliary transformer's `transformer_RPu`/`XPu`, which differ in the last bit
  (`1.0000000000000008e-05` vs `…004e-05`): the workbook holds the short-circuit impedance and the
  R/X ratio, and splitting them again is not bit-exact. It is float noise, not a modelling
  difference.
- **The frequency ramp is not in the sheet.** `Signaux zone 3` has no row for the frequency-ramp
  case, so no workbook can describe `PCS_RTE-I16z3.GridFreqRamp.W500mHz250ms`. It is the only test
  the BESS example carries that regenerating it does not reproduce; adding the row to the template
  is RTE's, and `[Zone3-Tests]` then names it.
