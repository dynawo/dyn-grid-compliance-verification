#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
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
    """
    A class used to represent a producer from an INI file.

    This class extends the Producer class and provides methods to
    access producer-related data stored in an INI file.
    """

    def __init__(self, producer_ini: Path) -> None:
        """
        Initializes the GFMProducer with the path to the producer INI file.

        Parameters
        ----------
        producer_ini : Path
            The path to the producer INI file.
        """
        super().__init__(None, producer_ini)
        self._config = self.__read_producer_ini()

    def get_producer_path(self) -> Path:
        """
        Get the path to the producer INI file.

        Returns
        -------
        Path
            The path to the producer INI file.
        """
        return self._producer_ini_path

    def get_filenames(self, zone: int = 0) -> list[str]:
        """
        Get the filenames of the producer model.

        Parameters
        ----------
        zone : int, optional
            Zone to test, only applies to model validation. Defaults to 0.

        Returns
        -------
        list[str]
            List of filenames (stems).
        """
        pattern = re.compile(r".*.[iI][nN][iI]")
        return sorted(
            [
                file.stem
                for file in self._producer_ini_path.resolve().iterdir()
                if pattern.match(str(file))
            ]
        )

    def get_sim_type_str(self) -> str:
        """
        Gets a string according to the type of validation being executed.

        Returns
        -------
        str
            'gfm'
        """
        return "gfm"

    def set_zone(self, zone: int, filename: str) -> None:
        """
        Dummy
        """
        pass

    def get_config(self) -> configparser.ConfigParser:
        """
        Gets the producer settings for the GFM calculations.

        Returns
        -------
        configparser.ConfigParser
            The parsed configuration object containing producer settings.
        """
        return self._config

    def __read_producer_ini(self) -> configparser.ConfigParser:
        """
        Reads and parses the producer INI file.

        Returns
        -------
        configparser.ConfigParser
            The parsed configuration object.
        """

        def __get_producer_ini(path: Path, pattern: re.Pattern) -> Path:
            """
            Helper function to get the producer INI file path.

            Parameters
            ----------
            path : Path
                The directory path to search in.
            pattern : re.Pattern
                The regex pattern to match the filename.

            Returns
            -------
            Path
                The full path to the producer INI file.
            """
            for file in path.resolve().iterdir():
                if pattern.match(str(file)):
                    return path.resolve() / file
            raise FileNotFoundError("Producer INI file not found.")

        pattern_ini = re.compile(r".*.[iI][nN][iI]")
        producer_ini_path = __get_producer_ini(self.get_producer_path(), pattern_ini)

        producer_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        producer_config.read(producer_ini_path)
        return producer_config
