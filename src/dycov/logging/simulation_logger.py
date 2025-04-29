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
from logging.handlers import RotatingFileHandler
from pathlib import Path


class SimulationLogger(logging.getLoggerClass()):
    def __init__(self, name: str) -> None:
        super(SimulationLogger, self).__init__(name)
        self.setLevel(logging.DEBUG)

    def init_handlers(
        self,
        file_log_level: str,
        file_formatter: str,
        file_max_bytes: int,
        log_dir: Path,
    ) -> None:

        self.setLevel(file_log_level)

        log_name = "dycov.log"
        log_file = log_dir / log_name
        file_handler = RotatingFileHandler(
            log_file, mode="a", maxBytes=file_max_bytes, backupCount=5, encoding=None, delay=0
        )
        file_handler.setLevel(file_log_level)

        file_handler.setFormatter(logging.Formatter(file_formatter))
        self.addHandler(file_handler)

    def close_handlers(self):
        for handler in self.handlers:
            self.removeHandler(handler)
            handler.close()
