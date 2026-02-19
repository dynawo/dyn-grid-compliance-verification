#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from dycov.configuration.cfg import config

# Mapping of measurement names to their respective prefixes used in configuration keys.
# This dictionary is used to retrieve the appropriate prefix for a given measurement name.
MEASUREMENT_PREFIX_MAP = {
    "BusPDR_BUS_ActivePower": "P",
    "BusPDR_BUS_ReactivePower": "Q",
    "BusPDR_BUS_ActiveCurrent": "Ip",
    "BusPDR_BUS_ReactiveCurrent": "Iq",
    "InjectedActiveCurrent": "Ip",
    "InjectedReactiveCurrent": "Iq",
}


def _get_window_threshold_values_for_simulation(prefix: str) -> dict:
    return {
        "before": {
            "mxe": config.get_float("GridCode", f"thr_{prefix}_mxe_before", 0.05),
            "me": config.get_float("GridCode", f"thr_{prefix}_me_before", 0.02),
            "mae": config.get_float("GridCode", f"thr_{prefix}_mae_before", 0.03),
        },
        "during": {
            "mxe": config.get_float("GridCode", f"thr_{prefix}_mxe_during", 0.08),
            "me": config.get_float("GridCode", f"thr_{prefix}_me_during", 0.05),
            "mae": config.get_float("GridCode", f"thr_{prefix}_mae_during", 0.07),
        },
        "after": {
            "mxe": config.get_float("GridCode", f"thr_{prefix}_mxe_after", 0.05),
            "me": config.get_float("GridCode", f"thr_{prefix}_me_after", 0.02),
            "mae": config.get_float("GridCode", f"thr_{prefix}_mae_after", 0.03),
        },
    }


def _get_voltage_dip_threshold_values_for_simulation(measurement_name: str) -> dict:
    prefix = MEASUREMENT_PREFIX_MAP.get(measurement_name)
    if prefix is None:
        return {
            "before": {"mxe": None, "me": None, "mae": None},
            "during": {"mxe": None, "me": None, "mae": None},
            "after": {"mxe": None, "me": None, "mae": None},
        }

    return _get_window_threshold_values_for_simulation(prefix)


def _get_window_threshold_values_for_test(prefix: str) -> dict:
    return {
        "before": {
            "mxe": config.get_float("GridCode", f"thr_FT_{prefix}_mxe_before", 0.08),
            "me": config.get_float("GridCode", f"thr_FT_{prefix}_me_before", 0.04),
            "mae": config.get_float("GridCode", f"thr_FT_{prefix}_mae_before", 0.07),
        },
        "during": {
            "mxe": config.get_float("GridCode", f"thr_FT_{prefix}_mxe_during", 0.10),
            "me": config.get_float("GridCode", f"thr_FT_{prefix}_me_during", 0.05),
            "mae": config.get_float("GridCode", f"thr_FT_{prefix}_mae_during", 0.08),
        },
        "after": {
            "mxe": config.get_float("GridCode", f"thr_FT_{prefix}_mxe_after", 0.08),
            "me": config.get_float("GridCode", f"thr_FT_{prefix}_me_after", 0.04),
            "mae": config.get_float("GridCode", f"thr_FT_{prefix}_mae_after", 0.07),
        },
    }


def _get_voltage_dip_threshold_values_for_test(measurement_name: str) -> dict:
    prefix = MEASUREMENT_PREFIX_MAP.get(measurement_name)
    if prefix is None:
        return {
            "before": {"mxe": None, "me": None, "mae": None},
            "during": {"mxe": None, "me": None, "mae": None},
            "after": {"mxe": None, "me": None, "mae": None},
        }

    return _get_window_threshold_values_for_test(prefix)


def get_setpoint_tracking_threshold_values() -> dict:
    """
    Get the setpoint tracking threshold values for different time windows.

    Regardless of the nature of the reference signal, the maximum permissible errors on the
    quantity tracked in pu (base setpoint variation level) are as follow:
    | window | quantity tracked   |
    |--------|------|------|------|
    |        | MXE  | ME   | MAE  |
    | Before | 0.05 | 0.02 | 0.03 |
    | During | 0.08 | 0.05 | 0.07 |
    | After  | 0.05 | 0.02 | 0.03 |

    Returns
    -------
    dict
        A dictionary with three keys: "before", "during", and "after". Each key maps to another
        dictionary with the following structure:
        {
            "mxe": float,  # Maximum absolute error
            "me": float,   # Mean error
            "mae": float   # Mean absolute error
        }
        The values are floats representing the thresholds.

    """
    return {
        "before": {
            "mxe": config.get_float("GridCode", "thr_reftrack_mxe_before", 0.05),
            "me": config.get_float("GridCode", "thr_reftrack_me_before", 0.02),
            "mae": config.get_float("GridCode", "thr_reftrack_mae_before", 0.03),
        },
        "during": {
            "mxe": config.get_float("GridCode", "thr_reftrack_mxe_during", 0.08),
            "me": config.get_float("GridCode", "thr_reftrack_me_during", 0.05),
            "mae": config.get_float("GridCode", "thr_reftrack_mae_during", 0.07),
        },
        "after": {
            "mxe": config.get_float("GridCode", "thr_reftrack_mxe_after", 0.05),
            "me": config.get_float("GridCode", "thr_reftrack_me_after", 0.02),
            "mae": config.get_float("GridCode", "thr_reftrack_mae_after", 0.03),
        },
    }


def get_voltage_dip_threshold_values(measurement_name: str, is_field_measurements: bool) -> dict:
    """
    The following thresholds apply for errors between simulation and reference signals.
    Exclusion windows on transients on insertion (20 ms) and elimination of the fault
    (60 ms) can be applied. For type 3 wind turbines, the producer can request a broader
    exclusion (it is recognized that the behavior of the Crow bar is difficult to represent
    with standard models). In no case will they exceed 140 ms when the fault is inserted
    or 500 ms when the fault is cleared (see IEC 61400-27-2).

    When the reference signals are simulation results, the maximum permissible errors
    in pu (base Sn and In) are as follows:
    | window | active power       | reactive power     | active current     | reactive current    |
    |--------|------|------|------|------|------|------|------|------|------|------|------|-------|
    |        | MXE  | ME   | MAE  | MXE  | ME   | MAE  | MXE  | ME   | MAE  | MXE  | ME   | MAE   |
    | Before | 0.05 | 0.02 | 0.03 | 0.05 | 0.02 | 0.03 | 0.05 | 0.02 | 0.03 | 0.05 | 0.02 | 0.03  |
    | During | 0.08 | 0.05 | 0.07 | 0.08 | 0.05 | 0.07 | 0.08 | 0.05 | 0.07 | 0.08 | 0.05 | 0.07  |
    | After  | 0.05 | 0.02 | 0.03 | 0.05 | 0.02 | 0.03 | 0.05 | 0.02 | 0.03 | 0.05 | 0.02 | 0.03  |

    When the reference signals are test results, the maximum permissible errors in pu
    (base Sn and In) are as follows:

    | window | active power       | reactive power     | active current     | reactive current   |
    |--------|------|------|------|------|------|------|------|------|------|------|------|------|
    |        | MXE  | ME   | MAE  | MXE  | ME   | MAE  | MXE  | ME   | MAE  | MXE  | ME   | MAE  |
    | Before | 0.08 | 0.04 | 0.07 | 0.08 | 0.04 | 0.07 | 0.08 | 0.04 | 0.07 | 0.08 | 0.04 | 0.07 |
    | During | 0.10 | 0.05 | 0.08 | 0.10 | 0.05 | 0.08 | 0.10 | 0.05 | 0.08 | 0.10 | 0.05 | 0.08 |
    | After  | 0.08 | 0.04 | 0.07 | 0.08 | 0.04 | 0.07 | 0.08 | 0.04 | 0.07 | 0.08 | 0.04 | 0.07 |

    Parameters
    ----------
    measurement_name: str
        Measurement curve name. Possible values are:
        - "BusPDR_BUS_ActivePower"
        - "BusPDR_BUS_ReactivePower"
        - "BusPDR_BUS_ActiveCurrent"
        - "BusPDR_BUS_ReactiveCurrent"
    is_field_measurements: bool
        Indicates whether the thresholds are for test results (True) or simulation results (False).

    Returns
    -------
    dict
        A dictionary with three keys: "before", "during", and "after". Each key maps to another
        dictionary with the following structure:
        {
            "mxe": float or None,  # Maximum absolute error
            "me": float or None,   # Mean error
            "mae": float or None   # Mean absolute error
        }
        The values are either floats representing the thresholds or None if the prefix is not
        found.
    """
    return (
        _get_voltage_dip_threshold_values_for_test(measurement_name)
        if is_field_measurements
        else _get_voltage_dip_threshold_values_for_simulation(measurement_name)
    )
