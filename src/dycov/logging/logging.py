#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import logging

from dycov.logging.logger import DycovLogger


def _get_instance() -> DycovLogger:
    logging.setLoggerClass(DycovLogger)
    return logging.getLogger("DyCoV")


dycov_logging = _get_instance()
