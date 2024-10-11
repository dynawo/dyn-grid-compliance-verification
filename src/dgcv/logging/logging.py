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

from dgcv.logging.logger import DgcvLogger


def _get_instance() -> DgcvLogger:
    logging.setLoggerClass(DgcvLogger)
    return logging.getLogger("DGCV")


dgcv_logging = _get_instance()
