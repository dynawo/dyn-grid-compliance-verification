#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import configparser
import re
from pathlib import Path
from dycov.model.producer import Producer


class GFMProducer(Producer):
    """Represents a producer parsed from an INI configuration file."""

    def __init__(self, producer_ini: Path) -> None:
        """Initializes the GFMProducer with the given configuration file.

        Args:
            producer_ini (Path): The file path to the producer's INI configuration.
        """
        super().__init__(None, producer_ini)
        self._config = self.__read_producer_ini()

    def get_producer_path(self) -> Path:
        """Retrieves the absolute path to the producer's INI file.

        Returns:
            Path: The absolute path to the INI file.
        """
        return self._producer_ini_path

    def get_filenames(self, zone: int = 0) -> list[str]:
        """Returns a list of INI filenames found in the producer's directory.

        Args:
            zone (int, optional): The network zone identifier. Defaults to 0.

        Returns:
            list[str]: A sorted list of configuration filename stems.
        """
        pattern = re.compile(r".*\.[iI][nN][iI]")
        return sorted(
            [
                file.stem
                for file in self._producer_ini_path.resolve().iterdir()
                if pattern.match(str(file))
            ]
        )

    def get_sim_type_str(self) -> str:
        """Retrieves the simulation type identifier.

        Returns:
            str: The simulation string identifier (e.g., "gfm").
        """
        return "gfm"

    def set_zone(self, zone: int, filename: str) -> None:
        """Sets the active zone and filename.

        Args:
            zone (int): The zone identifier.
            filename (str): The name of the file to associate.
        """
        pass

    def get_config(self) -> configparser.ConfigParser:
        """Retrieves the parsed configuration object.

        Returns:
            configparser.ConfigParser: The loaded configuration parser instance.
        """
        return self._config

    def __read_producer_ini(self) -> configparser.ConfigParser:
        """Locates and parses the producer's INI configuration file.

        Returns:
            configparser.ConfigParser: The populated configuration parser.

        Raises:
            FileNotFoundError: If the INI file cannot be located in the directory.
        """

        def __get_producer_ini(path: Path, pattern: re.Pattern) -> Path:
            for file in path.resolve().iterdir():
                if pattern.match(str(file)):
                    return path.resolve() / file
            raise FileNotFoundError("Producer INI file not found.")

        pattern_ini = re.compile(r".*\.[iI][nN][iI]")
        producer_ini_path = __get_producer_ini(self.get_producer_path(), pattern_ini)
        producer_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        producer_config.read(producer_ini_path)
        return producer_config
