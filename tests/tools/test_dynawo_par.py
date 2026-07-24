# Copyright (c) 2024-2026, RTE (https://www.rte-france.com)
# SPDX-License-Identifier: MPL-2.0
"""Tests for the Dynawo PAR generation tool (``tools/dynawo_par``).

A minimal but valid ``.xlsx`` is built in memory (inline strings only) so the
core pipeline - reading, parsing and output - is exercised without any
third-party dependency. ``test_real_example_import`` additionally imports the
committed ``examples/WECCSample.xlsx`` to validate the real Excel reading path.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

# The tool lives under tools/ (outside the dycov package); import it by path.
_TOOL_DIR = Path(__file__).resolve().parents[2] / "tools" / "dynawo_par"
sys.path.insert(0, str(_TOOL_DIR))

import generate_par as gp  # noqa: E402

# ---------------------------------------------------------------------------
# Minimal .xlsx builder (inline strings, no shared-strings table)
# ---------------------------------------------------------------------------


def _col_letter(idx: int) -> str:
    letters = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters


def _sheet_xml(rows: list[list[str | None]]) -> str:
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        "<sheetData>",
    ]
    for r, row in enumerate(rows, start=1):
        out.append(f'<row r="{r}">')
        for c, value in enumerate(row):
            if value is None or value == "":
                continue
            ref = f"{_col_letter(c)}{r}"
            out.append(
                f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'
            )
        out.append("</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)


def make_xlsx(path: Path, sheets: dict[str, list[list[str | None]]]) -> None:
    names = list(sheets)
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for i in range(1, len(names) + 1)
        )
        + "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument'
        '/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
        + "".join(
            f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>'
            for i, name in enumerate(names, start=1)
        )
        + "</sheets></workbook>"
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="rId{i}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{i}.xml"/>'
            for i in range(1, len(names) + 1)
        )
        + "</Relationships>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        for i, name in enumerate(names, start=1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", _sheet_xml(sheets[name]))


# ---------------------------------------------------------------------------
# Fixtures: a small workbook with values, two sparse variants, base units
# ---------------------------------------------------------------------------


def _sample_sheets() -> dict[str, list[list[str | None]]]:
    general = [
        ["Type de bloc", "Choix"],
        ["REPC", "REPC_A"],
        ["REEC", "REEC_C"],
        ["WTGP", "Aucun"],
        [],
        ["Grandeur", "Description", "Valeur", "Unite"],
        ["SnZone1", "converter base", "100", "MVA"],
        ["Nombre de convertisseur", "", "4", ""],
        ["SnZone3", "park base", "25", "MVA"],
    ]
    repc = [
        ["Plant Controller", None, None, None, None],
        ["REPC_A", None, None, None, None],
        ["Parameter", "Type", "Value", "Base unit", "Comment"],
        ["VCompFlag", "boolean", "true", None, "reactive droop flag"],
        ["Kp", "double", "1.5", None, None],
        ["QMaxPu", "double", "0.4", "SnZone3", "reactive power limit"],
        ["Empty", "double", None, None, "no value here"],  # no value -> skipped
    ]
    # Two sparse variants: REEC_A and REEC_C sharing a Base unit column (col 6).
    reec = [
        ["Electrical Controller", None, None, None, None, None, None],
        ["REEC_A", None, None, "REEC_C", None, None, None],
        ["Parameter", "Type", "Value", "Parameter", "Type", "Value", "Base unit"],
        ["VDipPu", "double", "0.9", "VDipPu", "double", "0.85", "Un"],
        ["PFlag", "boolean", "true", None, "boolean", None, None],   # A only
        [None, "double", None, "tBattery", "double", "0.01", None],  # C only
    ]
    return {"Général": general, "REPC": repc, "REEC": reec}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_full_pipeline(tmp_path: Path) -> None:
    xlsx = tmp_path / "model.xlsx"
    make_xlsx(xlsx, _sample_sheets())

    workbook = gp.read_workbook(xlsx)
    variants = gp.parse_variants(workbook)
    config = gp.parse_config(workbook)

    # --- configuration -----------------------------------------------------
    assert config.selections == [("REPC", "REPC_A"), ("REEC", "REEC_C"), ("WTGP", "Aucun")]
    assert config.sn_zone1 == "100"
    assert config.n_converters == "4"
    assert config.sn_zone3 == "25"

    # --- variants & sparse parsing -----------------------------------------
    assert set(variants) == {"REPC_A", "REEC_A", "REEC_C"}
    reec_a = [p.name for p in variants["REEC_A"].parameters]
    reec_c = [p.name for p in variants["REEC_C"].parameters]
    assert reec_a == ["VDipPu", "PFlag"]          # C-only row skipped
    assert reec_c == ["VDipPu", "tBattery"]       # A-only row skipped
    assert variants["REEC_A"].table == "Electrical Controller"

    # base unit shared down the column for both variants
    vdip_a = variants["REEC_A"].parameters[0]
    vdip_c = variants["REEC_C"].parameters[0]
    assert vdip_a.base_unit == "Un" and vdip_c.base_unit == "Un"

    # --- Zone 1: excludes REPC, computes nothing for SnZone1 header --------
    zone1 = gp.build_zone1(config, variants)
    assert "SnZone1 = 100" in zone1
    assert "REPC_A" not in zone1            # REPC excluded from Zone 1
    assert "REEC_C" in zone1

    # --- Zone 3: includes REPC, SnZone3 = 25 * 4 = 100 ---------------------
    zone3 = gp.build_zone3(config, variants)
    assert "SnZone3 = 100" in zone3
    assert "REPC_A" in zone3

    # --- type mapping, value filtering, comment / base-unit merge ----------
    assert '<par type="BOOL" name="VCompFlag" value="true"/>' in zone3
    assert '<par type="DOUBLE" name="Kp" value="1.5"/>' in zone3
    assert "<!-- reactive droop flag -->" in zone3          # comment only
    assert "<!-- reactive power limit | Base unit: SnZone3 -->" in zone3  # merged
    assert "QMaxPu" in zone3
    assert "Empty" not in zone3             # parameter without value is dropped

    # --- end-to-end file writing ------------------------------------------
    z1, z3 = gp.generate(xlsx, tmp_path / "out")
    assert z1.read_text(encoding="utf-8") == zone1
    assert z3.read_text(encoding="utf-8") == zone3


def test_missing_variant_raises(tmp_path: Path) -> None:
    sheets = _sample_sheets()
    sheets["Général"][1] = ["REPC", "REPC_Z"]  # variant that does not exist
    xlsx = tmp_path / "bad.xlsx"
    make_xlsx(xlsx, sheets)
    workbook = gp.read_workbook(xlsx)
    variants = gp.parse_variants(workbook)
    config = gp.parse_config(workbook)
    try:
        gp.build_zone3(config, variants)
    except ValueError as exc:
        assert "REPC_Z" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected a ValueError for the missing variant")


# ---------------------------------------------------------------------------
# Real-file test: exercises the .xlsx reader against the committed example.
# ---------------------------------------------------------------------------

SAMPLE_XLSX = _TOOL_DIR / "examples" / "WECCSample.xlsx"


def test_real_example_import(tmp_path: Path) -> None:
    """Import the committed WECCSample.xlsx (a real Excel-saved file).

    Unlike the synthetic fixtures (inline strings), this file uses the shared
    strings table and the layout produced by Excel, so it validates the actual
    Excel import path end to end.
    """
    assert SAMPLE_XLSX.is_file(), f"missing example file: {SAMPLE_XLSX}"

    workbook = gp.read_workbook(SAMPLE_XLSX)
    variants = gp.parse_variants(workbook)
    config = gp.parse_config(workbook)

    # Configuration: full wind-turbine case.
    assert config.selections == [
        ("REPC", "REPC_A"), ("REEC", "REEC_A"), ("REGC", "REGC_A"),
        ("WTGT", "WTGT_B"), ("WTGP", "WTGP_A"), ("WTGA", "WTGA_A"), ("WTGQ", "WTGQ_A"),
    ]
    assert config.sn_zone1 == "4"
    assert config.n_converters == "20"
    assert config.sn_zone3 == "4.5"

    # Every selected variant was parsed with its full parameter set.
    valued = {name: sum(p.value is not None for p in v.parameters)
              for name, v in variants.items()}
    assert valued["REPC_A"] == 27
    assert valued["REEC_A"] == 50
    assert valued["REGC_A"] == 9
    assert valued["WTGT_B"] == 5
    assert valued["WTGP_A"] == 10
    assert valued["WTGA_A"] == 2
    assert valued["WTGQ_A"] == 15

    zone1 = gp.build_zone1(config, variants)
    zone3 = gp.build_zone3(config, variants)

    # Zone 1 excludes REPC (27 params) -> 91; Zone 3 includes it -> 118.
    assert zone1.count("<par ") == 91
    assert zone3.count("<par ") == 118
    assert "REPC_A" not in zone1 and "REPC_A" in zone3

    # Headers, contextual SnZone3 = 4.5 x 20 = 90, type mapping, real values.
    assert zone1.startswith("  <!-- SnZone1 = 4 -->")
    assert "  <!-- SnZone3 = 90 -->" in zone3
    assert '<par type="BOOL" name="TFlag" value="true"/>' in zone3
    assert '<par type="DOUBLE" name="Kp" value="0.1"/>' in zone3

    # The unselected battery variant (REEC_C) never reaches the output.
    assert "tBattery" not in zone1 and "tBattery" not in zone3

    # Sparse variant with gaps: REEC_C shares the parallel columns with REEC_A
    # but skips several rows (PFlag, VRef1Pu, IqFrzPu, tHoldIq, tHoldIpMax) and
    # resumes ~40 rows below with the battery block. Parsing must skip the gaps
    # without ending the table, and preserve order.
    names_a = [p.name for p in variants["REEC_A"].parameters]
    names_c = [p.name for p in variants["REEC_C"].parameters]
    assert [n for n in names_a if n not in names_c] == [
        "PFlag", "VRef1Pu", "IqFrzPu", "tHoldIq", "tHoldIpMax",
    ]
    assert names_c[-4:] == ["tBattery", "SOC0Pu", "SOCMaxPu", "SOCMinPu"]
    # Order is preserved across the gaps (no reordering, no early stop).
    assert names_c == sorted(names_c, key=lambda n: names_a.index(n)
                             if n in names_a else len(names_a))


def test_output_follows_workbook_order(tmp_path: Path) -> None:
    """Output order follows the sheets/tables, NOT the 'Général' selection order.

    'Général' only decides which variant each block uses; the emission order
    must come from the workbook. Here the selection table is deliberately the
    reverse of the sheet order, so the two orders disagree.
    """
    sheets = {
        "Général": [
            ["Type de bloc", "Choix"],
            ["B2", "V2"],   # selection order is reversed vs. the sheet order
            ["B1", "V1"],
            [],
            ["Grandeur", "Description", "Valeur", "Unite"],
            ["SnZone1", "", "5", "MVA"],
        ],
        "Sheet1": [["Tbl1"], ["V1"], ["Parameter", "Type", "Value"], ["P1", "double", "11"]],
        "Sheet2": [["Tbl2"], ["V2"], ["Parameter", "Type", "Value"], ["P2", "double", "22"]],
    }
    xlsx = tmp_path / "order.xlsx"
    make_xlsx(xlsx, sheets)
    workbook = gp.read_workbook(xlsx)
    variants = gp.parse_variants(workbook)
    config = gp.parse_config(workbook)

    for text in (gp.build_zone1(config, variants), gp.build_zone3(config, variants)):
        # Sheet1/V1 (P1) must precede Sheet2/V2 (P2), despite Général listing V2 first.
        assert text.index('name="P1"') < text.index('name="P2"')


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        test_full_pipeline(Path(d))
    with tempfile.TemporaryDirectory() as d:
        test_missing_variant_raises(Path(d))
    with tempfile.TemporaryDirectory() as d:
        test_real_example_import(Path(d))
    with tempfile.TemporaryDirectory() as d:
        test_output_follows_workbook_order(Path(d))
    print("All tests passed.")
