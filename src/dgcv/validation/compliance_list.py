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


def append(
    target: list,
    benchmark: str,
    validation_type: str,
    compliance_test: str,
    subtests: list = None,
) -> None:
    """Check if any key is contained in list of elements.

    Parameters
    ----------
    target: list
       List where the new elements will be added
    benchmark: str
       Current benchmark
    validation_type: str
       Validation type, supported values "Performance-Validations" or "Model-Validations"
    compliance_test: str
       Name of the compliance test defined in the configuration file
    subtests: list
       Subtests that make up the compliance test. None otherwise.
    """
    if benchmark in config.get_list(validation_type, compliance_test):
        if subtests:
            target += subtests
        else:
            target.append(compliance_test)


def contains_key(keys: list, elements: list) -> bool:
    """Check if any key is contained in list of elements.

    Parameters
    ----------
    keys: list
       Keys to look for
    elements: list
       Items to search for the key

    Returns
    -------
    bool
        True if any key is contained in the list of elements, False otherwise
    """
    for key in keys:
        if key in elements:
            return True

    return False
