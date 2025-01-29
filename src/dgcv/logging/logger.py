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

import colorama

from dgcv.logging.custom_formatter import CustomFormatter

colorama.init()


class DgcvLogger(logging.getLoggerClass()):
    def __init__(self, name: str) -> None:
        super(DgcvLogger, self).__init__(name)
        self.setLevel(logging.DEBUG)

    def _add_console_handler(
        self,
        console_log_level: str,
        console_formatter: str,
        disable_console: bool = False,
    ) -> None:
        stdout_handler = logging.StreamHandler()
        stdout_handler.setLevel(console_log_level)

        if colorama:
            stdout_handler.setFormatter(CustomFormatter(console_formatter))
        else:
            stdout_handler.setFormatter(logging.Formatter(console_formatter))

        if not disable_console:
            self.addHandler(stdout_handler)

    def _add_file_handler(
        self,
        file_log_level: str,
        file_formatter: str,
        file_max_bytes: int,
        log_dir: Path,
        disable_file: bool = False,
    ) -> None:
        log_name = "dgcv.log"
        log_file = log_dir / log_name
        file_handler = RotatingFileHandler(
            log_file, mode="a", maxBytes=file_max_bytes, backupCount=5, encoding=None, delay=0
        )
        file_handler.setLevel(file_log_level)

        file_handler.setFormatter(logging.Formatter(file_formatter))

        if not disable_file:
            self.addHandler(file_handler)

    def init_handlers(
        self,
        file_log_level: str,
        file_formatter: str,
        file_max_bytes: int,
        console_log_level: str,
        console_formatter: str,
        log_dir: Path,
        disable_console: bool = False,
        disable_file: bool = False,
    ) -> None:

        self.setLevel(console_log_level)
        if file_log_level < console_log_level:
            self.setLevel(file_log_level)

        self._add_console_handler(console_log_level, console_formatter, disable_console)
        self._add_file_handler(
            file_log_level, file_formatter, file_max_bytes, log_dir, disable_file
        )

    def get_logger(self, name: str):
        logger = self.getChild(name)
        logger.setLevel(self.getEffectiveLevel())
        return logger
