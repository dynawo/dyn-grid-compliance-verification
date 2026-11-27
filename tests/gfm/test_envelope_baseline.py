#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The envelopes of generate_gfm_envelopes against those a stable release generated.

The command runs with the configuration directory and the Producer.ini of a real case, copied
under resources/baseline, and compares through its own -t option. It runs with -od because
that directory keeps PPM/ and BESS/ under templates/PCS/gfm, which the command takes for two
more PCS and aborts on.
"""

import shutil
import tarfile
from pathlib import Path

RESOURCES = Path(__file__).resolve().parent / "resources" / "baseline"


def _csv_files(directory: Path) -> list[Path]:
    return sorted(path.relative_to(directory) for path in directory.rglob("*.csv"))


def _without_grid_forming_templates(directory: str, names: list[str]) -> list[str]:
    """The release read none of the Grid Forming templates of the case, which the tool now
    takes for the user's descriptions of its own Grid Forming PCS."""
    return ["gfm"] if Path(directory).parent.name == "templates" else []


def _home_with_user_config(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    shutil.copytree(
        RESOURCES / "config", home / ".config" / "dycov", ignore=_without_grid_forming_templates
    )
    return home


def _baseline(tmp_path: Path) -> Path:
    baseline = tmp_path / "baseline"
    with tarfile.open(RESOURCES / "envelopes.tar.xz") as archive:
        archive.extractall(baseline, filter="data")
    return baseline


def test_the_envelopes_are_those_of_the_release(tmp_path, run_dycov):
    home = _home_with_user_config(tmp_path)
    baseline = _baseline(tmp_path)
    output = tmp_path / "Results"

    run = run_dycov(
        "generate_gfm_envelopes",
        "-od",
        "-i",
        str(RESOURCES / "Producer.ini"),
        "-o",
        str(output),
        "-t",
        str(baseline),
        home=home,
    )

    assert run.returncode == 0, run.stdout + run.stderr
    assert _csv_files(output) == _csv_files(baseline)
