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

This tool is superseded by ``tools/dynawo_inputs`` (which generates the full
DyCoV input trees from the same template) and will be retired with it. The
Excel parsing engine lives there (``tools/dynawo_inputs/workbook.py``); this
module keeps only the fragment emission and re-exports the parsing API it
always exposed.

Usage::

    python generate_par.py --excel input.xlsx [--outdir DIR]
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

# The parsing engine lives in the successor tool; import it by path (repo tool convention).
_DYNAWO_INPUTS = Path(__file__).resolve().parent.parent / "dynawo_inputs"
if str(_DYNAWO_INPUTS) not in sys.path:
    sys.path.insert(0, str(_DYNAWO_INPUTS))

from workbook import (  # noqa: E402,F401  (re-exported parsing API)
    Config,
    Grid,
    Parameter,
    Variant,
    _cell,
    _CONFIG_SHEET,
    _map_type,
    _merge_comment,
    _NO_BLOCK,
    _selected_variants,
    _strip_accents,
    parse_config,
    parse_variants,
    read_workbook,
)

# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------


def _render_variant(variant: Variant) -> list[str]:
    """Render a single variant block as PAR fragment lines (values only)."""
    lines = [
        f"  <!-- {variant.sheet} -->",
        f"  <!-- {variant.table} | {variant.name} -->",
    ]
    for param in variant.parameters:
        if param.value is None:
            continue
        comment = _merge_comment(param)
        if comment:
            lines.append(f"  <!-- {comment} -->")
        lines.append(
            f'  <par type="{_map_type(param.type)}" '
            f'name="{param.name}" value="{param.value}"/>'
        )
    return lines


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
