#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the figures of the PDF report."""

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import pytest

from dycov.report import figure
from dycov.report.figure import (
    _add_curve2plot,
    _get_xrange,
    _get_xrange_for_curve,
    _get_yrange,
    create_plot,
    get_common_time_range,
    get_curves2plot,
)
from dycov.report.figure_decorations import draw_additional_curves, draw_response_characteristics
from dycov.report.types import (
    DynamicBand,
    EventMarker,
    FigureDescription,
    FinalValueBand,
    FrequencyBand,
)

matplotlib.use("Agg")


@pytest.fixture(autouse=True)
def cleanup_matplotlib():
    yield
    plt.close("all")


def test_create_plot_saves_expected_plot(tmp_path):
    time = [0, 1, 2, 3, 4]
    curves = [{"curve": [0, 1, 2, 3, 4], "color": "#4c72b0", "style": "-"}]
    time_reference = [0, 1, 2, 3, 4]
    curves_reference = [{"curve": [0, 0.5, 1, 1.5, 2], "color": "#dd8452", "style": "-"}]
    time_range = {"min": 0, "max": 4}
    results = {"AVR_5_crvs": [[1, 1, 1, 1, 1]], "time_85U": 2, "sim_t_event_start": 0}
    output_file = tmp_path / "plot.png"
    figure_description = FigureDescription(
        name="ActiveCurrentInjTerminal",
        variables="ActiveCurrentInjTerminal",
        ylabel="MW",
    )

    create_plot(
        time,
        figure_description,
        curves,
        time_reference,
        curves_reference,
        time_range,
        output_file,
        results,
    )

    assert output_file.exists()
    assert output_file.stat().st_size > 0


def _make_plot_curve(name: str) -> dict:
    return {"name": name, "curve": [0.0, 0.5, 1.0], "color": "#4c72b0", "style": "-"}


def test_create_plot_marks_the_mxe_the_zone_measured_on_the_curve(monkeypatch, tmp_path):
    marked = []
    monkeypatch.setattr(
        figure,
        "draw_mxe",
        lambda renderer, curve_name, results, zone: marked.append((curve_name, zone)),
    )
    figure_description = FigureDescription(
        name="fig_V", variables=[{"type": "bus", "variable": "Voltage"}], ylabel="V"
    )

    create_plot(
        [0, 1, 2],
        figure_description,
        [_make_plot_curve("BusPDR_BUS_Voltage")],
        None,
        None,
        {"min": 0, "max": 2},
        tmp_path / "plot.pdf",
        {},
        zone=1,
    )

    assert marked == [("BusPDR_BUS_Voltage", 1)]


def test_create_plot_marks_no_mxe_on_a_figure_of_several_magnitudes(monkeypatch, tmp_path):
    """#553: the figure of the currents draws Ip and Iq together, and their MXE belongs to the
    figures that draw each of them alone."""
    marked = []
    monkeypatch.setattr(figure, "draw_mxe", lambda *args: marked.append(args[1]))
    figure_description = FigureDescription(
        name="fig_I",
        variables=[
            {"type": "generator", "variable": "ActiveCurrentInjTerminal"},
            {"type": "generator", "variable": "ReactiveCurrentInjTerminal"},
        ],
        ylabel="I",
    )
    curves = [
        _make_plot_curve("WT_GEN_ActiveCurrentInjTerminal"),
        _make_plot_curve("WT_GEN_ReactiveCurrentInjTerminal"),
    ]

    create_plot(
        [0, 1, 2],
        figure_description,
        curves,
        None,
        None,
        {"min": 0, "max": 2},
        tmp_path / "plot.pdf",
        {},
        zone=1,
    )

    assert marked == []


def test_get_common_time_range_includes_all_events():
    time = [0, 1, 2, 3, 4]
    curves = {"time": time, "BusPDR_BUS_ActivePower": [0, 1, 2, 3, 4]}
    results = {
        "curves": curves,
        "sim_t_event_start": 1.0,
        "sim_t_event_end": 3.0,
        "calc_settling_time": 3.5,
    }

    figures_description = {
        "OC": [
            FigureDescription(
                name="desc", variables=[{"type": "bus", "variable": "ActivePower"}], ylabel=""
            )
        ]
    }

    unit_characteristics = {}
    operating_condition = "OC.Benchmark"

    xmin, xmax = get_common_time_range(
        operating_condition,
        unit_characteristics,
        figures_description,
        results,
    )
    assert xmin <= 1.0
    assert xmax >= 3.5


def test_get_xrange_for_curve_falls_back_to_defaults_on_empty_values(set_user_option):
    set_user_option("Figures", "graph_rel_tol", "")
    set_user_option("Figures", "graph_abs_tol", "")
    set_user_option("Figures", "graph_preevent_trange_pct", "")
    set_user_option("Figures", "graph_postevent_trange_pct", "")
    time_curve = [0, 1, 2, 3, 4]
    curve = [0, 5, 5, 5, 5]
    sim_t_event_end = 0.5

    xmin, xmax = _get_xrange_for_curve("OC.Benchmark", {}, time_curve, curve, sim_t_event_end)

    # Settling at t=1, defaults 15%/20% of the [t_event, t_SS] window (min 1s)
    assert xmin == pytest.approx(0.35)
    assert xmax == pytest.approx(1.2)


def test_get_xrange_for_curve_honors_figures_overrides(set_user_option):
    set_user_option("Figures", "graph_preevent_trange_pct", "50")
    set_user_option("Figures", "graph_postevent_trange_pct", "100")
    time_curve = [0, 1, 2, 3, 4]
    curve = [0, 5, 5, 5, 5]
    sim_t_event_end = 0.5

    xmin, xmax = _get_xrange_for_curve("OC.Benchmark", {}, time_curve, curve, sim_t_event_end)

    assert xmin == pytest.approx(0.0)
    assert xmax == pytest.approx(2.0)


@pytest.mark.parametrize(
    "variable, color",
    [
        ("ActiveCurrentInjTerminal", "#64b5cd"),
        ("ReactiveCurrentInjTerminal", "#8172b3"),
        ("VoltageSetpointPu", "#8c8c8c"),
        ("ActivePowerSetpointPu", "#8c8c8c"),
        ("ReactivePowerSetpointPu", "#8c8c8c"),
        ("Other", "#4c72b0"),
    ],
)
def test_add_curve2plot_applies_color_and_style(variable, color):
    curves = pd.DataFrame({variable: [1, 2, 3]})
    plot_curves = []

    _add_curve2plot(variable, variable, curves, plot_curves)

    assert [(curve["name"], curve["color"]) for curve in plot_curves] == [(variable, color)]


_POWER_WITH_ITS_SETPOINT = [
    {"type": "generator", "variable": "ActivePowerControlledPu"},
    {"type": "generator", "variable": "ActivePowerSetpointPu"},
]


def test_get_curves2plot_draws_the_setpoint_of_the_reference_in_a_style_of_its_own():
    """#554: the setpoint of the reference is the trace that shows whether the reference curves
    stepped the setpoint the test applies."""
    reference = pd.DataFrame(
        {
            "WT_GEN_ActivePowerControlledPu": [0.85, 0.80],
            "WT_GEN_ActivePowerSetpointPu": [0.85, 0.80],
        }
    )

    plot_curves = get_curves2plot(_POWER_WITH_ITS_SETPOINT, reference, is_reference=True)

    assert [(curve["name"], curve["color"], curve["style"]) for curve in plot_curves] == [
        ("WT_GEN_ActivePowerControlledPu", "#dd8452", "-"),
        ("WT_GEN_ActivePowerSetpointPu", "#dd8452", "--"),
    ]


def test_get_curves2plot_draws_the_magnitude_of_a_reference_without_its_setpoint_alone():
    reference = pd.DataFrame({"WT_GEN_ActivePowerControlledPu": [0.85, 0.80]})

    plot_curves = get_curves2plot(_POWER_WITH_ITS_SETPOINT, reference, is_reference=True)

    assert [curve["name"] for curve in plot_curves] == ["WT_GEN_ActivePowerControlledPu"]


def test_get_curves2plot_skips_a_bus_curve_the_curves_do_not_carry():
    reference = pd.DataFrame({"BusPDR_BUS_Voltage": [1.0, 0.9]})
    variables = [
        {"type": "bus", "variable": "Voltage"},
        {"type": "bus", "variable": "ActivePower"},
    ]

    plot_curves = get_curves2plot(variables, reference, is_reference=True)

    assert [curve["name"] for curve in plot_curves] == ["BusPDR_BUS_Voltage"]


def test_save_plot_draws_each_reference_curve_in_its_own_style(tmp_path):
    fig, ax = plt.subplots()
    curves_reference = [
        {"curve": [0.85, 0.85, 0.80], "color": "#dd8452", "style": "-"},
        {"curve": [0.85, 0.80, 0.80], "color": "#dd8452", "style": "--"},
    ]

    figure._save_plot(
        fig,
        ax,
        [0, 1, 2],
        [],
        [0, 1, 2],
        curves_reference,
        {"min": None, "max": None},
        tmp_path / "plot.pdf",
        "P",
        None,
        None,
    )

    assert [line.get_linestyle() for line in ax.get_lines()] == ["-", "--"]


def test_create_plot_marks_the_mxe_of_a_magnitude_drawn_with_its_setpoint(monkeypatch, tmp_path):
    marked = []
    monkeypatch.setattr(figure, "draw_mxe", lambda *args: marked.append(args[1]))
    figure_description = FigureDescription(
        name="fig_P", variables=_POWER_WITH_ITS_SETPOINT, ylabel="P"
    )
    curves = [
        _make_plot_curve("WT_GEN_ActivePowerControlledPu"),
        _make_plot_curve("WT_GEN_ActivePowerSetpointPu"),
    ]

    create_plot(
        [0, 1, 2],
        figure_description,
        curves,
        None,
        None,
        {"min": 0, "max": 2},
        tmp_path / "plot.pdf",
        {},
        zone=1,
    )

    assert marked == ["WT_GEN_ActivePowerControlledPu"]


def test_get_yrange_applies_explicit_range_for_low_variation(set_user_option):
    set_user_option("Figures", "graph_minvariation_yrange_pct", "100")
    set_user_option("Figures", "graph_bottom_yrange_pct", "10")
    set_user_option("Figures", "graph_top_yrange_pct", "5")
    curve = [1, 1, 1, 1, 1]

    yrange_min, yrange_max = _get_yrange([{"curve": curve}])

    # Flat curve: variation replaced by 0.1*|midpoint|, expanded by 1.2 / 1.1
    assert yrange_min == pytest.approx(0.94)
    assert yrange_max == pytest.approx(1.055)


def test_get_yrange_honors_figures_margins(set_user_option):
    set_user_option("Figures", "graph_minvariation_yrange_pct", "100")
    set_user_option("Figures", "graph_bottom_yrange_pct", "50")
    set_user_option("Figures", "graph_top_yrange_pct", "25")
    curve = [1.0, 1.1]

    yrange_min, yrange_max = _get_yrange([{"curve": curve}])

    assert yrange_min == pytest.approx(0.95)
    assert yrange_max == pytest.approx(1.125)


def test_get_yrange_auto_range_option_disables_explicit_range(set_user_option):
    set_user_option("Figures", "graph_auto_range_yrange", "true")
    curve = [1, 1, 1, 1, 1]

    yrange_min, yrange_max = _get_yrange([{"curve": curve}])

    assert yrange_min is None
    assert yrange_max is None


def test_graph_options_in_global_section_are_ignored(set_user_option):
    set_user_option("Global", "graph_bottom_yrange_pct", "1000")
    set_user_option("Global", "graph_top_yrange_pct", "1000")
    curve = [1, 1, 1, 1, 1]

    yrange_min, yrange_max = _get_yrange([{"curve": curve}])

    # The [Figures] defaults apply; values under [Global] have no effect
    assert yrange_min == pytest.approx(0.94)
    assert yrange_max == pytest.approx(1.055)


def test_draw_additional_curves_draws_every_band_and_marker(renderer):
    results = {
        "time_85U": 2,
        "sim_t_event_start": 0,
        "AVR_5_crvs": [[1, 1, 1, 1, 1]],
    }
    figure_description = FigureDescription(
        name="test",
        variables="BusPDR_BUS_ActivePower",
        ylabel="",
        tolerance_band=FinalValueBand(upper=10.0, lower=10.0, color="#55a868"),
        frequency_bands=[FrequencyBand(upper=1.0, lower=1.0)],
        dynamic_band=DynamicBand(upper=5.0, lower=5.0, source_key="AVR_5_crvs"),
        event_markers=[EventMarker(source_key="time_85U")],
    )

    ymin, ymax = draw_additional_curves(
        renderer, figure_description, [0, 1, 2, 3, 4], 1, results, 0, 2
    )

    # 10% around the last value, then 1 Hz around 50 Hz in pu, 5% around the AVR curve, T85U
    assert renderer.marks == [
        ("hline", pytest.approx(1.1)),
        ("hline", pytest.approx(0.9)),
        ("hline", pytest.approx(1.02)),
        ("hline", pytest.approx(0.98)),
        ("curve", pytest.approx([1.05] * 5)),
        ("curve", pytest.approx([0.95] * 5)),
        ("vline", 2),
    ]
    assert (ymin, ymax) == (0, 2)


def test_draw_response_characteristics_marks_reaction_rise_and_settling(renderer):
    results = {
        "calc_reaction_target": {"BusPDR_BUS_ActivePower": 2.0},
        "calc_reaction_time": 1.0,
        "sim_t_event_start": 0.5,
        "calc_rise_target": {"BusPDR_BUS_ActivePower": 3.0},
        "calc_rise_time": 2.0,
        "calc_settling_tube": {"BusPDR_BUS_ActivePower": (1.5, 3.5)},
        "calc_settling_time": 3.0,
        "calc_ss_value": 2.5,
    }

    draw_response_characteristics(renderer, "BusPDR_BUS_ActivePower", results)

    assert renderer.marks == [
        ("hline", 2.0),
        ("vline", 1.5),
        ("hline", 3.0),
        ("vline", 2.5),
        ("scatter", (2.5, 3.0)),
        ("annotation", "2.5000s"),
        ("hrect", (1.5, 3.5)),
        ("vline", 3.5),
        ("scatter", (3.5, 2.5)),
        ("annotation", "3.5000s"),
    ]


# ---------------------------------------------------------------------------
# Frequency drawn in Hz
# ---------------------------------------------------------------------------


def _frequency_figure(*deviations: float) -> FigureDescription:
    return FigureDescription(
        name="fig_WRef",
        variables=[{"type": "generator", "variable": "NetworkFrequencyPu"}],
        ylabel=r"$\omega$ (Hz)",
        frequency_bands=[FrequencyBand(upper=d, lower=d) for d in deviations or (1.0,)],
        in_hz=True,
    )


def _frequency_curve(values: list) -> dict:
    return {"name": "WT_GEN_NetworkFrequencyPu", "curve": values, "color": "#4c72b0", "style": "-"}


def test_create_plot_draws_the_frequency_and_its_reference_in_hz(monkeypatch, tmp_path):
    drawn = {}
    monkeypatch.setattr(
        figure,
        "_save_plot",
        lambda fig, ax, time, curves, time_reference, curves_reference, *args: drawn.update(
            curves=curves, reference=curves_reference
        ),
    )

    create_plot(
        [0, 1],
        _frequency_figure(),
        [_frequency_curve([1.0, 0.98])],
        [0, 1],
        [_frequency_curve([1.0, 0.99])],
        {"min": 0, "max": 1},
        tmp_path / "plot.pdf",
        {},
    )

    assert [curve["curve"] for curve in drawn["curves"]] == [pytest.approx([50.0, 49.0])]
    assert [curve["curve"] for curve in drawn["reference"]] == [pytest.approx([50.0, 49.5])]


def test_draw_additional_curves_draws_the_frequency_band_of_a_figure_in_hz_in_hz(renderer):
    draw_additional_curves(renderer, _frequency_figure(), [0, 1], 1.0, {}, None, None)

    assert renderer.marks == [("hline", pytest.approx(51.0)), ("hline", pytest.approx(49.0))]


def test_draw_additional_curves_draws_every_frequency_band_of_a_figure(renderer):
    draw_additional_curves(renderer, _frequency_figure(0.2, 0.25), [0, 1], 1.0, {}, None, None)

    assert renderer.marks == [
        ("hline", pytest.approx(50.2)),
        ("hline", pytest.approx(49.8)),
        ("hline", pytest.approx(50.25)),
        ("hline", pytest.approx(49.75)),
    ]


def test_draw_response_characteristics_marks_the_settling_of_a_figure_in_hz_in_hz(renderer):
    results = {
        "calc_settling_tube": {"WT_GEN_NetworkFrequencyPu": (1.0099, 1.0101)},
        "calc_settling_time": 0.37,
        "sim_t_event_start": 20.0,
        "calc_ss_value": 1.01,
    }

    draw_response_characteristics(renderer, "WT_GEN_NetworkFrequencyPu", results, 50.0)

    assert renderer.marks == [
        ("hrect", pytest.approx((50.495, 50.505))),
        ("vline", pytest.approx(20.37)),
        ("scatter", pytest.approx((20.37, 50.5))),
        ("annotation", "20.3700s"),
    ]


def test_get_xrange_aggregates_curve_ranges(monkeypatch):
    curve_ranges = iter([(1, 3), (0, 2), (0.5, 4)])
    monkeypatch.setattr(figure, "_get_xrange_for_curve", lambda *args: next(curve_ranges))
    curves = [{"curve": [1, 2, 3]}, {"curve": [2, 3, 4]}, {"curve": [0, 5, 6]}]

    xmin, xmax = _get_xrange("OC.Benchmark", {}, [0, 1, 2], curves, 2)

    assert (xmin, xmax) == (0, 4)


def test_get_yrange_falls_back_to_defaults_on_invalid_values(set_user_option):
    set_user_option("Figures", "graph_minvariation_yrange_pct", "not_a_number")
    set_user_option("Figures", "graph_bottom_yrange_pct", "not_a_number")
    set_user_option("Figures", "graph_top_yrange_pct", "not_a_number")
    curve = [1, 1, 1, 1, 1]

    yrange_min, yrange_max = _get_yrange([{"curve": curve}])

    assert yrange_min == pytest.approx(0.94)
    assert yrange_max == pytest.approx(1.055)
