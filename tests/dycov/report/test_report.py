#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import logging
from pathlib import Path

import pandas as pd
import pytest

from dycov.core.global_variables import ELECTRIC_PERFORMANCE_BESS, REPORT_NAME
from dycov.model.benchmark import Summary
from dycov.model.compliance import Compliance
from dycov.report import report
from dycov.report.curve_classification import is_setpoint
from dycov.report.types import FigureDescription


@pytest.fixture
def oc_results():
    return {
        "curves": pd.DataFrame(
            {"time": [0.0, 1.0, 2.0], "BusPDR_BUS_ActivePower": [0.0, 0.5, 1.0]}
        )
    }


@pytest.fixture
def figures_description():
    return {
        "PCS.Benchmark": [
            FigureDescription(
                name="fig_P",
                variables=[{"type": "bus", "variable": "ActivePower"}],
                ylabel="P [pu]",
            )
        ]
    }


def test_generate_figures_passes_zone_to_html(
    monkeypatch, tmp_path, oc_results, figures_description
):
    seen_zones = []
    monkeypatch.setattr(report.figure, "create_plot", lambda *a, **k: None)
    monkeypatch.setattr(
        report.html,
        "plotly_figures",
        lambda *a, **k: seen_zones.append(k.get("zone")) or ([], "", ""),
    )

    report._generate_figures(
        tmp_path,
        "Producer",
        figures_description,
        "PCS.Benchmark",
        oc_results,
        "PCS.Benchmark.OC",
        0.0,
        2.0,
        zone=1,
    )

    assert seen_zones == [1]


def test_generate_figures_default_zone(monkeypatch, tmp_path, oc_results, figures_description):
    seen_zones = []
    monkeypatch.setattr(report.figure, "create_plot", lambda *a, **k: None)
    monkeypatch.setattr(
        report.html,
        "plotly_figures",
        lambda *a, **k: seen_zones.append(k.get("zone")) or ([], "", ""),
    )

    report._generate_figures(
        tmp_path,
        "Producer",
        figures_description,
        "PCS.Benchmark",
        oc_results,
        "PCS.Benchmark.OC",
        0.0,
        2.0,
    )

    assert seen_zones == [0]


def test_generate_figures_passes_zone_to_the_pdf(
    monkeypatch, tmp_path, oc_results, figures_description
):
    seen_zones = []
    monkeypatch.setattr(
        report.figure, "create_plot", lambda *a, **k: seen_zones.append(k.get("zone"))
    )
    monkeypatch.setattr(report.html, "plotly_figures", lambda *a, **k: ([], "", ""))

    report._generate_figures(
        tmp_path,
        "Producer",
        figures_description,
        "PCS.Benchmark",
        oc_results,
        "PCS.Benchmark.OC",
        0.0,
        2.0,
        zone=1,
    )

    assert seen_zones == [1]


@pytest.mark.parametrize("in_pdf, expected_pdf_figures", [(True, ["fig_P"]), (False, [])])
def test_generate_figures_sends_every_figure_to_the_html_and_to_the_pdf_only_if_asked(
    monkeypatch, tmp_path, oc_results, in_pdf, expected_pdf_figures
):
    """#553: the power at InternalNode1 is always drawn in the HTML, and in the PDF only when
    it does not repeat the controlled power."""
    pdf_figures, html_figures = [], []
    monkeypatch.setattr(
        report.figure,
        "create_plot",
        lambda time, description, *a, **k: pdf_figures.append(description.name),
    )
    monkeypatch.setattr(
        report.html,
        "plotly_figures",
        lambda description, *a, **k: html_figures.append(description.name) or ([], "", ""),
    )
    figures_description = {
        "PCS.Benchmark": [
            FigureDescription(
                name="fig_P", variables="BusPDR_BUS_ActivePower", ylabel="P", in_pdf=in_pdf
            )
        ]
    }

    report._generate_figures(
        tmp_path,
        "Producer",
        figures_description,
        "PCS.Benchmark",
        oc_results,
        "PCS.Benchmark.OC",
        0.0,
        2.0,
        zone=1,
    )

    assert pdf_figures == expected_pdf_figures
    assert html_figures == ["fig_P"]


_OC = "PCS.Benchmark.OC"


def _zone1_figures() -> list:
    """The figures of a Zone 1 test whose converter controls InternalNode2, each naming the
    setpoint that drives what it draws."""
    return [
        FigureDescription(
            name="fig_V", variables=[{"type": "bus", "variable": "Voltage"}], ylabel="V"
        ),
        FigureDescription(
            name="fig_UIt",
            variables=[{"type": "generator", "variable": "VoltageNode2"}],
            ylabel="V",
            setpoint="VoltageSetpointPu",
        ),
        FigureDescription(
            name="fig_P",
            variables=[{"type": "generator", "variable": "ActivePowerControlledNode"}],
            ylabel="P",
            setpoint="ActivePowerSetpointPu",
        ),
        FigureDescription(
            name="fig_Q",
            variables=[{"type": "generator", "variable": "ReactivePowerControlledNode"}],
            ylabel="Q",
            setpoint="ReactivePowerSetpointPu",
        ),
    ]


def _setpoints_by_figure(figures: list) -> dict:
    """The setpoints each figure draws, for the figures that draw any."""
    setpoints = {
        fd.name: [v["variable"] for v in fd.variables if is_setpoint(v["variable"])]
        for fd in figures
    }
    return {name: names for name, names in setpoints.items() if names}


@pytest.mark.parametrize(
    "test_type, expected",
    [
        ("PSetpoint", {"fig_P": ["ActivePowerSetpointPu"]}),
        ("QSetpoint", {"fig_Q": ["ReactivePowerSetpointPu"]}),
        ("USetpoint", {"fig_UIt": ["VoltageSetpointPu"]}),
        ("Others", {}),
    ],
)
def test_a_setpoint_step_draws_its_setpoint_over_the_magnitude_it_drives_and_nowhere_else(
    set_user_option, test_type, expected
):
    """#554: SetPointStep.Active, .Reactive and .Voltage of Zone 1, and a test that steps no
    setpoint of the unit, such as a grid voltage step."""
    set_user_option(_OC, "setpoint_change_test_type", test_type)

    drawn = [report._with_stepped_setpoint(fd, _OC, 1) for fd in _zone1_figures()]

    assert _setpoints_by_figure(drawn) == expected


def test_a_test_without_a_type_draws_no_setpoint():
    drawn = [report._with_stepped_setpoint(fd, _OC, 1) for fd in _zone1_figures()]

    assert _setpoints_by_figure(drawn) == {}


def test_a_setpoint_step_of_zone_3_draws_no_setpoint(set_user_option):
    set_user_option(_OC, "setpoint_change_test_type", "PSetpoint")
    fig_p = FigureDescription(name="fig_P", variables="BusPDR_BUS_ActivePower", ylabel="P")

    assert report._with_stepped_setpoint(fig_p, _OC, 3) == fig_p


def _step_results(magnitude: str, setpoint: str, reference_carries_setpoint: bool) -> dict:
    curves = pd.DataFrame(
        {"time": [0.0, 1.0, 2.0], magnitude: [0.85, 0.82, 0.80], setpoint: [0.85, 0.80, 0.80]}
    )
    reference = curves if reference_carries_setpoint else curves.drop(columns=setpoint)
    return {"curves": curves, "reference_curves": reference}


def test_generate_figures_draws_the_setpoint_of_the_step_in_the_pdf_and_in_the_html(
    monkeypatch, set_user_option, tmp_path
):
    set_user_option(_OC, "setpoint_change_test_type", "PSetpoint")
    pdf_variables, html_variables = [], []
    monkeypatch.setattr(
        report.figure,
        "create_plot",
        lambda time, description, *a, **k: pdf_variables.append(description.variables),
    )
    monkeypatch.setattr(
        report.html,
        "plotly_figures",
        lambda description, *a, **k: html_variables.append(description.variables) or ([], "", ""),
    )

    report._generate_figures(
        tmp_path,
        "Producer",
        {"PCS.Benchmark": [_zone1_figures()[2]]},
        "PCS.Benchmark",
        _step_results("WT_GEN_ActivePowerControlledNode", "WT_GEN_ActivePowerSetpointPu", True),
        _OC,
        0.0,
        2.0,
        zone=1,
    )

    expected = [
        {"type": "generator", "variable": "ActivePowerControlledNode"},
        {"type": "generator", "variable": "ActivePowerSetpointPu"},
    ]
    assert pdf_variables == [expected]
    assert html_variables == [expected]


@pytest.mark.parametrize("reference_carries_setpoint", [True, False])
@pytest.mark.parametrize(
    "test_type, figure_description, magnitude, setpoint",
    [
        (
            "PSetpoint",
            _zone1_figures()[2],
            "WT_GEN_ActivePowerControlledNode",
            "WT_GEN_ActivePowerSetpointPu",
        ),
        (
            "USetpoint",
            _zone1_figures()[1],
            "WT_GEN_VoltageNode2",
            "WT_GEN_VoltageSetpointPu",
        ),
        (
            "USetpoint",
            FigureDescription(
                name="fig_V",
                variables=[{"type": "bus", "variable": "Voltage"}],
                ylabel="V",
                setpoint="VoltageSetpointPu",
            ),
            "BusPDR_BUS_Voltage",
            "WT_GEN_VoltageSetpointPu",
        ),
    ],
    ids=["active power", "voltage at InternalNode2", "voltage at InternalNode1"],
)
def test_generate_figures_draws_a_setpoint_step_whether_the_reference_carries_it_or_not(
    set_user_option,
    tmp_path,
    test_type,
    figure_description,
    magnitude,
    setpoint,
    reference_carries_setpoint,
):
    set_user_option(_OC, "setpoint_change_test_type", test_type)

    plotted_curves, figures = report._generate_figures(
        tmp_path,
        "Producer",
        {"PCS.Benchmark": [figure_description]},
        "PCS.Benchmark",
        _step_results(magnitude, setpoint, reference_carries_setpoint),
        _OC,
        0.0,
        2.0,
        zone=1,
    )

    assert (tmp_path / f"Producer_{figure_description.name}_{_OC}.pdf").exists()
    assert plotted_curves == [magnitude, setpoint]
    assert [div_id for div_id, _ in figures] == [figure_description.name]


def test_build_oc_notices_without_missing_or_warnings():
    notices, watermark = report._build_oc_notices({"missed_columns": []})

    assert notices == ""
    assert watermark == "\\SetWatermarkText{}"


def test_build_oc_notices_with_missed_columns():
    notices, watermark = report._build_oc_notices(
        {"missed_columns": ["Wind_Turbine_GEN_ActiveCurrentNode2"]}
    )

    assert "\\noindent\\textcolor{red}{Missing curves:}" in notices
    assert "\\item \\textcolor{red}{Wind\\_Turbine\\_GEN\\_ActiveCurrentNode2}" in notices
    assert watermark == "\\SetWatermarkText{INVALID}"


def test_build_oc_notices_without_reference_curves():
    notices, watermark = report._build_oc_notices(
        {"missed_columns": [], "incomplete_curves": True}
    )

    assert "\\noindent\\textcolor{red}{Missing curves:}" in notices
    assert "no reference curves" in notices
    assert watermark == "\\SetWatermarkText{INVALID}"


def test_build_oc_notices_without_reference_curves_and_with_missed_columns():
    notices, watermark = report._build_oc_notices(
        {"missed_columns": ["BusPDR_BUS_Voltage"], "incomplete_curves": True}
    )

    assert notices.count("Missing curves:") == 1
    assert "\\item \\textcolor{red}{BusPDR\\_BUS\\_Voltage}" in notices
    assert watermark == "\\SetWatermarkText{INVALID}"


def test_a_stable_test_is_labelled_as_such():
    assert report._stability_label(True) == "stable"


def test_a_test_whose_stability_is_unknown_is_labelled_not_available():
    assert report._stability_label("N/A") == "N/A"


def test_an_unstable_test_is_labelled_with_a_latex_command_in_red():
    label = report._stability_label(False)

    assert label == r"\textcolor{red}{unstable}"
    assert "\t" not in label


def test_main_template_of_a_verification_keeps_dynawo_and_the_step_response_appendix():
    templates = Path(report.__file__).resolve().parent.parent / "templates" / "reports"

    rendered = report.get_template(templates, REPORT_NAME).render(
        {"summaryReport": [], "reports": []}
    )

    assert r"using \Dynawo~\cite{Dynawo}" in rendered
    assert "step_response_characteristics" in rendered


def test_a_report_whose_tests_have_no_page_brings_the_logo_it_includes(tmp_path):
    class Producer:
        def is_dynawo_model(self):
            return False

        def get_producer_path(self):
            return tmp_path / "ProducerCurves"

        def has_reference_curves_path(self):
            return False

        def get_sim_type(self):
            return ELECTRIC_PERFORMANCE_BESS

    class Parameters:
        def get_working_dir(self):
            return tmp_path

        def get_producer(self):
            return Producer()

        def get_sim_type(self):
            return ELECTRIC_PERFORMANCE_BESS

        def get_producer_workbook(self):
            return None

    (tmp_path / "Latex").mkdir()
    test_without_envelopes = Summary(
        producer_name="Producer",
        id=18,
        zone=1,
        pcs="PCS_RTE-I18z1",
        benchmark="S_VolAngStep1",
        operating_condition="OC2",
        compliance=Compliance.WithoutEnvelopes,
        report_name="report.RTE-I18z1.tex",
    )
    pcs_results = {"producer": "Producer", "report_name": "report.RTE-I18z1.tex"}

    report.create_pdf(
        [test_without_envelopes],
        {"Producer_PCS_RTE-I18z1": pcs_results},
        Parameters(),
        Path("templates/reports"),
        dry_run=True,
    )

    assert (tmp_path / "Latex" / "TSO_logo.pdf").is_file()


class _SummaryProducer:
    def is_dynawo_model(self):
        return True

    def get_producer_path(self):
        return Path("examples/Model/Wind/IECA2015/Dynawo")

    def has_reference_curves_path(self):
        return True

    def get_reference_path(self):
        return Path("examples/Model/Wind/IECA2015/ReferenceCurves")


class _SummaryParameters:
    def __init__(self, workbook=None):
        self._workbook = workbook

    def get_producer(self):
        return _SummaryProducer()

    def get_launcher_dwo(self):
        return Path("dynawo.sh")

    def get_producer_workbook(self):
        return self._workbook


def _logged_summary(caplog) -> str:
    [summary] = [record.getMessage() for record in caplog.records if record.name == "DyCoV.Report"]
    return summary


def test_the_summary_names_the_model_and_the_outcome_of_every_test(monkeypatch, caplog):
    monkeypatch.setattr(report.manage_files, "get_dynawo_version", lambda launcher: "2.0.0")
    tests = [
        Summary(
            producer_name="Producer",
            id=1,
            zone=3,
            pcs="PCS_RTE-I16z3",
            benchmark="USetPointStep",
            operating_condition="AReactance",
            compliance=Compliance.Simulated,
            report_name="report",
        )
    ]

    with caplog.at_level(logging.INFO, logger="DyCoV"):
        report.log_summary(tests, _SummaryParameters())

    summary = _logged_summary(caplog)
    assert "***Dynawo version: 2.0.0***" in summary
    assert "***Model dir: examples/Model/Wind/IECA2015/Dynawo***" in summary
    assert "***Reference curves dir: examples/Model/Wind/IECA2015/ReferenceCurves***" in summary
    [row] = [line for line in summary.splitlines() if "PCS_RTE-" in line]
    assert row.split()[1:4] == ["PCS_RTE-I16z3", "USetPointStep", "AReactance"]
    assert row[20 + 15 + 25 + 40 :].strip() == "Simulated"


def test_the_summary_of_a_workbook_names_the_workbook_alone(monkeypatch, caplog):
    monkeypatch.setattr(report.manage_files, "get_dynawo_version", lambda launcher: "2.0.0")

    with caplog.at_level(logging.INFO, logger="DyCoV"):
        report.log_summary([], _SummaryParameters(workbook=Path("Producer.xlsx")))

    summary = _logged_summary(caplog)
    assert "***Workbook: Producer.xlsx***" in summary
    assert "Model dir" not in summary
    assert "Reference curves dir" not in summary


_PACKAGED_REPORTS = Path(report.__file__).resolve().parent.parent / "templates"
_PCS_REPORTS = Path("reports/model/PPM/PCS_RTE-I16z3")


def _copy_the_templates(tmp_path: Path, monkeypatch, user_templates: dict) -> Path:
    config_dir = tmp_path / "config"
    user_dir = config_dir / "templates" / _PCS_REPORTS
    user_dir.mkdir(parents=True)
    for name, text in user_templates.items():
        (user_dir / name).write_text(text)
    monkeypatch.setattr(type(report.config), "get_config_dir", lambda self: config_dir)
    latex_dir = tmp_path / "Latex"
    latex_dir.mkdir()
    report.copy_pcs_latex_files(
        Path("templates/reports"), "model/PPM", "PCS_RTE-I16z3", "Producer", latex_dir
    )
    return latex_dir


def test_a_user_report_template_replaces_the_packaged_one_of_the_same_name(
    tmp_path, monkeypatch, set_user_option
):
    set_user_option("DTR", "current", "20240215")

    latex_dir = _copy_the_templates(
        tmp_path, monkeypatch, {"report.GridVoltageSwell.QMax.tex": "USER TEMPLATE"}
    )

    assert (latex_dir / "Producer.report.GridVoltageSwell.QMax.tex").read_text() == (
        "USER TEMPLATE"
    )
    packaged = _PACKAGED_REPORTS / _PCS_REPORTS / "report.GridVoltageSwell.QMin.tex"
    assert (latex_dir / "Producer.report.GridVoltageSwell.QMin.tex").read_text() == (
        packaged.read_text()
    )


def test_a_user_report_template_replaces_the_one_of_the_revision_of_the_dtr(
    tmp_path, monkeypatch, set_user_option
):
    set_user_option("DTR", "current", "20260723")

    latex_dir = _copy_the_templates(
        tmp_path, monkeypatch, {"report.GridVoltageDip.Qzero.tex": "USER TEMPLATE"}
    )

    assert (latex_dir / "Producer.report.GridVoltageDip.Qzero.tex").read_text() == (
        "USER TEMPLATE"
    )


def test_the_revision_of_the_dtr_replaces_the_packaged_report_template(
    tmp_path, monkeypatch, set_user_option
):
    set_user_option("DTR", "current", "20260723")

    latex_dir = _copy_the_templates(tmp_path, monkeypatch, {})

    delta = _PACKAGED_REPORTS / "revisions/20260723" / _PCS_REPORTS
    assert (latex_dir / "Producer.report.GridVoltageDip.Qzero.tex").read_text() == (
        (delta / "report.GridVoltageDip.Qzero.tex").read_text()
    )


def test_a_user_report_template_under_a_new_name_is_added_to_the_packaged_ones(
    tmp_path, monkeypatch, set_user_option
):
    set_user_option("DTR", "current", "20240215")

    latex_dir = _copy_the_templates(
        tmp_path, monkeypatch, {"report.GridVoltageSwell.QMaxBis.tex": "USER TEMPLATE"}
    )

    assert (latex_dir / "Producer.report.GridVoltageSwell.QMaxBis.tex").exists()
    assert (latex_dir / "Producer.report.GridVoltageSwell.QMax.tex").exists()


class _CircuitPcs:
    def __init__(self, zone: int):
        self._zone = zone

    def get_name(self):
        return f"PCS_RTE-I16z{self._zone}"

    def get_zone(self):
        return self._zone


class _CircuitProducer:
    def __init__(self, group_xfmrs: list):
        self.group_xfmrs = group_xfmrs

    def get_category(self):
        return "B"

    def is_field_measurements(self):
        return False


_ZONE1_SCHEMATIC = "circuit_z1_setpoint.tikz"


def _latex_dir_with_the_zone1_schematic(tmp_path: Path) -> Path:
    shipped = (
        Path(report.__file__).resolve().parent.parent
        / "templates/reports/model/PPM/PCS_RTE-I16z1"
        / _ZONE1_SCHEMATIC
    )
    (tmp_path / _ZONE1_SCHEMATIC).write_text(shipped.read_text())
    (tmp_path / "report.tex").write_text("")
    return tmp_path


def _prepare(latex_dir: Path, zone: int, group_xfmrs: list, producer: str = "Producer") -> None:
    pcs_results = {"producer": producer, "pcs": _CircuitPcs(zone)}
    report._pcs_replace(latex_dir, pcs_results, "report.tex", _CircuitProducer(group_xfmrs))


def _schematic_of(latex_dir: Path, unit: str = "Producer") -> str:
    return (latex_dir / f"{unit}.{_ZONE1_SCHEMATIC}").read_text()


def test_the_zone1_schematic_follows_the_zone1_model_when_a_zone3_pcs_gets_there_first(
    tmp_path,
):
    latex_dir = _latex_dir_with_the_zone1_schematic(tmp_path)

    _prepare(latex_dir, zone=3, group_xfmrs=[])
    _prepare(latex_dir, zone=1, group_xfmrs=["Group_Xfmr"])

    schematic = _schematic_of(latex_dir)
    assert "Group\\\\ transformer" in schematic
    assert "BLOCK" not in schematic


def test_the_zone1_schematic_draws_no_group_transformer_the_zone1_model_lacks(tmp_path):
    latex_dir = _latex_dir_with_the_zone1_schematic(tmp_path)

    _prepare(latex_dir, zone=1, group_xfmrs=[])

    schematic = _schematic_of(latex_dir)
    assert "transformer" not in schematic
    assert "BLOCK" not in schematic


def test_a_zone3_pcs_leaves_the_zone1_schematic_to_the_zone1_pcs(tmp_path):
    latex_dir = _latex_dir_with_the_zone1_schematic(tmp_path)
    template = (latex_dir / _ZONE1_SCHEMATIC).read_text()

    _prepare(latex_dir, zone=3, group_xfmrs=[])

    assert (latex_dir / _ZONE1_SCHEMATIC).read_text() == template
    assert not (latex_dir / f"Producer.{_ZONE1_SCHEMATIC}").exists()


def test_each_zone1_unit_draws_its_own_schematic_from_the_shared_template(tmp_path):
    latex_dir = _latex_dir_with_the_zone1_schematic(tmp_path)
    template = (latex_dir / _ZONE1_SCHEMATIC).read_text()

    _prepare(latex_dir, zone=1, group_xfmrs=["Group_Xfmr"], producer="Unit_A")
    _prepare(latex_dir, zone=1, group_xfmrs=[], producer="Unit_B")

    assert "Group\\\\ transformer" in _schematic_of(latex_dir, "UnitA")
    assert "transformer" not in _schematic_of(latex_dir, "UnitB")
    assert (latex_dir / _ZONE1_SCHEMATIC).read_text() == template


def test_the_report_of_a_unit_names_the_files_of_the_unit(tmp_path):
    latex_dir = _latex_dir_with_the_zone1_schematic(tmp_path)
    (latex_dir / "report.tex").write_text("{{ producercommand }}")

    _prepare(latex_dir, zone=1, group_xfmrs=[], producer="Unit_B")

    assert "\\renewcommand{\\ProducerFiles}{UnitB}" in (latex_dir / "report.tex").read_text()
