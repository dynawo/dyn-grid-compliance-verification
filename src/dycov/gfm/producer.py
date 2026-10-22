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

# Each kind of producer is given its own tests: the DTR Fiche I18 applies to storage alone
_GENERATOR_TYPES = ("PPM", "BESS")


class GFMProducer(Producer):
    """Represents a producer parsed from an INI configuration file."""

    def __init__(self, producer_ini: Path) -> None:
        """
        Initializes the GFMProducer with the given configuration file.

        Parameters
        ----------
        producer_ini : Path
            The file path to the producer's INI configuration.

        Raises
        ------
        FileNotFoundError
            If the INI file does not exist.
        ValueError
            If the INI file does not declare a supported generator type.
        """
        super().__init__(None, producer_ini)
        self._producer_ini = producer_ini
        self._config = self.__read_producer_ini()
        self._generator_type = self.__read_generator_type()

    def get_producer_path(self) -> Path:
        """
        Retrieves the absolute path to the producer's INI file.

        Returns
        -------
        Path
            The absolute path to the INI file.
        """
        return self._producer_ini_path

    def get_filenames(self, zone: int = 0) -> list[str]:
        """
        Returns the name of the unit, that of its INI file.

        Parameters
        ----------
        zone : int, optional
            The network zone identifier. Defaults to 0.

        Returns
        -------
        list[str]
            The stem of the INI file.
        """
        return [self._producer_ini.stem]

    def get_sim_type_str(self) -> str:
        """
        Retrieves the simulation type identifier.

        Returns
        -------
        str
            The directory of the PCS the producer is given, 'gfm/PPM' or 'gfm/BESS'.
        """
        return f"gfm/{self._generator_type}"

    def set_zone(self, zone: int, filename: str) -> None:
        """
        Sets the active zone and filename.

        Parameters
        ----------
        zone : int
            The zone identifier.
        filename : str
            The name of the file to associate.
        """
        pass

    def get_config(self) -> configparser.ConfigParser:
        """
        Retrieves the parsed configuration object.

        Returns
        -------
        configparser.ConfigParser
            The loaded configuration parser instance.
        """
        return self._config

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

        # Allow inline comments starting with '#' in the INI file
        producer_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        producer_config.read(self._producer_ini)

        return producer_config

    def __read_generator_type(self) -> str:
        """
        Reads the kind of producer the INI file declares.

        Returns
        -------
        str
            One of the supported generator types.

        Raises
        ------
        ValueError
            If the generator type is missing or not supported.
        """
        generator_type = self._config.get("DEFAULT", "generator_type", fallback="").strip()
        if generator_type not in _GENERATOR_TYPES:
            raise ValueError(
                f"The producer INI in '{self.get_producer_path()}' declares generator_type = "
                f"'{generator_type}' in its [DEFAULT] section; it must be one of "
                f"{', '.join(_GENERATOR_TYPES)}, as the Grid Forming tests depend on it"
            )
        return generator_type
