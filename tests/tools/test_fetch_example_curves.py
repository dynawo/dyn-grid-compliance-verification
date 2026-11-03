#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the script that brings the curves of the examples to a clone
(``tools/scripts/fetch_example_curves.sh``).

The script is run as it is, from a clone of its own whose ``curl`` serves a local asset instead
of the one a release publishes, so nothing leaves the machine.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import zipfile
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "scripts" / "fetch_example_curves.sh"
_CURVES = Path("examples") / "Model" / "Wind" / "Unit" / "ReferenceCurves"

pytestmark = pytest.mark.skipif(shutil.which("unzip") is None, reason="the script needs unzip")

_CURL_SERVING_THE_ASSET = """#!/bin/bash
while (($#)); do
    if [ "$1" = "-o" ]; then cp "$FAKE_ASSET" "$2"; exit 0; fi
    shift
done
exit 22
"""


def _asset(path: Path, curves: dict[str, str]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in curves.items():
            archive.writestr(str(_CURVES / name), content)
    return path


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    root = tmp_path / "clone"
    (root / "examples" / "Model").mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl = bin_dir / "curl"
    curl.write_text(_CURL_SERVING_THE_ASSET)
    curl.chmod(curl.stat().st_mode | stat.S_IXUSR)
    return root


def _fetch(clone: Path, asset: Path, release: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PATH"] = f"{clone.parent / 'bin'}{os.pathsep}{env['PATH']}"
    env["FAKE_ASSET"] = str(asset)
    return subprocess.run(
        ["bash", str(_SCRIPT), "--release", release],
        cwd=clone,
        env=env,
        capture_output=True,
        text=True,
    )


def test_a_clone_without_curves_gets_those_of_the_release(clone, tmp_path):
    asset = _asset(tmp_path / "first.zip", {"Test.csv": "time;V\n0;1\n"})

    run = _fetch(clone, asset, "v1.0.0")

    assert run.returncode == 0, run.stderr
    assert (clone / _CURVES / "Test.csv").read_text() == "time;V\n0;1\n"
    assert (clone / "examples" / ".curves-release").read_text() == "v1.0.0\n"


def test_fetching_again_replaces_the_curves_and_the_release_they_come_from(clone, tmp_path):
    _fetch(clone, _asset(tmp_path / "first.zip", {"Old.csv": "time;V\n0;1\n"}), "v1.0.0")

    run = _fetch(clone, _asset(tmp_path / "second.zip", {"New.csv": "time;V\n0;2\n"}), "v1.1.0")

    assert run.returncode == 0, run.stderr
    assert not (clone / _CURVES / "Old.csv").exists()
    assert (clone / _CURVES / "New.csv").read_text() == "time;V\n0;2\n"
    assert (clone / "examples" / ".curves-release").read_text() == "v1.1.0\n"


def test_fetching_over_regenerated_curves_records_the_release(clone, tmp_path):
    (clone / _CURVES).mkdir(parents=True)
    (clone / _CURVES / "Regenerated.csv").write_text("time;V\n0;3\n")
    (clone / "examples" / ".curves-release").write_text("the working tree at 0123abc\n")

    run = _fetch(clone, _asset(tmp_path / "asset.zip", {"Test.csv": "time;V\n0;1\n"}), "v1.0.0")

    assert run.returncode == 0, run.stderr
    assert not (clone / _CURVES / "Regenerated.csv").exists()
    assert (clone / "examples" / ".curves-release").read_text() == "v1.0.0\n"


def test_an_asset_without_curves_leaves_the_curves_of_the_clone_and_their_release(clone, tmp_path):
    _fetch(clone, _asset(tmp_path / "first.zip", {"Old.csv": "time;V\n0;1\n"}), "v1.0.0")
    empty = tmp_path / "empty.zip"
    with zipfile.ZipFile(empty, "w") as archive:
        archive.writestr("examples/Model/README.txt", "no curves\n")

    run = _fetch(clone, empty, "v1.1.0")

    assert run.returncode != 0
    assert "The asset of release v1.1.0 holds no curve." in run.stderr + run.stdout
    assert (clone / _CURVES / "Old.csv").read_text() == "time;V\n0;1\n"
    assert (clone / "examples" / ".curves-release").read_text() == "v1.0.0\n"
