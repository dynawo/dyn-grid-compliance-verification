# Workbooks

The blank workbooks an installation is described in, one per standard the tool models:

- `Producer_IEC.xlsx` — IEC 61400-27-1 models
- `Producer_WECC.xlsx` — WECC models

Copy the one that matches your model, fill it in, and hand it to the tool, which reads
every input from it:

```console
dycov excel2inputs Producer_IEC.xlsx
dycov validate --excel Producer_IEC.xlsx
dycov performance --excel Producer_IEC.xlsx
```

The `format_version` cell of the `Infos générales ->` sheet names the DyCoV release the
workbook was written for.

The row labels of the `Signaux zone 1` and `Signaux zone 3` sheets are what the tool matches
to know which curve each row describes: a label it does not recognise is dropped, and the
curve it names is then missing from the reference dictionary. The names it accepts are
listed in `excel_names.ini`, next to your configuration file.
