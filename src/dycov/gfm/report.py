#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Report of the Grid Forming tests.

Every test gets a page with its parameters and its envelopes. 'dycov generate_gfm_envelopes'
writes a PDF of the envelopes alone, while a performance verification adds to its report a
section for the Grid Forming PCS of each producer, whose pages also show the checks of the DTR
Fiche I18 of the producer curves and their verdict. Both are built on the main template and the
LaTeX machinery of the verification reports.
"""

import logging
import time
from collections import namedtuple
from pathlib import Path
from typing import Optional

from dycov._build_info import commit_id, version
from dycov.configuration.cfg import config
from dycov.core.global_variables import REPORT_NAME
from dycov.files import manage_files
from dycov.gfm.parameters import GFMParameters
from dycov.logging import dycov_logging
from dycov.report import printable, report
from dycov.report.LatexReportException import LatexReportException
from dycov.report.tables import summary

# What the report shows of a test; the names of its first fields are those of the summary table
GFMTestReport = namedtuple(
    "GFMTestReport",
    [
        "producer_name",
        "pcs",
        "benchmark",
        "operating_condition",
        "magnitude",
        "parameters",
        "compliance",
        "envelope",
        "modes",
    ],
)
PcsReport = namedtuple("PcsReport", ["producer_name", "pcs", "report_name", "tests"])

# The page of a test, shared by every Grid Forming PCS
_TEST_TEMPLATE = "report.GFMTest.tex"
_MODEL_TYPES = {"gfm/BESS": "Battery Energy Storage Systems", "gfm/PPM": "Power Park Modules"}
# The parameters are those printed on the figures, whose symbols LaTeX does not set in text mode
_LATEX_TEXT = str.maketrans(
    {
        "_": r"\_",
        "%": r"\%",
        "Δ": r"\ensuremath{\Delta}",
        "θ": r"\ensuremath{\theta}",
        "°": r"\ensuremath{^\circ}",
    }
)


def create_pdf(pcs_reports: list[PcsReport], parameters: GFMParameters) -> None:
    """Creates the report of the envelopes generated, in the Reports directory of the output.

    Parameters
    ----------
    pcs_reports: list[PcsReport]
        The tests of every PCS generated, in the order the report shows them
    parameters: GFMParameters
        The parameters of the run

    Raises
    ------
    LatexReportException
        If pdflatex does not produce the report.
    """
    logger = dycov_logging.get_logger("GFMReport")
    latex_path = parameters.get_working_dir() / "Latex"
    manage_files.create_dir(latex_path)
    path_latex_files = Path(config.get_value("Global", "latex_templates_path"))
    tool_latex_path = Path(__file__).resolve().parent.parent / path_latex_files
    manage_files.copy_file(tool_latex_path / REPORT_NAME, latex_path)

    sim_type_str = parameters.get_producer().get_sim_type_str()
    reports = []
    tests = []
    for pcs_report in pcs_reports:
        pcs_input = prepare_pcs_report(
            pcs_report, latex_path, sim_type_str, outputs_by_producer=False
        )
        if pcs_input:
            reports.append(pcs_input)
            tests += pcs_report.tests

    if not tests:
        logger.warning("No test was generated, so there is no report to create")
        return

    report.get_template(latex_path, REPORT_NAME).stream(
        {
            "gridforming": True,
            "summary_description": _summary_description(parameters).replace("_", r"\_"),
            "summaryReport": _summary_rows(tests),
            "reports": reports,
            "verificationtype": "Grid Forming Verification",
            "modeltype": _MODEL_TYPES.get(sim_type_str, ""),
        }
    ).dump(str(latex_path / REPORT_NAME))

    proc = report.compile_pdf(latex_path)
    if logger.getEffectiveLevel() != logging.DEBUG:
        report.clean_latex_outputs(latex_path)

    reports_path = parameters.get_output_dir() / "Reports"
    manage_files.create_dir(reports_path, clean_first=False)
    report_moved = manage_files.move_report(latex_path, reports_path, REPORT_NAME)
    if proc.returncode != 0 or not report_moved:
        logger.debug(proc.stderr.decode("utf-8", errors="replace"))
        raise LatexReportException("pdflatex did not produce the final report.")
    logger.info(f"PDF report done in {reports_path}")


def prepare_pcs_report(
    pcs_report: PcsReport, latex_path: Path, sim_type_str: str, outputs_by_producer: bool
) -> Optional[str]:
    """Writes the section of a PCS, and the page of each of its tests, where the report is
    compiled.

    Parameters
    ----------
    pcs_report: PcsReport
        The tests of the PCS the section shows
    latex_path: Path
        Directory where the report is compiled, inside the working directory of the run
    sim_type_str: str
        Directory of the templates of the kind of unit, e.g. 'gfm/BESS'
    outputs_by_producer: bool
        Whether the output of the run keeps a directory by producer, as a verification does

    Returns
    -------
    Optional[str]
        The input of the section in the main report, None when it shows no test
    """
    if not pcs_report.tests:
        return None
    if not pcs_report.report_name:
        dycov_logging.get_logger("GFMReport").warning(
            f"{pcs_report.pcs} declares no report_name, it is left out of the PDF"
        )
        return None

    path_latex_files = Path(config.get_value("Global", "latex_templates_path"))
    _copy_test_template(path_latex_files, latex_path)
    report.copy_pcs_latex_files(
        path_latex_files, sim_type_str, pcs_report.pcs, pcs_report.producer_name, latex_path
    )
    return _write_pcs_report(pcs_report, latex_path, outputs_by_producer)


def _copy_test_template(path_latex_files: Path, latex_path: Path) -> None:
    """Copies the page of a test, the user's one winning over the tool's."""
    tool_path = Path(__file__).resolve().parent.parent / path_latex_files
    for templates_path in (tool_path, config.get_config_dir() / path_latex_files):
        test_template = templates_path / "gfm" / _TEST_TEMPLATE
        if test_template.exists():
            manage_files.copy_file(test_template, latex_path)


def _write_pcs_report(pcs_report: PcsReport, latex_path: Path, outputs_by_producer: bool) -> str:
    """Renders the page of every test of the PCS and its section, and returns the input of the
    section in the main report."""
    prefix = pcs_report.producer_name.replace("_", "")
    test_template = report.get_template(latex_path, _TEST_TEMPLATE)
    subreports = []
    for test in pcs_report.tests:
        test_report = f"{prefix}.report.{_test_name(test)}.tex"
        test_template.stream(_test_map(test, outputs_by_producer)).dump(
            str(latex_path / test_report)
        )
        subreports.append(f"\\input{{{test_report.replace('.tex', '')}}}")

    pcs_template = f"{prefix}.{pcs_report.report_name}"
    report.get_template(latex_path, pcs_template).stream(
        {
            "producercommand": f"\\renewcommand{{\\Producer}}{{{pcs_report.producer_name}}}",
            "producer": pcs_report.producer_name.replace("_", r"\_"),
            "subReports": subreports,
        }
    ).dump(str(latex_path / pcs_template))
    return f"\\input{{{pcs_template.replace('.tex', '')}}}"


def _test_name(test: GFMTestReport) -> str:
    return f"{test.pcs}.{test.benchmark}.{test.operating_condition}"


def _test_map(test: GFMTestReport, outputs_by_producer: bool) -> dict:
    """The values the page of a test shows."""
    test_path = Path(test.pcs) / test.benchmark / test.operating_condition
    html_figure = test_path / f"{_test_name(test)}.html"
    if outputs_by_producer:
        html_figure = Path(test.producer_name) / html_figure
    return {
        # Escaped rather than detokenized, as the table of contents reads it back
        "testname": f"{test.benchmark}.{test.operating_condition}".replace("_", r"\_"),
        "parameters": [_parameter_row(parameter) for parameter in test.parameters],
        # Read in place from the working directory, which the Latex directory sits in
        "figure": (
            Path("..") / test.producer_name / test_path / f"{_test_name(test)}.png"
        ).as_posix(),
        # From the Reports directory of the output
        "link": f"\\href{{run:../{html_figure.as_posix()}}}{{html figures}}",
        "checked": test.compliance is not None,
        "envelope": _envelope_row(test),
        "modes": _mode_rows(test),
        "cutoff": config.get_float("GFM", "cutoff", 30.0),
        "tolerance": config.get_float("GFM", "envelope_tolerance", 0.005),
        "threshold": config.get_float("GFM", "thr_damping_ratio", 0.40),
        "minamplitude": config.get_float("GFM", "damping_min_amplitude", 0.001),
        "fmin": config.get_float("GFM", "damping_f_min", 0.1),
        "fmax": config.get_float("GFM", "damping_f_max", 10.0),
        "compliance": summary.translate_compliance(test.compliance) if test.compliance else "",
    }


def _parameter_row(parameter: str) -> list[str]:
    """A parameter as printed on the figure, 'name = value unit', split into its two columns."""
    name, _, value = parameter.partition(" = ")
    return [name.translate(_LATEX_TEXT), value.translate(_LATEX_TEXT)]


def _envelope_row(test: GFMTestReport) -> list | None:
    envelope = test.envelope
    if envelope is None:
        return None
    if envelope.t_from is None:
        return [test.magnitude, "--", "--", "--", printable.format_latex_check(False)]
    return [
        test.magnitude,
        f"{envelope.t_from:.3f}",
        f"{envelope.t_to:.3f}",
        f"{envelope.max_excess:.4f}",
        printable.format_latex_check(envelope.within),
    ]


def _mode_rows(test: GFMTestReport) -> list[list[str]]:
    thr_damping_ratio = config.get_float("GFM", "thr_damping_ratio", 0.40)
    return [
        [
            mode.curve,
            mode.window,
            f"{mode.frequency:.3f}",
            f"{mode.damping_ratio:.3f}",
            f"{mode.amplitude:.3f}",
            printable.format_latex_check(mode.damping_ratio >= thr_damping_ratio),
        ]
        for mode in test.modes
    ]


def _summary_description(parameters: GFMParameters) -> str:
    timestamp = time.strftime("%Y-%m-%d %H:%M %Z", time.localtime())
    description = f"Run on: {timestamp} \\\\"
    description += f"Dycov version: {version} commit: {commit_id} \\\\"
    description += f"Producer dir: {parameters.get_producer().get_producer_path()} \\\\"
    envelopes = "EMT" if parameters.is_emt() else "RMS"
    return description + f"Envelopes for {envelopes} simulations \\\\"


def _summary_rows(tests: list[GFMTestReport]) -> list[list[str]]:
    # The run delivers envelopes, and gives no verdict
    return [
        [
            text.replace("_", r"\_")
            for text in (test.producer_name, test.pcs, test.benchmark, test.operating_condition)
        ]
        + ["Envelopes generated"]
        for test in tests
    ]
