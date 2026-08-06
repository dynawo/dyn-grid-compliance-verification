#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
import re
from pathlib import Path
from dycov.model.producer import Producer


class GFMProducer(Producer):
    """
    A class used to represent a producer parsed from an INI configuration file.
    This class extends the base Producer class, providing specific methods to
    locate, read, and access producer-related data required for Grid Forming (GFM)
    calculations.
    """

    def __init__(self, producer_ini: Path) -> None:
        """Initializes the GFMProducer with the path to the producer INI file."""
        super().__init__(None, producer_ini)
        self._config = self.__read_producer_ini()

    def get_producer_path(self) -> Path:
        return self._producer_ini_path

    def get_filenames(self, zone: int = 0) -> list[str]:
        # Filter files ending in .ini (case-insensitive)
        pattern = re.compile(r".*\.[iI][nN][iI]")
        return sorted(
            [
                file.stem
                for file in self._producer_ini_path.resolve().iterdir()
                if pattern.match(str(file))
            ]
        )

    def get_sim_type_str(self) -> str:
        return "gfm"

    def set_zone(self, zone: int, filename: str) -> None:
        pass

    def get_config(self) -> configparser.ConfigParser:
        return self._config

    def __read_producer_ini(self) -> configparser.ConfigParser:
        def __get_producer_ini(path: Path, pattern: re.Pattern) -> Path:
            # Recursively find the first configuration file matching the pattern
            for file in path.resolve().iterdir():
                if pattern.match(str(file)):
                    return path.resolve() / file
            raise FileNotFoundError("Producer INI file not found.")

        pattern_ini = re.compile(r".*\.[iI][nN][iI]")
        producer_ini_path = __get_producer_ini(self.get_producer_path(), pattern_ini)

        # Force ConfigParser to treat '#' strictly as comments, not data
        producer_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        producer_config.read(producer_ini_path)
        return producer_config
