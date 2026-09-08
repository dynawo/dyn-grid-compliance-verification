#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The per-test ``.dict``: how to read one file of reference curves.

The metadata describes the user's own curve files, not the model, so the tool cannot fill it in:
it writes the keys with their meaning and leaves the values for the user.
"""

from __future__ import annotations

from .common import ABC_HELP, dictionary_lines, time_line

# Metadata keys of a .dict, in DyCoV's own order, with the guidance it documents them by.
METADATA_HELP = {
    "is_field_measurements": [
        "True when the reference curves are field measurements",
    ],
    "sim_t_event_start": [
        "Instant of time at which the event or fault starts",
        "Variable sim_t_event_start is called simply sim_t_event in the DTR",
    ],
    "fault_duration": [
        "Duration of the event or fault",
    ],
    "frequency_sampling": [
        "Frequency sampling of the reference curves",
    ],
}
# Optional per-generator key DyCoV also reads from this section.
_METADATA_OPTIONAL = [
    "# The maximum injected current of a generator, when the curves come from field measurements:",
    "#    <generator>_GEN_MaxInjectedCurrentPu =",
]


def _metadata_lines() -> list:
    lines = ["[Curves-Metadata]"]
    for key, help_lines in METADATA_HELP.items():
        lines += ["# %s" % text for text in help_lines]
        lines.append("%s =" % key)
    return lines + _METADATA_OPTIONAL


def text(signals) -> str:
    """Render one test's file: the metadata skeleton plus its zone's curve dictionary.

    Parameters
    ----------
    signals: signals.ZoneSignals
        The zone the test belongs to, which fixes the curves the file declares.

    Returns
    -------
    str
        The file contents, ready to write.
    """
    lines = _metadata_lines()
    lines += ["", "[Curves-Dictionary]"] + ABC_HELP + [time_line()]
    lines += dictionary_lines(signals.curves)
    return "\n".join(lines) + "\n"
