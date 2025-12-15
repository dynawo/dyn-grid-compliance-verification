#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

"""
Central repository for simulation constants and magic numbers.
"""

# General Simulation Parameters
SIMULATION_START_TIME_DEFAULT = 0.0
SIMULATION_START_TIME_EXTENDED = -1.0  # For RoCoF and SCRJump
SIMULATION_END_TIME = 5.0
SIMULATION_POINTS = 3000
SIMULATION_EVENT_TIME = 0.0

# Delay and Time Constants
EMT_FINAL_DELAY_S = 0.02
SCR_BOUND_DELAY_S = 0.01
OVERDAMPED_MAX_DELAY_S = 0.01
UNDERDAMPED_MIN_DELAY_S = 0.01
UNDERDAMPED_MAX_DELAY_S = 0.01
SCRJUMP_INITIAL_LIMITING_S = 0.1
SCRJUMP_MODIFY_ENVELOPE_S = 0.03

# Time Tunnel Calculation Parameters
TIME_TUNNEL_START_OFFSET = 0.02
TIME_TUNNEL_EXP_TAU = 0.3
