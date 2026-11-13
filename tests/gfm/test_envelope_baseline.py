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


def _home_with_user_config(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    shutil.copytree(RESOURCES / "config", home / ".config" / "dycov")
    return home


def _baseline(tmp_path: Path) -> Path:
    baseline = tmp_path / "baseline"
    with tarfile.open(RESOURCES / "envelopes.tar.xz") as archive:
        archive.extractall(baseline, filter="data")
    return baseline


def test_the_envelopes_are_those_of_the_release(tmp_path, run_dycov):
    home = _home_with_user_config(tmp_path)
    baseline = _baseline(tmp_path)
    expected_files = _csv_files(baseline)
    # The phase jumps follow the transfer function of the converter since the release, so their
    # envelopes are no longer those it generated
    shutil.rmtree(baseline / "PCS_RTE-IGFM1")
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
    assert _csv_files(output) == expected_files
