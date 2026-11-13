#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
# marinjl@aia.es
# omsg@aia.es
# demiguelm@aia.es
#

import numpy as np
import pytest

from dycov.gfm.outputs import find_end_trim_index, find_start_trim_index, plot_results


@pytest.mark.parametrize("find_index", [find_start_trim_index, find_end_trim_index])
@pytest.mark.parametrize(
    "signals",
    [
        (np.array([0.0, 1, 2, 3]), np.zeros(3), np.zeros(4)),
        (np.array([0.0, 0, 0, 3]), np.zeros(3), np.zeros(4)),
        (np.zeros(4), np.zeros(4), np.zeros(5)),
    ],
)
def test_trim_indices_reject_signals_of_different_lengths(find_index, signals):
    with pytest.raises(ValueError, match="same length"):
        find_index(*signals)


def _plot(path, **options):
    time = np.linspace(0.0, 1.0, 50)
    signal = np.where(time < 0.5, 0.0, 1.0)
    arguments = dict(
        path=path / "figure",
        title="Figure",
        magnitude="P",
        time_array=time,
        event_time=0.5,
        shift_time=0.0,
        pcc_signal=signal,
        lower_envelope=signal - 0.1,
        upper_envelope=signal + 0.1,
        output_format="png&html",
    )
    arguments.update(options)
    plot_results(**arguments)


@pytest.mark.parametrize("output_format", ["", "pdf", "svg&jpg"])
def test_plot_rejects_a_format_that_names_no_output(tmp_path, output_format):
    with pytest.raises(ValueError, match="png, html or both"):
        _plot(tmp_path, output_format=output_format)
    assert not list(tmp_path.iterdir())


def test_plot_rejects_a_format_that_is_not_text(tmp_path):
    with pytest.raises(TypeError, match="output format must be text"):
        _plot(tmp_path, output_format=None)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("output_format", ["png", "html"])
def test_plot_rejects_a_disclaimer_that_is_not_text(tmp_path, output_format):
    with pytest.raises(TypeError, match="disclaimer message must be text"):
        _plot(tmp_path, output_format=output_format, show_disclaimer=True, disclaimer_message=5)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "lengths",
    [
        dict(time_array=np.linspace(0.0, 1.0, 40)),
        dict(lower_envelope=np.zeros(40)),
        dict(extra_envelopes={"envelope_overdamped": np.zeros(40)}),
    ],
)
def test_plot_rejects_a_time_or_envelope_of_another_length(tmp_path, lengths):
    with pytest.raises(ValueError, match="same length"):
        _plot(tmp_path, **lengths)
    assert not list(tmp_path.iterdir())
