#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The page of a Zone 1 test that has no curve, compiled with the macros of its commonz1.tex: a
fault whose dip is out of reach, say, leaves the page without figures (#831)."""

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("pdflatex") is None or shutil.which("pdftotext") is None,
    reason="needs pdflatex and pdftotext",
)

REPORTS = Path(__file__).resolve().parents[4] / "src" / "dycov" / "templates" / "reports"

DOCUMENT = r"""\documentclass{article}
\usepackage{xcolor}
\usepackage{graphicx}
\newcommand{\Producer}{Producer}
\newcommand{\PCSname}{PCS_RTE-I16z1}
\newcommand{\DTRPcs}{ThreePhaseFault}
\newcommand{\OCname}{PermanentHiZ}
\input{commonz1.tex}
\begin{document}
\GridSimulationHeaderZone{
    \GridCurvesDescriptionZone
}
\GridCurvesZone
\end{document}
"""


FIGURE = r"""\documentclass{article}
\begin{document}
figure
\end{document}
"""


def _compile(directory: Path, source: str, name: str) -> subprocess.CompletedProcess:
    (directory / f"{name}.tex").write_text(source)
    return subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"{name}.tex"],
        cwd=directory,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("family", ["PPM", "BESS"])
@pytest.mark.parametrize("with_figure", [False, True])
def test_the_page_says_it_has_no_figure_only_when_it_has_none(family, with_figure, tmp_path):
    """#831: the page of a test without curves stopped pdflatex, and the report lost its PDF."""
    shutil.copy(REPORTS / "model" / family / "PCS_RTE-I16z1" / "commonz1.tex", tmp_path)
    if with_figure:
        _compile(tmp_path, FIGURE, "figure")
        shutil.copy(
            tmp_path / "figure.pdf",
            tmp_path / "Producer_fig_V_PCS_RTE-I16z1.ThreePhaseFault.PermanentHiZ.pdf",
        )

    run = _compile(tmp_path, DOCUMENT, "page")

    assert run.returncode == 0, run.stdout[-2000:]
    text = subprocess.run(
        ["pdftotext", "page.pdf", "-"], cwd=tmp_path, capture_output=True, text=True
    ).stdout
    assert ("No figure: the test produced no curve." in text) is not with_figure
    assert ("Voltage at InternalNode1." in text) is with_figure
