import re
import shutil
import subprocess

import pytest

from dycov.report.tables import characteristics_response, compliance

pytestmark = pytest.mark.skipif(shutil.which("pdflatex") is None, reason="needs pdflatex")

DOCUMENT = r"""\documentclass{article}
\usepackage{hyperref}
\makeatletter
\let\markless@makefnmark\@makefnmark
\def\@makefnmark{\typeout{MARK:\@thefnmark}\markless@makefnmark}
\makeatother
\begin{document}
A note of the document.\footnote{Document note.}

\typeout{TABLE BEGINS}
\begin{minipage}{\linewidth}
\begin{tabular}{ll}
%s
\end{tabular}
\end{minipage}
\typeout{TABLE ENDS}
\end{document}
"""


def _marks_in_table(tmp_path, rows: list) -> list:
    body = "\n".join(f"{row[0]} & {row[1]} \\\\" for row in rows)
    (tmp_path / "table.tex").write_text(DOCUMENT % body)
    run = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "table.tex"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stdout[-2000:]
    log = (tmp_path / "table.log").read_text(errors="replace")
    table_log = log[log.index("TABLE BEGINS") : log.index("TABLE ENDS")]
    return re.findall(r"MARK:(.*)", table_log)


def test_every_not_calculated_time_carries_the_mark_of_its_note(tmp_path):
    results = {}
    for variable in ("reaction_time", "rise_time", "settling_time"):
        results |= {
            f"calc_{variable}": 0.5,
            f"ref_{variable}": 0.0,
            f"{variable}_error": "-",
            f"{variable}_thr": 0.1,
            f"{variable}_check": True,
        }
    rows = [[row[0], row[3]] for row in characteristics_response.create_map(results)]

    marks = _marks_in_table(tmp_path, rows)

    assert len(marks) == 4
    assert len(set(marks)) == 1
    assert "1" not in marks[0]


def test_every_non_compliant_time_carries_the_mark_of_its_note(tmp_path):
    results = {
        "freq1": 1.5,
        "freq1_check": False,
        "AVR_5": 2.5,
        "AVR_5_check": False,
        "imax_reac": 3.5,
        "imax_reac_check": False,
    }
    rows = [[row[0], row[1]] for row in compliance.create_map(results)]

    marks = _marks_in_table(tmp_path, rows)

    assert len(marks) == 4
    assert len(set(marks)) == 1
    assert "1" not in marks[0]
