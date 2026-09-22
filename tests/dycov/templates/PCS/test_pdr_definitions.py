#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from __future__ import annotations

import configparser
import math
from dataclasses import dataclass
from pathlib import Path

import pytest

from dycov.files.model_parameters import extract_defined_value


@dataclass(frozen=True)
class PdrEntry:
    ini_path: Path
    section: str
    key: str
    value: str


def find_repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "src" / "dycov").exists():
            return parent
    raise RuntimeError("Repository root not found (expected 'src/dycov' to exist).")


def iter_pcsdescription_ini_files(repo_root: Path) -> list[Path]:
    patterns = [
        "src/dycov/templates/PCS/model/**/PCS_RTE-I*/PCSDescription.ini",
        "src/dycov/templates/PCS/performance/**/PCS_RTE-I*/PCSDescription.ini",
    ]
    files: list[Path] = []
    for pat in patterns:
        files.extend(repo_root.glob(pat))
    return sorted(set(files))


def read_pdr_entries(ini_path: Path) -> list[PdrEntry]:
    cfg = configparser.ConfigParser(interpolation=None, strict=False)
    cfg.read(ini_path, encoding="utf-8")

    target = {"pdr_p", "pdr_q", "pdr_u"}
    entries: list[PdrEntry] = []

    for section in cfg.sections():
        for k, v in cfg.items(section):
            kl = k.lower().strip()
            if kl in target:
                entries.append(
                    PdrEntry(
                        ini_path=ini_path,
                        section=section,
                        key=kl,
                        value=(v or "").strip(),
                    )
                )
    return entries


def choose_parameter(entry: PdrEntry) -> str:
    s = entry.value.lower()

    if entry.key == "pdr_p":
        return "PMax"

    if entry.key == "pdr_q":
        if "qmax" in s:
            return "Qmax"
        if "qmin" in s:
            return "Qmin"
        if "pmax" in s:
            return "PMax"
        return "Qmax"

    if entry.key == "pdr_u":
        if "udim" in s:
            return "Udim"
        if "unom" in s:
            return "Unom"
        return "Udim"

    raise AssertionError(f"Unexpected key: {entry.key}")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return find_repo_root()


@pytest.fixture(scope="session")
def pdr_entries(repo_root: Path) -> list[PdrEntry]:
    entries: list[PdrEntry] = []
    for ini_file in iter_pcsdescription_ini_files(repo_root):
        entries.extend(read_pdr_entries(ini_file))
    assert entries, "No pdr_P / pdr_Q / pdr_U entries found."
    return entries


def entry_id(e: PdrEntry) -> str:
    return f"{e.ini_path.as_posix()}::{e.section}::{e.key}={e.value}"


@pytest.mark.parametrize("sign", [1, -1], ids=["sign+1", "sign-1"])
def test_pdr_definitions_match_expected_reference_parameter(
    pdr_entries: list[PdrEntry], sign: int
):
    base_value = 1.0
    errors: list[str] = []

    for e in pdr_entries:
        if not e.value:
            errors.append(f"Empty definition: {entry_id(e)}")
            continue

        parameter = choose_parameter(e)

        try:
            out = extract_defined_value(
                e.value, parameter=parameter, base_value=base_value, sign=sign
            )
        except ValueError as exc:
            errors.append(f"Rejected: {entry_id(e)} (parameter={parameter}, error={exc})")
            continue

        if not (isinstance(out, float) and math.isfinite(out)):
            errors.append(f"Non-finite result: {entry_id(e)} -> {out!r} (parameter={parameter})")

    assert not errors, "Invalid pdr_* definitions:\n" + "\n".join(errors)
