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
from dycov.validation import compared_curves


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
    prefix = compared_curves.threshold_of(measurement_name)
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
    prefix = compared_curves.threshold_of(measurement_name)
    if prefix is None:
        return {
            "before": {"mxe": None, "me": None, "mae": None},
            "during": {"mxe": None, "me": None, "mae": None},
            "after": {"mxe": None, "me": None, "mae": None},
        }

    return _get_window_threshold_values_for_test(prefix)


def get_setpoint_tracking_threshold_values(thresholds_family: str = "") -> dict:
    """
    Get the setpoint tracking threshold values used for electrical performance
    verification against reference setpoints.

    The maximum permissible errors on the quantity tracked, in pu (base setpoint variation
    level), are a family of ``thr_<family>_reftrack_*`` keys of the [GridCode] section, named
    by the ``setpoint_tracking_thresholds`` key of the PCS. Without one, the DTR Fiche I16
    table applies, whatever the nature of the reference signals:
    | window | quantity tracked   |
    |--------|------|------|------|
    |        | MXE  | ME   | MAE  |
    | Before | 0.05 | 0.02 | 0.03 |
    | During | 0.08 | 0.05 | 0.07 |
    | After  | 0.05 | 0.02 | 0.03 |

    The ``FT`` family is the table of the DTR Fiche F16, whose reference signals are on-site
    measurements:
    | window | quantity tracked   |
    |--------|------|------|------|
    |        | MXE  | ME   | MAE  |
    | Before | 0.05 | 0.03 | 0.04 |
    | During | 0.10 | 0.05 | 0.07 |
    | After  | 0.05 | 0.03 | 0.04 |

    Parameters
    ----------
    thresholds_family: str
        Family of the thresholds the PCS applies ("" for the I16 table, "FT" for the F16 one).

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
    defaults = _SETPOINT_TRACKING_DEFAULTS.get(thresholds_family, _SETPOINT_TRACKING_DEFAULTS[""])
    prefix = "thr_" + (f"{thresholds_family}_" if thresholds_family else "") + "reftrack"
    return {
        window: {
            error: config.get_float("GridCode", f"{prefix}_{error}_{window}", default)
            for error, default in errors.items()
        }
        for window, errors in defaults.items()
    }


_SETPOINT_TRACKING_DEFAULTS = {
    "": {
        "before": {"mxe": 0.05, "me": 0.02, "mae": 0.03},
        "during": {"mxe": 0.08, "me": 0.05, "mae": 0.07},
        "after": {"mxe": 0.05, "me": 0.02, "mae": 0.03},
    },
    "FT": {
        "before": {"mxe": 0.05, "me": 0.03, "mae": 0.04},
        "during": {"mxe": 0.10, "me": 0.05, "mae": 0.07},
        "after": {"mxe": 0.05, "me": 0.03, "mae": 0.04},
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
