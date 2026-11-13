#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""generate_gfm_envelopes reads the producer file -i names, whatever else its folder holds."""

import shutil
from pathlib import Path

RESOURCES = Path(__file__).resolve().parent / "resources" / "baseline"

USER_CONFIG = "[DTR]\ncurrent = 20260723\n"


def _producer_next_to_a_user_config(tmp_path: Path) -> Path:
    folder = tmp_path / "producer"
    folder.mkdir()
    shutil.copy(RESOURCES / "Producer.ini", folder / "Producer.ini")
    (folder / "user_config.ini").write_text(USER_CONFIG)
    return folder


def _generate(run_dycov, folder: Path, producer_ini: Path, output: Path):
    return run_dycov(
        "--user-config",
        str(folder / "user_config.ini"),
        "generate_gfm_envelopes",
        "-i",
        str(producer_ini),
        "-p",
        "PCS_RTE-IGFM1",
        "-o",
        str(output),
        home=folder.parent / "home",
    )


def test_another_ini_next_to_the_producer_file_is_no_producer(tmp_path, run_dycov):
    folder = _producer_next_to_a_user_config(tmp_path)
    output = tmp_path / "Results"

    run = _generate(run_dycov, folder, folder / "Producer.ini", output)

    assert run.returncode == 0, run.stdout + run.stderr
    assert [path.name for path in output.iterdir()] == ["PCS_RTE-IGFM1"]
    assert any(output.rglob("*.csv"))


def test_a_producer_file_that_does_not_exist_stops_the_run(tmp_path, run_dycov):
    folder = _producer_next_to_a_user_config(tmp_path)
    output = tmp_path / "Results"
    missing = folder / "Typo.ini"

    run = _generate(run_dycov, folder, missing, output)

    assert run.returncode != 0
    assert str(missing) in run.stdout + run.stderr
    assert not output.exists()
