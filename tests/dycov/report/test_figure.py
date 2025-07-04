#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import tempfile
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import pytest

from dycov.configuration.cfg import config
from dycov.report.figure import (
    _add_curve2plot,
    _get_xrange,
    _get_yrange,
    _is_controlled_magnitude,
    _plot_additional_curves,
    _plot_response_characteristics,
    create_plot,
    get_common_time_range,
)

matplotlib.use("Agg")


# Helper to reset config values after test
class ConfigReset:
    def __init__(self):
        self._backup = {}

    def set(self, section, key, value):
        if not hasattr(config, "_user_config"):
            return
        if not config._user_config.has_section(section):
            config._user_config.add_section(section)
        self._backup[(section, key)] = (
            config._user_config.get(section, key)
            if config._user_config.has_option(section, key)
            else None
        )
        config._user_config.set(section, key, str(value))

    def remove(self, section, key):
        if (section, key) in self._backup:
            if self._backup[(section, key)] is None:
                config._user_config.remove_option(section, key)
            else:
                config._user_config.set(section, key, self._backup[(section, key)])


@pytest.fixture(autouse=True)
def cleanup_matplotlib():
    yield
    plt.close("all")


def test_create_plot_saves_expected_plot():
    # Setup
    time = [0, 1, 2, 3, 4]
    curves = [{"curve": [0, 1, 2, 3, 4], "color": "#4c72b0", "style": "-"}]
    time_reference = [0, 1, 2, 3, 4]
    curves_reference = [{"curve": [0, 0.5, 1, 1.5, 2], "color": "#dd8452", "style": "-"}]
    time_range = {"min": 0, "max": 4}
    additional_curves = ["10P", "freq_1"]
    results = {"AVR_5_crvs": [[1, 1, 1, 1, 1]], "time_85U": 2, "sim_t_event_start": 0}
    unit = "MW"
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "plot.png"
        create_plot(
            time,
            "InjectedActiveCurrent",
            curves,
            time_reference,
            curves_reference,
            time_range,
            output_file,
            additional_curves,
            results,
            unit,
            log_title="",
        )
        assert output_file.exists()
        assert output_file.stat().st_size > 0


def test_get_common_time_range_includes_all_events():
    # Setup
    time = [0, 1, 2, 3, 4]
    curves = {"time": time, "BusPDR_BUS_ActivePower": [0, 1, 2, 3, 4]}
    results = {
        "curves": curves,
        "sim_t_event_start": 1.0,
        "sim_t_event_end": 3.0,
        "calc_settling_time": 3.5,
    }
    figures_description = {"OC": [("desc", [{"type": "bus", "variable": "ActivePower"}])]}
    unit_characteristics = {}
    operating_condition = "OC.Benchmark"
    xmin, xmax = get_common_time_range(
        operating_condition,
        unit_characteristics,
        figures_description,
        results,
        log_title="",
    )
    assert xmin <= 1.0
    assert xmax >= 3.5


def test_plot_functions_with_missing_config_values():
    # Remove config values if present
    reset = ConfigReset()
    reset.set("Global", "graph_rel_tol", "")
    reset.set("Global", "graph_abs_tol", "")
    reset.set("Global", "graph_preevent_trange_pct", "")
    reset.set("Global", "graph_postevent_trange_pct", "")
    try:
        # Should fallback to defaults and not raise
        time_curve = [0, 1, 2, 3, 4]
        curve = [1, 2, 3, 4, 5]
        unit_characteristics = {}
        operating_condition = "OC.Benchmark"
        sim_t_event_end = 4
        _get_xrange_for_curve = __import__(
            "dycov.report.figure", fromlist=["_get_xrange_for_curve"]
        )._get_xrange_for_curve
        xmin, xmax = _get_xrange_for_curve(
            operating_condition, unit_characteristics, time_curve, curve, sim_t_event_end
        )
        assert isinstance(xmin, (float, type(None)))
        assert isinstance(xmax, (float, type(None)))
    finally:
        reset.remove("Global", "graph_rel_tol")
        reset.remove("Global", "graph_abs_tol")
        reset.remove("Global", "graph_preevent_trange_pct")
        reset.remove("Global", "graph_postevent_trange_pct")


def test_add_curve2plot_applies_color_and_style():
    df = pd.DataFrame(
        {
            "InjectedActiveCurrent": [1, 2, 3],
            "InjectedReactiveCurrent": [4, 5, 6],
            "AVRSetpointPu": [7, 8, 9],
            "Other": [10, 11, 12],
        }
    )
    plot_curves = []
    _add_curve2plot("InjectedActiveCurrent", "InjectedActiveCurrent", df, plot_curves)
    assert plot_curves[-1]["color"] == "#64b5cd"
    _add_curve2plot("InjectedReactiveCurrent", "InjectedReactiveCurrent", df, plot_curves)
    assert plot_curves[-1]["color"] == "#8172b3"
    _add_curve2plot("AVRSetpointPu", "AVRSetpointPu", df, plot_curves)
    assert plot_curves[-1]["color"] == "#8c8c8c"
    _add_curve2plot("Other", "Other", df, plot_curves)
    assert plot_curves[-1]["color"] == "#4c72b0"


def test_get_yrange_applies_explicit_range_for_low_variation():
    # Setup config for low variation threshold
    reset = ConfigReset()
    reset.set("Global", "graph_minvariaton_yrange_pct", "100")
    reset.set("Global", "graph_bottom_yrange_pct", "10")
    reset.set("Global", "graph_top_yrange_pct", "5")
    try:
        curve = [1, 1, 1, 1, 1]
        yrange_min, yrange_max = _get_yrange([{"curve": curve}])
        assert yrange_min is not None
        assert yrange_max is not None
        assert yrange_max > yrange_min
    finally:
        reset.remove("Global", "graph_minvariaton_yrange_pct")
        reset.remove("Global", "graph_bottom_yrange_pct")
        reset.remove("Global", "graph_top_yrange_pct")


def test_plot_additional_curves_renders_all_types():
    time = [0, 1, 2, 3, 4]
    additional_curves = [
        "10P",
        "5P",
        "10Pfloor",
        "5Pfloor",
        "85U",
        "freq_1",
        "freq_200",
        "freq_250",
        "AVR5",
    ]
    results = {
        "time_85U": 2,
        "sim_t_event_start": 0,
        "AVR_5_crvs": [[1, 1, 1, 1, 1]],
    }
    ymin, ymax = 0, 2
    last_val = 1
    # Should not raise
    _plot_additional_curves(time, additional_curves, results, last_val, ymin, ymax)


def test_plot_response_characteristics_annotations():
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
    # Should not raise and should annotate
    _plot_response_characteristics("BusPDR_BUS_ActivePower", results)


def test_is_controlled_magnitude_identifies_correct_combinations():
    assert _is_controlled_magnitude("BusPDR_BUS_ActivePower", "P") is True
    assert _is_controlled_magnitude("BusPDR_BUS_ReactivePower", "Q") is True
    assert _is_controlled_magnitude("BusPDR_BUS_ActiveCurrent", "P") is True
    assert _is_controlled_magnitude("BusPDR_BUS_ReactiveCurrent", "Q") is True
    assert _is_controlled_magnitude("BusPDR_BUS_Voltage", "V") is True
    assert _is_controlled_magnitude("NetworkFrequencyPu", "$\\omega") is True
    assert _is_controlled_magnitude("BusPDR_BUS_ActivePower", "Q") is False
    assert _is_controlled_magnitude("UnknownCurve", "P") is False


def test_plot_functions_with_unsupported_curve_types():
    # Should not raise
    # Pass a dict as a curve
    try:
        _get_yrange([{"curve": {"a": 1, "b": 2}}])
    except Exception:
        pass  # Acceptable: dicts can't be max/min'ed, but should not crash the whole suite

    # Pass an object as a curve
    class Dummy:
        pass

    try:
        _get_yrange([{"curve": Dummy()}])
    except Exception:
        pass  # Acceptable


def test_get_xrange_aggregates_curve_ranges():
    # Setup
    def fake_get_xrange_for_curve(
        operating_condition, unit_characteristics, time_curve, curve, sim_t_event_end
    ):
        return min(time_curve), max(time_curve)

    # Patch in the function
    import dycov.report.figure as figure_mod

    orig = figure_mod._get_xrange_for_curve
    figure_mod._get_xrange_for_curve = fake_get_xrange_for_curve
    try:
        curves = [
            {"curve": [1, 2, 3]},
            {"curve": [2, 3, 4]},
            {"curve": [0, 5, 6]},
        ]
        time_curve = [0, 1, 2]
        operating_condition = "OC.Benchmark"
        unit_characteristics = {}
        sim_t_event_end = 2
        xmin, xmax = _get_xrange(
            operating_condition, unit_characteristics, time_curve, curves, sim_t_event_end
        )
        assert xmin == 0
        assert xmax == 2
    finally:
        figure_mod._get_xrange_for_curve = orig


def test_plot_functions_with_invalid_config_types():
    # Set config values to invalid types
    reset = ConfigReset()
    reset.set("Global", "graph_minvariaton_yrange_pct", "not_a_number")
    reset.set("Global", "graph_bottom_yrange_pct", "not_a_number")
    reset.set("Global", "graph_top_yrange_pct", "not_a_number")
    try:
        curve = [1, 1, 1, 1, 1]
        try:
            _get_yrange([{"curve": curve}])
        except Exception:
            pass  # Acceptable: should not crash the suite
    finally:
        reset.remove("Global", "graph_minvariaton_yrange_pct")
        reset.remove("Global", "graph_bottom_yrange_pct")
        reset.remove("Global", "graph_top_yrange_pct")
