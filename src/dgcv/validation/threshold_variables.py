#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from dgcv.configuration.cfg import config


def _get_voltage_dip_threshold_values_for_simulation(measurement_name: str) -> dict:
    if measurement_name == "BusPDR_BUS_ActivePower":
        window = {
            "before": {
                "mxe": config.get_float("GridCode", "thr_P_mxe_before", 0.05),
                "me": config.get_float("GridCode", "thr_P_me_before", 0.02),
                "mae": config.get_float("GridCode", "thr_P_mae_before", 0.03),
            },
            "during": {
                "mxe": config.get_float("GridCode", "thr_P_mxe_during", 0.08),
                "me": config.get_float("GridCode", "thr_P_me_during", 0.05),
                "mae": config.get_float("GridCode", "thr_P_mae_during", 0.07),
            },
            "after": {
                "mxe": config.get_float("GridCode", "thr_P_mxe_after", 0.05),
                "me": config.get_float("GridCode", "thr_P_me_after", 0.02),
                "mae": config.get_float("GridCode", "thr_P_mae_after", 0.03),
            },
        }
    elif measurement_name == "BusPDR_BUS_ReactivePower":
        window = {
            "before": {
                "mxe": config.get_float("GridCode", "thr_Q_mxe_before", 0.05),
                "me": config.get_float("GridCode", "thr_Q_me_before", 0.02),
                "mae": config.get_float("GridCode", "thr_Q_mae_before", 0.03),
            },
            "during": {
                "mxe": config.get_float("GridCode", "thr_Q_mxe_during", 0.08),
                "me": config.get_float("GridCode", "thr_Q_me_during", 0.05),
                "mae": config.get_float("GridCode", "thr_Q_mae_during", 0.07),
            },
            "after": {
                "mxe": config.get_float("GridCode", "thr_Q_mxe_after", 0.05),
                "me": config.get_float("GridCode", "thr_Q_me_after", 0.02),
                "mae": config.get_float("GridCode", "thr_Q_mae_after", 0.03),
            },
        }
    elif measurement_name == "BusPDR_BUS_ActiveCurrent":
        window = {
            "before": {
                "mxe": config.get_float("GridCode", "thr_Ip_mxe_before", 0.05),
                "me": config.get_float("GridCode", "thr_Ip_me_before", 0.02),
                "mae": config.get_float("GridCode", "thr_Ip_mae_before", 0.03),
            },
            "during": {
                "mxe": config.get_float("GridCode", "thr_Ip_mxe_during", 0.08),
                "me": config.get_float("GridCode", "thr_Ip_me_during", 0.05),
                "mae": config.get_float("GridCode", "thr_Ip_mae_during", 0.07),
            },
            "after": {
                "mxe": config.get_float("GridCode", "thr_Ip_mxe_after", 0.05),
                "me": config.get_float("GridCode", "thr_Ip_me_after", 0.02),
                "mae": config.get_float("GridCode", "thr_Ip_mae_after", 0.03),
            },
        }
    elif measurement_name == "BusPDR_BUS_ReactiveCurrent":
        window = {
            "before": {
                "mxe": config.get_float("GridCode", "thr_Iq_mxe_before", 0.05),
                "me": config.get_float("GridCode", "thr_Iq_me_before", 0.02),
                "mae": config.get_float("GridCode", "thr_Iq_mae_before", 0.03),
            },
            "during": {
                "mxe": config.get_float("GridCode", "thr_Iq_mxe_during", 0.08),
                "me": config.get_float("GridCode", "thr_Iq_me_during", 0.05),
                "mae": config.get_float("GridCode", "thr_Iq_mae_during", 0.07),
            },
            "after": {
                "mxe": config.get_float("GridCode", "thr_Iq_mxe_after", 0.05),
                "me": config.get_float("GridCode", "thr_Iq_me_after", 0.02),
                "mae": config.get_float("GridCode", "thr_Iq_mae_after", 0.03),
            },
        }
    else:
        window = {
            "before": {"mxe": None, "me": None, "mae": None},
            "during": {"mxe": None, "me": None, "mae": None},
            "after": {"mxe": None, "me": None, "mae": None},
        }

    return window


def _get_voltage_dip_threshold_values_for_test(measurement_name) -> dict:
    if measurement_name == "BusPDR_BUS_ActivePower":
        window = {
            "before": {
                "mxe": config.get_float("GridCode", "thr_FT_P_mxe_before", 0.08),
                "me": config.get_float("GridCode", "thr_FT_P_me_before", 0.04),
                "mae": config.get_float("GridCode", "thr_FT_P_mae_before", 0.07),
            },
            "during": {
                "mxe": config.get_float("GridCode", "thr_FT_P_mxe_during", 0.10),
                "me": config.get_float("GridCode", "thr_FT_P_me_during", 0.05),
                "mae": config.get_float("GridCode", "thr_FT_P_mae_during", 0.08),
            },
            "after": {
                "mxe": config.get_float("GridCode", "thr_FT_P_mxe_after", 0.08),
                "me": config.get_float("GridCode", "thr_FT_P_me_after", 0.04),
                "mae": config.get_float("GridCode", "thr_FT_P_mae_after", 0.07),
            },
        }
    elif measurement_name == "BusPDR_BUS_ReactivePower":
        window = {
            "before": {
                "mxe": config.get_float("GridCode", "thr_FT_Q_mxe_before", 0.08),
                "me": config.get_float("GridCode", "thr_FT_Q_me_before", 0.04),
                "mae": config.get_float("GridCode", "thr_FT_Q_mae_before", 0.07),
            },
            "during": {
                "mxe": config.get_float("GridCode", "thr_FT_Q_mxe_during", 0.10),
                "me": config.get_float("GridCode", "thr_FT_Q_me_during", 0.05),
                "mae": config.get_float("GridCode", "thr_FT_Q_mae_during", 0.08),
            },
            "after": {
                "mxe": config.get_float("GridCode", "thr_FT_Q_mxe_after", 0.08),
                "me": config.get_float("GridCode", "thr_FT_Q_me_after", 0.04),
                "mae": config.get_float("GridCode", "thr_FT_Q_mae_after", 0.07),
            },
        }
    elif measurement_name == "BusPDR_BUS_ActiveCurrent":
        window = {
            "before": {
                "mxe": config.get_float("GridCode", "thr_FT_Ip_mxe_before", 0.08),
                "me": config.get_float("GridCode", "thr_FT_Ip_me_before", 0.04),
                "mae": config.get_float("GridCode", "thr_FT_Ip_mae_before", 0.07),
            },
            "during": {
                "mxe": config.get_float("GridCode", "thr_FT_Ip_mxe_during", 0.10),
                "me": config.get_float("GridCode", "thr_FT_Ip_me_during", 0.05),
                "mae": config.get_float("GridCode", "thr_FT_Ip_mae_during", 0.08),
            },
            "after": {
                "mxe": config.get_float("GridCode", "thr_FT_Ip_mxe_after", 0.08),
                "me": config.get_float("GridCode", "thr_FT_Ip_me_after", 0.04),
                "mae": config.get_float("GridCode", "thr_FT_Ip_mae_after", 0.07),
            },
        }
    elif measurement_name == "BusPDR_BUS_ReactiveCurrent":
        window = {
            "before": {
                "mxe": config.get_float("GridCode", "thr_FT_Iq_mxe_before", 0.08),
                "me": config.get_float("GridCode", "thr_FT_Iq_me_before", 0.04),
                "mae": config.get_float("GridCode", "thr_FT_Iq_mae_before", 0.07),
            },
            "during": {
                "mxe": config.get_float("GridCode", "thr_FT_Iq_mxe_during", 0.10),
                "me": config.get_float("GridCode", "thr_FT_Iq_me_during", 0.05),
                "mae": config.get_float("GridCode", "thr_FT_Iq_mae_during", 0.08),
            },
            "after": {
                "mxe": config.get_float("GridCode", "thr_FT_Iq_mxe_after", 0.08),
                "me": config.get_float("GridCode", "thr_FT_Iq_me_after", 0.04),
                "mae": config.get_float("GridCode", "thr_FT_Iq_mae_after", 0.07),
            },
        }
    else:
        window = {
            "before": {"mxe": None, "me": None, "mae": None},
            "during": {"mxe": None, "me": None, "mae": None},
            "after": {"mxe": None, "me": None, "mae": None},
        }

    return window


def get_setpoint_tracking_threshold_values() -> dict:
    """
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
        Thresholds apply for errors between simulation and reference signals

    """
    window = {
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
    return window


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
        Measurement curve name.
    is_field_measurements: bool
        True if the reference signals are field measurements.

    Returns
    -------
    dict
        Thresholds apply for errors between simulation and reference signals
    """
    if is_field_measurements:
        return _get_voltage_dip_threshold_values_for_test(measurement_name)

    return _get_voltage_dip_threshold_values_for_simulation(measurement_name)
