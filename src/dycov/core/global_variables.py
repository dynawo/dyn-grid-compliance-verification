#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

"""
This module defines global constants and numerical identifiers for various
verification types, report names, and case separators used throughout the DYCOV tool.
These constants provide a centralized and unambiguous way to refer to key
parameters and states within the application.
"""

# --- Execution Types ---
# Numerical identifiers for different execution types.
ELECTRIC_PERFORMANCE = 0
MODEL_VALIDATION = 10

# --- Electrical Performance Verification Types ---
# Numerical identifiers for electrical performance verification sub-types.
ELECTRIC_PERFORMANCE_SM = 1
ELECTRIC_PERFORMANCE_PPM = 2
ELECTRIC_PERFORMANCE_BESS = 3

# --- Model Validation Types ---
# Numerical identifiers for model validation sub-types.
MODEL_VALIDATION_PPM = 11
MODEL_VALIDATION_BESS = 12

# --- File and Naming Conventions ---
# Standard report file name.
REPORT_NAME = "report.tex"
# Separator used for distinguishing different cases or identifiers.
CASE_SEPARATOR = "."
