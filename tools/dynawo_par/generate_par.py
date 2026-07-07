#!/usr/bin/env python3
# Copyright (c) 2024-2026, RTE (https://www.rte-france.com)
# SPDX-License-Identifier: MPL-2.0
"""Generate Dynawo PAR fragments from an Excel model specification.

This is a standalone preprocessing utility (see
``docs/design/Dynawo_par_generation_from_excel_design.md``). It reads a single
Excel workbook, which is the single source of truth, and emits two PAR
fragments ready to paste into Dynawo models:

* ``zone1.par`` - every selected block **except** REPC
* ``zone3.par`` - every selected block

The tool deliberately does NOT validate, interpret, or compute model
parameters. The only contextual transformations it performs are:

* mapping the Excel ``Type`` to the Dynawo convention (``double`` -> ``DOUBLE``);
* the ``SnZone3 = SnZone3 x Nombre de convertisseur`` header value of Zone 3.

It has no third-party dependencies: ``.xlsx`` files are plain ZIP archives of
XML, so they are parsed with the standard library only.

Usage::

    python generate_par.py --excel input.xlsx [--outdir DIR]
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# OpenXML spreadsheet namespaces.
_MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

# Name of the configuration sheet (accent-insensitive match is applied).
_CONFIG_SHEET = "general"

# Choices in the configuration sheet that mean "no block selected".
_NO_BLOCK = {"", "aucun", "none", "n/a", "na", "-"}

# Excel type -> Dynawo PAR type. Anything unknown is simply upper-cased.
_TYPE_MAP = {
    "double": "DOUBLE",
    "float": "DOUBLE",
    "real": "DOUBLE",
    "boolean": "BOOL",
    "bool": "BOOL",
    "integer": "INT",
    "int": "INT",
    "string": "STRING",
    "str": "STRING",
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Parameter:
    """A single parameter row of a variant table."""

    name: str
    type: str
    value: str | None = None
    comment: str | None = None
    base_unit: str | None = None


@dataclass
class Variant:
    """One variant (column group) of a table, e.g. ``REEC_A``."""

    name: str
    sheet: str
    table: str
    parameters: list[Parameter] = field(default_factory=list)


@dataclass
class Config:
    """Parsed contents of the ``Général`` configuration sheet."""

    # Ordered list of (block type, chosen variant), e.g. ("REEC", "REEC_A").
    selections: list[tuple[str, str]] = field(default_factory=list)
    sn_zone1: str | None = None
    sn_zone3: str | None = None
    n_converters: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_accents(text: str) -> str:
    """Return *text* lower-cased and stripped of diacritics, for matching."""
    norm = unicodedata.normalize("NFKD", text)
    return "".join(c for c in norm if not unicodedata.combining(c)).strip().lower()


def _col_letters_to_index(ref: str) -> int:
    """Convert a cell/column reference (e.g. ``"AB12"``) to a 0-based column."""
    match = re.match(r"([A-Za-z]+)", ref)
    letters = match.group(1).upper()
    col = 0
    for ch in letters:
        col = col * 26 + (ord(ch) - ord("A") + 1)
    return col - 1


# ---------------------------------------------------------------------------
# XLSX reading (standard library only)
# ---------------------------------------------------------------------------

# A sheet grid: list of rows, each row a list of cell values (str or None).
Grid = list[list["str | None"]]


def read_workbook(path: Path) -> dict[str, Grid]:
    """Read every worksheet of *path* into an ordered ``{name: grid}`` mapping.

    Cell values are returned as strings (or ``None`` when empty). No type
    conversion is applied beyond rendering booleans as ``true``/``false``.
    """
    with zipfile.ZipFile(path) as archive:
        shared = _read_shared_strings(archive)
        sheets = _read_sheet_index(archive)
        return {
            name: _read_sheet_grid(archive, target, shared)
            for name, target in sheets
        }


def _read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    """Return the shared-strings table (an empty list when absent)."""
    name = "xl/sharedStrings.xml"
    if name not in archive.namelist():
        return []
    root = ET.fromstring(archive.read(name))
    strings: list[str] = []
    for si in root.findall(f"{_MAIN_NS}si"):
        strings.append("".join(t.text or "" for t in si.iter(f"{_MAIN_NS}t")))
    return strings


def _read_sheet_index(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    """Return ordered ``(sheet_name, worksheet_path)`` pairs."""
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))

    rid_to_target: dict[str, str] = {}
    for rel in rels:
        target = rel.get("Target", "")
        # Targets are either absolute ("/xl/worksheets/sheet1.xml", written by
        # openpyxl) or relative to the workbook part ("worksheets/sheet1.xml").
        target = target.lstrip("/") if target.startswith("/") else "xl/" + target
        rid_to_target[rel.get("Id")] = target

    sheets: list[tuple[str, str]] = []
    for sheet in workbook.iter(f"{_MAIN_NS}sheet"):
        rid = sheet.get(f"{_REL_NS}id")
        target = rid_to_target.get(rid)
        if target:
            sheets.append((sheet.get("name", ""), target))
    return sheets


def _read_sheet_grid(
    archive: zipfile.ZipFile, target: str, shared: list[str]
) -> Grid:
    """Parse a single worksheet XML into a dense grid of string values."""
    root = ET.fromstring(archive.read(target))
    cells: dict[tuple[int, int], str] = {}
    max_row = max_col = -1

    for cell in root.iter(f"{_MAIN_NS}c"):
        ref = cell.get("r")
        if not ref:
            continue
        row = int(re.search(r"\d+", ref).group()) - 1
        col = _col_letters_to_index(ref)
        value = _cell_value(cell, shared)
        if value is None or value == "":
            continue
        cells[(row, col)] = value
        max_row = max(max_row, row)
        max_col = max(max_col, col)

    grid: Grid = [[None] * (max_col + 1) for _ in range(max_row + 1)]
    for (row, col), value in cells.items():
        grid[row][col] = value
    return grid


def _cell_value(cell: ET.Element, shared: list[str]) -> str | None:
    """Return the textual value of a worksheet cell."""
    ctype = cell.get("t")
    if ctype == "s":  # shared string
        node = cell.find(f"{_MAIN_NS}v")
        return shared[int(node.text)] if node is not None else None
    if ctype == "inlineStr":  # inline string
        node = cell.find(f"{_MAIN_NS}is")
        return "".join(t.text or "" for t in node.iter(f"{_MAIN_NS}t")) if node is not None else None
    if ctype == "b":  # boolean -> Dynawo wants true/false
        node = cell.find(f"{_MAIN_NS}v")
        return "true" if (node is not None and node.text == "1") else "false"
    # number, date, or formula result: keep the literal text as-is.
    node = cell.find(f"{_MAIN_NS}v")
    return node.text if node is not None else None


def _cell(grid: Grid, row: int, col: int) -> str | None:
    """Safe accessor that returns ``None`` when the cell is out of range."""
    if 0 <= row < len(grid) and 0 <= col < len(grid[row]):
        value = grid[row][col]
        return value.strip() if isinstance(value, str) else value
    return None


# ---------------------------------------------------------------------------
# Parameter table parsing
# ---------------------------------------------------------------------------


def parse_variants(workbook: dict[str, Grid]) -> dict[str, Variant]:
    """Parse every structured parameter sheet into variants keyed by name.

    Descriptive sheets (no ``Parameter | Type | Value`` header) and the
    configuration sheet yield nothing and are therefore ignored automatically.
    """
    variants: dict[str, Variant] = {}
    for sheet_name, grid in workbook.items():
        if _strip_accents(sheet_name).startswith(_CONFIG_SHEET):
            continue
        for variant in _parse_sheet(sheet_name, grid):
            if variant.name in variants:
                raise ValueError(
                    f"Duplicate variant '{variant.name}' found in sheets "
                    f"'{variants[variant.name].sheet}' and '{sheet_name}'."
                )
            variants[variant.name] = variant
    return variants


def _parse_sheet(sheet_name: str, grid: Grid) -> list[Variant]:
    """Parse the (single) parameter table block of one sheet into variants."""
    header_row = _find_header_row(grid)
    if header_row is None:
        return []  # not a structured parameter sheet

    column_groups = _find_column_groups(grid, header_row)
    base_columns = _find_extra_columns(grid, header_row, "base")
    comment_columns = _find_extra_columns(grid, header_row, "comment")
    table_labels = _find_table_labels(grid, header_row - 2)

    variants: list[Variant] = []
    for param_col in sorted(column_groups):
        variant_name = _cell(grid, header_row - 1, param_col)
        if not variant_name:
            continue
        table = _label_for_column(table_labels, param_col) or sheet_name
        base_col = _extra_for_column(base_columns, table_labels, param_col)
        comment_col = _extra_for_column(comment_columns, table_labels, param_col)
        variant = Variant(name=variant_name, sheet=sheet_name, table=table)
        variant.parameters = _parse_parameters(
            grid, header_row, param_col, base_col, comment_col
        )
        variants.append(variant)
    return variants


def _find_header_row(grid: Grid) -> int | None:
    """Return the first row index that contains a ``Parameter`` header cell."""
    for row_idx, row in enumerate(grid):
        for value in row:
            if isinstance(value, str) and value.strip().lower() == "parameter":
                return row_idx
    return None


def _find_column_groups(grid: Grid, header_row: int) -> list[int]:
    """Return the column index of every ``Parameter`` cell in the header row."""
    return [
        col
        for col, value in enumerate(grid[header_row])
        if isinstance(value, str) and value.strip().lower() == "parameter"
    ]


def _find_extra_columns(grid: Grid, header_row: int, prefix: str) -> list[int]:
    """Return header columns whose label starts with *prefix* (case-insensitive).

    Used for the optional ``Base unit`` / ``Base`` and ``Comment`` columns.
    """
    return [
        col
        for col, value in enumerate(grid[header_row])
        if isinstance(value, str) and value.strip().lower().startswith(prefix)
    ]


def _find_table_labels(grid: Grid, label_row: int) -> list[tuple[int, str]]:
    """Return sorted ``(column, label)`` table names from the label row."""
    if label_row < 0 or label_row >= len(grid):
        return []
    return sorted(
        (col, value.strip())
        for col, value in enumerate(grid[label_row])
        if isinstance(value, str) and value.strip()
    )


def _label_for_column(labels: list[tuple[int, str]], col: int) -> str | None:
    """Return the table label governing *col* (nearest label at or left of it)."""
    chosen: str | None = None
    for label_col, label in labels:
        if label_col <= col:
            chosen = label
        else:
            break
    return chosen


def _extra_for_column(
    extra_columns: list[int], labels: list[tuple[int, str]], param_col: int
) -> int | None:
    """Return the extra column (base unit / comment) of *param_col*'s block."""
    # The block spans from this column's table label to the next one.
    block_start = 0
    block_end = float("inf")
    for label_col, _ in labels:
        if label_col <= param_col:
            block_start = label_col
        elif label_col < block_end:
            block_end = label_col
    for extra_col in extra_columns:
        if block_start <= extra_col < block_end:
            return extra_col
    return None


def _parse_parameters(
    grid: Grid,
    header_row: int,
    param_col: int,
    base_col: int | None,
    comment_col: int | None,
) -> list[Parameter]:
    """Parse the data rows of a single variant column group.

    A row is valid for this variant when both ``Parameter`` and ``Type`` are
    non-empty. Empty rows (for this variant) are skipped without ending the
    table, so sparse parallel variants are handled correctly.
    """
    parameters: list[Parameter] = []
    for row in range(header_row + 1, len(grid)):
        name = _cell(grid, row, param_col)
        ptype = _cell(grid, row, param_col + 1)
        if not name or not ptype:
            continue
        value = _cell(grid, row, param_col + 2)
        base_unit = _cell(grid, row, base_col) if base_col is not None else None
        comment = _cell(grid, row, comment_col) if comment_col is not None else None
        parameters.append(
            Parameter(
                name=name,
                type=ptype,
                value=value if value else None,
                comment=comment if comment else None,
                base_unit=base_unit if base_unit else None,
            )
        )
    return parameters


# ---------------------------------------------------------------------------
# Configuration sheet parsing
# ---------------------------------------------------------------------------


def parse_config(workbook: dict[str, Grid]) -> Config:
    """Parse the ``Général`` sheet for block selections and global parameters."""
    for sheet_name, grid in workbook.items():
        if _strip_accents(sheet_name).startswith(_CONFIG_SHEET):
            config = Config()
            config.selections = _parse_block_selection(grid)
            _parse_globals(grid, config)
            return config
    raise ValueError("Configuration sheet 'Général' not found in the workbook.")


def _parse_block_selection(grid: Grid) -> list[tuple[str, str]]:
    """Read the ``Type de bloc | Choix`` table into ordered (block, choice)."""
    for row_idx, row in enumerate(grid):
        normalized = [_strip_accents(c) for c in row if isinstance(c, str)]
        if "type de bloc" in normalized and "choix" in normalized:
            block_col = next(
                c for c, v in enumerate(row)
                if isinstance(v, str) and _strip_accents(v) == "type de bloc"
            )
            choice_col = next(
                c for c, v in enumerate(row)
                if isinstance(v, str) and _strip_accents(v) == "choix"
            )
            selections: list[tuple[str, str]] = []
            for r in range(row_idx + 1, len(grid)):
                block = _cell(grid, r, block_col)
                if not block:
                    break
                choice = _cell(grid, r, choice_col) or ""
                selections.append((block, choice))
            return selections
    raise ValueError(
        "Block-selection table ('Type de bloc' | 'Choix') not found in 'Général'."
    )


def _parse_globals(grid: Grid, config: Config) -> None:
    """Read SnZone1, SnZone3 and the converter count from the globals table."""
    for row_idx, row in enumerate(grid):
        normalized = [_strip_accents(c) for c in row if isinstance(c, str)]
        if "grandeur" in normalized and "valeur" in normalized:
            name_col = next(
                c for c, v in enumerate(row)
                if isinstance(v, str) and _strip_accents(v) == "grandeur"
            )
            value_col = next(
                c for c, v in enumerate(row)
                if isinstance(v, str) and _strip_accents(v) == "valeur"
            )
            for r in range(row_idx + 1, len(grid)):
                name = _cell(grid, r, name_col)
                if not name:
                    break
                value = _cell(grid, r, value_col)
                key = _strip_accents(name)
                if key == "snzone1":
                    config.sn_zone1 = value
                elif key == "snzone3":
                    config.sn_zone3 = value
                elif "convertisseur" in key or "converter" in key:
                    config.n_converters = value
            return
    # The globals table is optional; absence simply leaves the fields as None.


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------


def _map_type(excel_type: str) -> str:
    """Map an Excel type to the Dynawo PAR convention (unknown -> upper-case)."""
    return _TYPE_MAP.get(excel_type.strip().lower(), excel_type.strip().upper())


def _merge_comment(param: Parameter) -> str | None:
    """Merge the optional comment and base unit into a single comment string."""
    parts = []
    if param.comment:
        parts.append(param.comment)
    if param.base_unit:
        parts.append(f"Base unit: {param.base_unit}")
    return " | ".join(parts) if parts else None


def _render_variant(variant: Variant) -> list[str]:
    """Render a single variant block as PAR fragment lines (values only)."""
    lines = [
        f"  <!-- {variant.sheet} -->",
        f"  <!-- {variant.table} | {variant.name} -->",
    ]
    for param in variant.parameters:
        if param.value is None:
            continue  # only parameters that carry a value are exported
        comment = _merge_comment(param)
        if comment:
            lines.append(f"  <!-- {comment} -->")
        lines.append(
            f'  <par type="{_map_type(param.type)}" '
            f'name="{param.name}" value="{param.value}"/>'
        )
    return lines


def _selected_variants(
    config: Config, variants: dict[str, Variant]
) -> list[tuple[str, Variant]]:
    """Return the enabled ``(block, variant)`` pairs in *workbook* order.

    The ``Général`` sheet only decides *which* variant each block uses; the
    output order follows the sheets and tables of the Excel file (the insertion
    order of *variants*), as required by the order-preservation principle.
    Disabled blocks (``Aucun`` / empty) are skipped; a selected variant that is
    absent from every parameter sheet raises an explicit error.
    """
    block_of: dict[str, str] = {}
    for block, choice in config.selections:
        if _strip_accents(choice) in _NO_BLOCK:
            continue
        if choice not in variants:
            raise ValueError(
                f"Selected variant '{choice}' (block '{block}') is not present "
                f"in any parameter sheet. Available variants: "
                f"{', '.join(sorted(variants)) or '(none)'}."
            )
        block_of[choice] = block
    return [
        (block_of[name], variant)
        for name, variant in variants.items()
        if name in block_of
    ]


def _zone3_header_value(config: Config) -> str:
    """Compute the contextual ``SnZone3 x Nombre de convertisseur`` value."""
    sn3, nconv = config.sn_zone3, config.n_converters
    if not sn3 or not nconv:
        missing = []
        if not sn3:
            missing.append("SnZone3")
        if not nconv:
            missing.append("Nombre de convertisseur")
        return f"(not computed: {', '.join(missing)} missing in Excel)"
    try:
        product = float(sn3) * float(nconv)
        # Render integers without a trailing ".0".
        return str(int(product)) if product.is_integer() else str(product)
    except ValueError:
        return f"{sn3} x {nconv}"


def build_zone1(config: Config, variants: dict[str, Variant]) -> str:
    """Build the Zone 1 fragment: every selected block except REPC."""
    lines = [f"  <!-- SnZone1 = {config.sn_zone1 or '(not provided)'} -->", ""]
    for block, variant in _selected_variants(config, variants):
        if _strip_accents(block) == "repc":
            continue
        lines.extend(_render_variant(variant))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_zone3(config: Config, variants: dict[str, Variant]) -> str:
    """Build the Zone 3 fragment: every selected block."""
    lines = [f"  <!-- SnZone3 = {_zone3_header_value(config)} -->", ""]
    for _, variant in _selected_variants(config, variants):
        lines.extend(_render_variant(variant))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def generate(excel: Path, outdir: Path) -> tuple[Path, Path]:
    """Read *excel*, write ``zone1.par`` and ``zone3.par`` into *outdir*."""
    workbook = read_workbook(excel)
    variants = parse_variants(workbook)
    config = parse_config(workbook)

    zone1_text = build_zone1(config, variants)
    zone3_text = build_zone3(config, variants)

    outdir.mkdir(parents=True, exist_ok=True)
    zone1_path = outdir / "zone1.par"
    zone3_path = outdir / "zone3.par"
    zone1_path.write_text(zone1_text, encoding="utf-8")
    zone3_path.write_text(zone3_text, encoding="utf-8")
    return zone1_path, zone3_path


def _print_summary(config: Config, variants: dict[str, Variant]) -> None:
    """Print a short console summary of what was generated."""
    print("Selected blocks:")
    for block, choice in config.selections:
        if _strip_accents(choice) in _NO_BLOCK:
            print(f"  - {block:<8} -> (none)")
            continue
        nparams = len(variants[choice].parameters)
        nvalued = sum(1 for p in variants[choice].parameters if p.value is not None)
        print(f"  - {block:<8} -> {choice} ({nvalued}/{nparams} values set)")
    print(f"\nSnZone1 = {config.sn_zone1 or '(not provided)'}")
    print(f"SnZone3 = {_zone3_header_value(config)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate Dynawo PAR fragments (Zone 1 and Zone 3) from an "
        "Excel model specification."
    )
    parser.add_argument(
        "--excel", required=True, type=Path, help="Path to the input .xlsx file."
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=None,
        help="Directory for zone1.par / zone3.par (default: next to the Excel).",
    )
    args = parser.parse_args(argv)

    if not args.excel.is_file():
        parser.error(f"Excel file not found: {args.excel}")
    outdir = args.outdir or args.excel.resolve().parent

    try:
        zone1_path, zone3_path = generate(args.excel, outdir)
    except (ValueError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    workbook = read_workbook(args.excel)
    _print_summary(parse_config(workbook), parse_variants(workbook))
    print(f"\nWrote: {zone1_path}\nWrote: {zone3_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
