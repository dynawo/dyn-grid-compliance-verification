#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

"""Central repository for simulation constants and magic numbers."""

# General Simulation Parameters
SIMULATION_START_TIME_DEFAULT = 0.0
SIMULATION_START_TIME_EXTENDED = -1.0
SIMULATION_END_TIME = 5.0
SIMULATION_POINTS = 3000
SIMULATION_EVENT_TIME = 0.0

# Delay and Time Constants (in seconds)
EMT_DELAY_S = 0.02
SCR_BOUND_DELAY_S = 0.01

# Phase jump model and envelopes
PHASE_JUMP_PLL_TIME_CONSTANT_S = 0.01
PHASE_JUMP_REDUCED_RESPONSE_DELAY_S = 0.01
PHASE_JUMP_DECAY_THRESHOLD = 0.05
PHASE_JUMP_DECAY_TIME_CONSTANTS = 3
# Extrema below this fraction of the largest one are the rounding noise of the simulation
PHASE_JUMP_NOISE_FLOOR = 1e-12
ANGLE_DAMPING_PER_DAMPING = 0.1656
ANGLE_DAMPING_OFFSET = 2.0022

# Limits and modifiers for SCRJump
SCRJUMP_INITIAL_LIMITING_S = 0.1
SCRJUMP_MODIFY_ENVELOPE_S = 0.03

# Time Tunnel Calculation Parameters
TIME_TUNNEL_START_OFFSET = 0.02
TIME_TUNNEL_EXP_TAU = 0.3
