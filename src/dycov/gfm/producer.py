#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

import configparser
from pathlib import Path

from dycov.model.producer import Producer


class GFMProducer(Producer):
    """Represents a producer parsed from an INI configuration file."""

    def __init__(self, producer_ini: Path) -> None:
        """
        Initializes the GFMProducer with the given configuration file.

        Parameters
        ----------
        producer_ini : Path
            The file path to the producer's INI configuration.
        """
        super().__init__(None, producer_ini)
        self._producer_ini = producer_ini
        self._config = self.__read_producer_ini()

    def get_producer_path(self) -> Path:
        """
        Retrieves the directory that holds the producer's INI file.

        Returns
        -------
        Path
            The directory of the INI file.
        """
        return self._producer_ini_path

    def get_filenames(self, zone: int = 0) -> list[str]:
        """
        Returns the name of the producer, the stem of its INI file.

        Parameters
        ----------
        zone : int, optional
            The network zone identifier. Defaults to 0.

        Returns
        -------
        list[str]
            The stem of the producer's INI file, alone.
        """
        return [self._producer_ini.stem]

    def get_sim_type_str(self) -> str:
        """
        Retrieves the simulation type identifier.

        Returns
        -------
        str
            The simulation string identifier (e.g., "gfm").
        """
        return "gfm"

    def set_zone(self, zone: int, filename: str) -> None:
        """
        Does nothing: a GFM producer has no zones.

        Parameters
        ----------
        zone : int
            The zone identifier.
        filename : str
            The name of the file to associate.
        """

    def get_config(self) -> configparser.ConfigParser:
        """
        Retrieves the parsed configuration object.

        Returns
        -------
        configparser.ConfigParser
            The loaded configuration parser instance.
        """
        return self._config

    def get_nominal_frequency(self) -> float:
        """
        Retrieves the nominal frequency of the network.

        Returns
        -------
        float
            The nominal frequency in Hz.
        """
        return self._f_nom

    def __read_producer_ini(self) -> configparser.ConfigParser:
        """
        Parses the producer's INI configuration file.

        Returns
        -------
        configparser.ConfigParser
            The populated configuration parser.

        Raises
        ------
        FileNotFoundError
            If the INI file does not exist.
        """
        if not self._producer_ini.is_file():
            raise FileNotFoundError(f"Producer INI file not found: {self._producer_ini}")

        producer_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        producer_config.read(self._producer_ini)
        return producer_config
