#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

import configparser
import re
from pathlib import Path

from dycov.model.producer import Producer


class GFMProducer(Producer):
    """Represents a producer parsed from an INI configuration file.

    Extends the base Producer class to handle GFM specific calculations.
    """

    def __init__(self, producer_ini: Path) -> None:
        """Initializes the GFMProducer with the INI file path.

        Parameters
        ----------
        producer_ini : Path
            Path pointing to the producer INI file.
        """
        super().__init__(None, producer_ini)
        self._config = self.__read_producer_ini()

    def get_producer_path(self) -> Path:
        """Retrieves the base path to the producer INI file.

        Returns
        -------
        Path
            Resolved path to the producer INI.
        """
        return self._producer_ini_path

    def get_filenames(self, zone: int = 0) -> list[str]:
        """Retrieves filenames associated with the producer model.

        Parameters
        ----------
        zone : int, optional
            Zone identifier used for model validation.

        Returns
        -------
        list[str]
            Sorted list of INI filenames (stems).
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
        """Retrieves the validation type identifier.

        Returns
        -------
        str
            Static string 'gfm'.
        """
        return "gfm"

    def set_zone(self, zone: int, filename: str) -> None:
        """Dummy method to satisfy interface requirements.

        Parameters
        ----------
        zone : int
            Zone identifier.
        filename : str
            Name of the file.
        """
        pass

    def get_config(self) -> configparser.ConfigParser:
        """Retrieves the loaded producer settings.

        Returns
        -------
        configparser.ConfigParser
            Parsed configuration object.
        """
        return self._config

    def __read_producer_ini(self) -> configparser.ConfigParser:
        """Reads and parses the producer INI file.

        Returns
        -------
        configparser.ConfigParser
            Parsed configuration object.

        Raises
        ------
        FileNotFoundError
            If no valid INI file is found.
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
