#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The process-wide logger of DyCoV and the handlers it is given."""

import logging
import shutil
import tempfile
from pathlib import Path

import pytest

from dycov.logging.custom_formatter import CustomFormatter
from dycov.logging.logger import DycovLogger


@pytest.fixture
def registered_logger():
    """Registering a logger mutates the process-wide manager, so undo it afterwards to keep
    these level changes from leaking into other tests."""
    created = []

    def _register(name: str) -> DycovLogger:
        created.append(name)
        return logging.getLogger(name)

    yield _register

    for name in created:
        leaked = [
            entry
            for entry in logging.Logger.manager.loggerDict
            if entry == name or entry.startswith(f"{name}.")
        ]
        for entry in leaked:
            logger = logging.Logger.manager.loggerDict.pop(entry)
            for handler in getattr(logger, "handlers", []):
                handler.close()


class TestDycovLogger:
    def test_unconfigured_logger_inherits_level(self, registered_logger):
        logger = registered_logger("third_party_logger")

        assert isinstance(logger, DycovLogger)
        assert logger.level == logging.NOTSET

    def test_logger_initializes_with_console_and_file_handlers(self, tmp_path):
        logger = DycovLogger("test_logger")

        logger.init_handlers(
            file_log_level=logging.INFO,
            file_formatter="%(levelname)s:%(message)s",
            file_max_bytes=1024,
            console_log_level=logging.INFO,
            console_formatter="%(levelname)s:%(message)s",
            log_dir=tmp_path,
        )
        handlers = list(logger.handlers)
        for handler in handlers:
            logger.removeHandler(handler)
            handler.close()

        [console] = [h for h in handlers if type(h) is logging.StreamHandler]
        [log_file] = [h for h in handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert isinstance(console.formatter, CustomFormatter)
        assert type(log_file.formatter) is logging.Formatter

    def test_child_logger_inherits_log_level(self, registered_logger):
        logger = registered_logger("parent_logger")
        logger.setLevel(logging.DEBUG)

        child_logger = logger.get_logger("child")

        assert child_logger.getEffectiveLevel() == logging.DEBUG

    def test_child_logger_follows_level_set_after_its_creation(self, registered_logger, tmp_path):
        logger = registered_logger("early_child_logger")
        child_logger = logger.get_logger("Early")

        logger.init_handlers(
            file_log_level=logging.DEBUG,
            file_formatter="%(levelname)s:%(message)s",
            file_max_bytes=1024,
            console_log_level=logging.DEBUG,
            console_formatter="%(levelname)s:%(message)s",
            log_dir=tmp_path,
            disable_console=True,
        )

        assert child_logger.isEnabledFor(logging.DEBUG)

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
