#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import configparser
import re
from pathlib import Path
from dycov.model.producer import Producer


class GFMProducer(Producer):
    def __init__(self, producer_ini: Path) -> None:
        """
        Parameters
        ----------
        producer_ini : Path
        """
        super().__init__(None, producer_ini)
        self._config = self.__read_producer_ini()

    def get_producer_path(self) -> Path:
        """
        Returns
        -------
        Path
        """
        return self._producer_ini_path

    def get_filenames(self, zone: int = 0) -> list[str]:
        """
        Parameters
        ----------
        zone : int

        Returns
        -------
        list[str]
        """
        pattern = re.compile(pattern=r".*\.[iI][nN][iI]")
        return sorted(
            [
                file.stem
                for file in self._producer_ini_path.resolve().iterdir()
                if pattern.match(string=str(file))
            ]
        )

    def get_sim_type_str(self) -> str:
        """
        Returns
        -------
        str
        """
        return "gfm"

    def set_zone(self, zone: int, filename: str) -> None:
        """
        Parameters
        ----------
        zone : int
        filename : str
        """
        pass

    def get_config(self) -> configparser.ConfigParser:
        """
        Returns
        -------
        configparser.ConfigParser
        """
        return self._config

    def __read_producer_ini(self) -> configparser.ConfigParser:
        """
        Returns
        -------
        configparser.ConfigParser
        """

        def __get_producer_ini(path: Path, pattern: re.Pattern) -> Path:
            for file in path.resolve().iterdir():
                if pattern.match(string=str(file)):
                    return path.resolve() / file
            raise FileNotFoundError("Producer INI file not found.")

        pattern_ini = re.compile(pattern=r".*\.[iI][nN][iI]")
        producer_ini_path = __get_producer_ini(path=self.get_producer_path(), pattern=pattern_ini)
        producer_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        producer_config.read(filenames=producer_ini_path)
        return producer_config
