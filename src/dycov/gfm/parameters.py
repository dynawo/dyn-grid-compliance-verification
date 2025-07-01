#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from collections import namedtuple

# Named tuple to store Grid Forming (GFM) parameters. This structure
# provides immutable and descriptive access to configuration values.
GFM_Params = namedtuple(
    "GFM_Params",
    [
        "EMT",  # Electro-Magnetic Transients simulation flag
        "RatioMin",  # Minimum ratio for parameter variations
        "RatioMax",  # Maximum ratio for parameter variations
        "P0",  # Initial active power (per unit - pu)
        "delta_theta",  # Phase angle jump magnitude (degrees)
        "SCR",  # Short Circuit Ratio, indicating grid strength
        "Wb",  # Base angular frequency (radians/second)
        "Ucv",  # Converter RMS voltage (pu)
        "Ugr",  # Grid RMS voltage (pu)
        "MarginHigh",  # Upper margin for power envelopes
        "MarginLow",  # Lower margin for power envelopes
        "FinalAllowedTunnelVariation",  # Parameter for tunnel function
        "FinalAllowedTunnelPn",  # Parameter for tunnel function
        "PMax",  # Maximum allowed active power (pu)
        "PMin",  # Minimum allowed active power (pu)
    ],
)
