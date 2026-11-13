#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""generate_gfm_envelopes refuses a producer whose D, H or Xeff cannot give envelopes."""

import re
from pathlib import Path

import pytest

RESOURCES = Path(__file__).resolve().parent / "resources" / "baseline"

USER_CONFIG = "[DTR]\ncurrent = 20260723\n"


def _producer(tmp_path: Path, values: dict[str, str], hybrid: bool = True) -> Path:
    text = (RESOURCES / "Producer.ini").read_text()
    if not hybrid:
        text = re.sub(r"(?m)^[DH]_(Over|Under)damped *=.*\n", "", text)
        text = text.replace("[GFM Parameters]\n", "[GFM Parameters]\nD = 152\nH = 2\n")
    for option, value in values.items():
        text, replaced = re.subn(rf"(?m)^{option} *=.*$", f"{option} = {value}", text)
        if not replaced:
            text = text.replace("[GFM Parameters]\n", f"[GFM Parameters]\n{option} = {value}\n")
    folder = tmp_path / "producer"
    folder.mkdir()
    (folder / "Producer.ini").write_text(text)
    (folder / "user_config.ini").write_text(USER_CONFIG)
    return folder


def _generate(run_dycov, folder: Path, output: Path):
    return run_dycov(
        "--user-config",
        str(folder / "user_config.ini"),
        "generate_gfm_envelopes",
        "-i",
        str(folder / "Producer.ini"),
        "-p",
        "PCS_RTE-IGFM3",
        "-o",
        str(output),
        home=folder.parent / "home",
    )


@pytest.mark.parametrize(
    "values, hybrid, named",
    [
        pytest.param({"H": "0"}, False, ["H = 0 must be a finite number above zero"], id="H zero"),
        pytest.param(
            {"H": "-2"}, False, ["H = -2 must be a finite number above zero"], id="H negative"
        ),
        pytest.param(
            {"D": "-1"}, False, ["D = -1 must be a finite number not below zero"], id="D negative"
        ),
        pytest.param(
            {"D": "nan"}, False, ["D = nan must be a finite number not below zero"], id="D nan"
        ),
        pytest.param(
            {"Xeff": "0"}, True, ["Xeff = 0 must be a finite number above zero"], id="Xeff zero"
        ),
        pytest.param(
            {"Xeff": "abc"},
            True,
            ["Xeff = abc must be a finite number above zero"],
            id="Xeff text",
        ),
        pytest.param(
            {"H_Underdamped": ""},
            True,
            ["H_Underdamped = (empty) must be a finite number above zero"],
            id="hybrid H empty",
        ),
        pytest.param(
            {"H_Overdamped": "inf", "D_Underdamped": "-5"},
            True,
            ["H_Overdamped = inf must be", "D_Underdamped = -5 must be"],
            id="hybrid several",
        ),
    ],
)
def test_a_producer_value_the_envelopes_cannot_use_stops_the_run(
    tmp_path, run_dycov, values, hybrid, named
):
    folder = _producer(tmp_path, values, hybrid)
    output = tmp_path / "Results"

    run = _generate(run_dycov, folder, output)

    assert run.returncode != 0
    for text in named:
        assert text in run.stdout + run.stderr
    assert str(folder / "Producer.ini") in run.stdout + run.stderr
    assert not output.exists() or not any(output.rglob("*.csv"))


def test_a_producer_without_damping_gives_envelopes(tmp_path, run_dycov):
    folder = _producer(tmp_path, {"D": "0"}, hybrid=False)
    output = tmp_path / "Results"

    run = _generate(run_dycov, folder, output)

    assert run.returncode == 0, run.stdout + run.stderr
    envelopes = list(output.rglob("*.csv"))
    assert envelopes
    assert not any("nan" in path.read_text().lower() for path in envelopes)
