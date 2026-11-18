#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""generate_gfm_envelopes keeps the envelopes of every PCS when one of them generates none."""

import shutil
from pathlib import Path

import dycov

RESOURCES = Path(__file__).resolve().parent / "resources" / "baseline"

USER_CONFIG = "[DTR]\ncurrent = 20260723\n"

GFM_PCS = ["PCS_RTE-IGFM1", "PCS_RTE-IGFM2", "PCS_RTE-IGFM3", "PCS_RTE-IGFM4"]

SHIPPED_IGFM1 = Path(dycov.__file__).resolve().parent / "templates/PCS/gfm/PCS_RTE-IGFM1"


def _producer(tmp_path: Path) -> Path:
    folder = tmp_path / "producer"
    folder.mkdir()
    shutil.copy(RESOURCES / "Producer.ini", folder / "Producer.ini")
    (folder / "user_config.ini").write_text(USER_CONFIG)
    return folder


def _generate(run_dycov, folder: Path, output: Path, home: Path, *pcs: str):
    return run_dycov(
        "--user-config",
        str(folder / "user_config.ini"),
        "generate_gfm_envelopes",
        "-i",
        str(folder / "Producer.ini"),
        *pcs,
        "-o",
        str(output),
        home=home,
    )


def test_a_pcs_that_is_not_a_gfm_one_ends_the_run_without_an_error(tmp_path, run_dycov):
    folder = _producer(tmp_path)
    output = tmp_path / "Results"

    run = _generate(run_dycov, folder, output, tmp_path / "home", "-p", "PCS_RTE-I8")

    log = run.stdout + run.stderr
    assert run.returncode == 0, log
    assert "PCS_RTE-I8 is not a valid PCS" in log
    assert "Error during generation" not in log
    assert list(output.iterdir()) == []


def test_a_stray_directory_among_the_user_pcs_leaves_the_others_envelopes(tmp_path, run_dycov):
    folder = _producer(tmp_path)
    output = tmp_path / "Results"
    home = tmp_path / "home"
    (home / ".config" / "dycov" / "templates" / "PCS" / "gfm" / "MyStray").mkdir(parents=True)

    run = _generate(run_dycov, folder, output, home)

    log = run.stdout + run.stderr
    assert run.returncode == 0, log
    assert "MyStray is not a valid PCS" in log
    assert "Error during generation" not in log
    assert sorted(path.name for path in output.iterdir()) == GFM_PCS
    for pcs in GFM_PCS:
        assert any((output / pcs).rglob("*.csv")), pcs


def _user_gfm_pcs(home: Path, name: str, description: str) -> None:
    folder = home / ".config" / "dycov" / "templates" / "PCS" / "gfm" / name
    folder.mkdir(parents=True)
    (folder / "PCSDescription.ini").write_text(description)


def _generate_igfm1_and(run_dycov, tmp_path: Path, home: Path, user_pcs: str):
    folder = _producer(tmp_path)
    (folder / "user_config.ini").write_text(
        f"{USER_CONFIG}\n[Global]\ngridforming_pcs = PCS_RTE-IGFM1,{user_pcs}\n"
    )
    output = tmp_path / "Results"
    return _generate(run_dycov, folder, output, home), output


def test_a_pcs_whose_description_cannot_be_read_leaves_the_others_envelopes(tmp_path, run_dycov):
    home = tmp_path / "home"
    _user_gfm_pcs(home, "PCS_User-Malformed", "[PCS_User-Malformed]\na line with no value\n")

    run, output = _generate_igfm1_and(run_dycov, tmp_path, home, "PCS_User-Malformed")

    log = run.stdout + run.stderr
    assert run.returncode == 0, log
    assert "Aborted execution for PCS_User-Malformed" in log
    assert "Error during generation" not in log
    assert [path.name for path in output.iterdir()] == ["PCS_RTE-IGFM1"]


def test_a_pcs_aborted_before_its_first_envelope_is_reported_and_left_out(tmp_path, run_dycov):
    home = tmp_path / "home"
    description = (SHIPPED_IGFM1 / "PCSDescription.ini").read_text()
    description = description.replace("PCS_RTE-IGFM1", "PCS_User-Aborted")
    description = description.replace("DeltaPhase = 0.3*", "DeltaPhase = bad*")
    _user_gfm_pcs(home, "PCS_User-Aborted", description)

    run, output = _generate_igfm1_and(run_dycov, tmp_path, home, "PCS_User-Aborted")

    log = run.stdout + run.stderr
    assert run.returncode == 0, log
    assert "Aborted execution for PCS_User-Aborted" in log
    assert "PCS_User-Aborted generated no envelopes" in log
    assert [path.name for path in output.iterdir()] == ["PCS_RTE-IGFM1"]
