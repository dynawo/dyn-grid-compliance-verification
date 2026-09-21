#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from typing import List

import numpy as np

# Where the test looks: just before the event, during it, and along the response that follows.
# Away from there a reference has nothing to say, which is what decides both where the noise
# goes and how densely the samples are kept.
WINDOW_LEAD = 1.0  # s before the event
WINDOW_TAIL = 10.0  # s after it
# An event that never clears is declared as lasting longer than the simulation. What the test
# looks at is still the response to it, not the hours it would go on for.
EVENT_SPAN = 10.0  # s at most
# A span is entered and left over this margin, so that what it changes never ends in a step.
BLEND_MARGIN = 0.1  # s


def event_window(event_time: float, event_duration: float) -> tuple:
    return event_time - WINDOW_LEAD, event_time + min(event_duration, EVENT_SPAN) + WINDOW_TAIL


def blend_weights(time: np.ndarray, spans: List[tuple]) -> np.ndarray:
    weights = np.zeros(len(time))
    for start, end in spans:
        rising = (time >= start - BLEND_MARGIN) & (time < start)
        falling = (time > end) & (time <= end + BLEND_MARGIN)
        weights[(time >= start) & (time <= end)] = 1.0
        weights[rising] = np.maximum(
            weights[rising], (time[rising] - start + BLEND_MARGIN) / BLEND_MARGIN
        )
        weights[falling] = np.maximum(
            weights[falling], (end + BLEND_MARGIN - time[falling]) / BLEND_MARGIN
        )
    return weights
