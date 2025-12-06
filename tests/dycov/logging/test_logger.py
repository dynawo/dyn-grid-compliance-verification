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
import shutil
import tempfile
from pathlib import Path

import pytest

from dycov.logging.custom_formatter import CustomFormatter
from dycov.logging.logger import DycovLogger


class TestDycovLogger:
    @pytest.mark.skip
    def test_logger_initializes_with_console_and_file_handlers(self):
        logger = DycovLogger("test_logger")
        with tempfile.TemporaryDirectory() as tmpdirname:
            log_dir = Path(tmpdirname)
            logger.init_handlers(
                file_log_level=logging.INFO,
                file_formatter="%(levelname)s:%(message)s",
                file_max_bytes=1024,
                console_log_level=logging.INFO,
                console_formatter="%(levelname)s:%(message)s",
                log_dir=log_dir,
            )
            assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
            assert any(
                isinstance(h, logging.handlers.RotatingFileHandler) for h in logger.handlers
            )
            # Check formatters
            stream_handler = next(
                h for h in logger.handlers if isinstance(h, logging.StreamHandler)
            )
            file_handler = next(
                h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)
            )
            assert isinstance(stream_handler.formatter, CustomFormatter)
            assert isinstance(file_handler.formatter, logging.Formatter)

    def test_child_logger_inherits_log_level(self):
        logger = DycovLogger("parent_logger")
        logger.setLevel(logging.WARNING)
        child_logger = logger.get_logger("child")
        assert child_logger.getEffectiveLevel() == logger.getEffectiveLevel()
        assert child_logger.getEffectiveLevel() == logging.WARNING

    @pytest.mark.skip
    def test_console_output_uses_custom_formatter_with_colorama(self):
        logger = DycovLogger("colorama_logger")
        with tempfile.TemporaryDirectory() as tmpdirname:
            log_dir = Path(tmpdirname)
            logger.init_handlers(
                file_log_level=logging.INFO,
                file_formatter="%(levelname)s:%(message)s",
                file_max_bytes=1024,
                console_log_level=logging.INFO,
                console_formatter="%(levelname)s:%(message)s",
                log_dir=log_dir,
            )
            stream_handler = next(
                h for h in logger.handlers if isinstance(h, logging.StreamHandler)
            )
            # Should use CustomFormatter if colorama is available
            assert isinstance(stream_handler.formatter, CustomFormatter)

    def test_disable_file_handler(self):
        logger = DycovLogger("no_file_logger")
        with tempfile.TemporaryDirectory() as tmpdirname:
            log_dir = Path(tmpdirname)
            logger.init_handlers(
                file_log_level=logging.INFO,
                file_formatter="%(levelname)s:%(message)s",
                file_max_bytes=1024,
                console_log_level=logging.INFO,
                console_formatter="%(levelname)s:%(message)s",
                log_dir=log_dir,
                disable_file=True,
            )
            assert not any(
                isinstance(h, logging.handlers.RotatingFileHandler) for h in logger.handlers
            )

    def test_file_handler_with_invalid_log_dir(self):
        logger = DycovLogger("invalid_dir_logger")
        invalid_dir = Path("/nonexistent_dir_for_dycov_logger_test")
        # Remove the directory if it exists (shouldn't, but just in case)
        if invalid_dir.exists():
            shutil.rmtree(invalid_dir)
        with pytest.raises(Exception):
            logger.init_handlers(
                file_log_level=logging.INFO,
                file_formatter="%(levelname)s:%(message)s",
                file_max_bytes=1024,
                console_log_level=logging.INFO,
                console_formatter="%(levelname)s:%(message)s",
                log_dir=invalid_dir,
            )
