#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import logging

import pytest

from dycov.logging.simulation_logger import SimulationLogger


class TestSimulationLogger:
    def test_simulation_logger_initializes_with_debug_level(self):
        logger = SimulationLogger("test_logger")
        assert logger.level == logging.DEBUG

    def test_init_handlers_adds_rotating_file_handler(self, tmp_path):
        logger = SimulationLogger("test_logger")
        log_dir = tmp_path
        file_log_level = 10
        file_formatter = "%(asctime)s - %(levelname)s - %(message)s"
        file_max_bytes = 1024

        logger.init_handlers(
            file_log_level=file_log_level,
            file_formatter=file_formatter,
            file_max_bytes=file_max_bytes,
            log_dir=log_dir,
        )

        handlers = logger.handlers
        assert len(handlers) == 1
        handler = handlers[0]
        assert isinstance(handler, logging.handlers.RotatingFileHandler)
        assert handler.level == logging.getLevelName(file_log_level)
        assert handler.formatter._fmt == file_formatter
        assert handler.maxBytes == file_max_bytes
        log_file = log_dir / "dycov.log"
        assert handler.baseFilename == str(log_file)

    def test_close_handlers_removes_and_closes_all_handlers(self, tmp_path):
        logger = SimulationLogger("test_logger")
        log_dir = tmp_path
        logger.init_handlers(
            file_log_level=10,
            file_formatter="%(message)s",
            file_max_bytes=1024,
            log_dir=log_dir,
        )
        assert len(logger.handlers) == 1
        logger.close_handlers()
        assert len(logger.handlers) == 0

    def test_init_handlers_nonexistent_log_dir_raises_exception(self, tmp_path):
        logger = SimulationLogger("test_logger")
        non_existent_dir = tmp_path / "does_not_exist"
        file_log_level = 10
        file_formatter = "%(message)s"
        file_max_bytes = 1024

        with pytest.raises(FileNotFoundError):
            logger.init_handlers(
                file_log_level=file_log_level,
                file_formatter=file_formatter,
                file_max_bytes=file_max_bytes,
                log_dir=non_existent_dir,
            )

    def test_init_handlers_invalid_log_level_raises_error(self, tmp_path):
        logger = SimulationLogger("test_logger")
        log_dir = tmp_path
        invalid_log_level = 999  # Invalid log level (not a valid logging level)
        file_formatter = "%(message)s"
        file_max_bytes = 1024

        with pytest.raises(ValueError):
            logger.init_handlers(
                file_log_level=invalid_log_level,
                file_formatter=file_formatter,
                file_max_bytes=file_max_bytes,
                log_dir=log_dir,
            )

    def test_close_handlers_no_handlers_attached(self):
        logger = SimulationLogger("test_logger")
        # Should not raise any exception
        logger.close_handlers()
