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
    A class used to represent a producer parsed from an INI configuration file.

    This class extends the base Producer class, providing specific methods to
    locate, read, and access producer-related data required for Grid Forming (GFM)
    calculations.
    """

    def __init__(self, producer_ini: Path) -> None:
        """Initializes the GFMProducer with the path to the producer INI file.

        Parameters
        ----------
        producer_ini : Path
            The absolute or relative path pointing to the producer INI file.
        """
        super().__init__(None, producer_ini)
        self._config = self.__read_producer_ini()

    def get_producer_path(self) -> Path:
        """
        Retrieves the base path to the producer INI file.

        Returns
        -------
        Path
            The resolved path to the directory or file representing the producer INI.
        """
        return self._producer_ini_path

    def get_filenames(self, zone: int = 0) -> list[str]:
        """
        Retrieves the filenames associated with the producer model.

        This method scans the producer path for INI files and returns a sorted
        list of their stem names (filenames without extensions).

        Parameters
        ----------
        zone : int, optional
            The zone identifier to test, primarily used for model validation.
            Defaults to 0.

        Returns
        -------
        list[str]
            A sorted list of filenames (stems) corresponding to the INI files found.
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
        Retrieves a string identifier representing the type of validation being executed.

        Returns
        -------
        str
            A static string literal 'gfm'.
        """
        return "gfm"

    def set_zone(self, zone: int, filename: str) -> None:
        """
        Dummy method to satisfy interface requirements.

        Parameters
        ----------
        zone : int
            The zone identifier.
        filename : str
            The name of the file.
        """
        pass

    def get_config(self) -> configparser.ConfigParser:
        """
        Retrieves the loaded producer settings required for GFM calculations.

        Returns
        -------
        configparser.ConfigParser
            The parsed configuration object containing all producer settings.
        """
        return self._config

    def __read_producer_ini(self) -> configparser.ConfigParser:
        """
        Reads and parses the producer INI file.

        This private method handles the internal logic of locating the INI file
        matching the specific pattern and loading it into a ConfigParser object.

        Returns
        -------
        configparser.ConfigParser
            The parsed configuration object ready for attribute retrieval.

        Raises
        ------
        FileNotFoundError
            If no file matching the INI pattern is found within the specified path.
        """

        def __get_producer_ini(path: Path, pattern: re.Pattern) -> Path:
            """
            Helper function to locate the producer INI file path.

            Parameters
            ----------
            path : Path
                The directory path to search within.
            pattern : re.Pattern
                The compiled regular expression pattern used to match the filename.

            Returns
            -------
            Path
                The full resolved path to the located producer INI file.
            """
            for file in path.resolve().iterdir():
                if pattern.match(str(file)):
                    return path.resolve() / file
            raise FileNotFoundError("Producer INI file not found.")

        # Compile pattern to match files with .ini or .INI extensions
        pattern_ini = re.compile(r".*.[iI][nN][iI]")
        producer_ini_path = __get_producer_ini(self.get_producer_path(), pattern_ini)

        # Initialize ConfigParser, ensuring '#' is recognized as an inline comment prefix
        producer_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        producer_config.read(producer_ini_path)
        return producer_config
