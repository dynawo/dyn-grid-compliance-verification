#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Access to the ``[Curves-Metadata]`` section of a curves dictionary."""

import configparser
from pathlib import Path
from typing import Optional

SECTION = "Curves-Metadata"

_MANDATORY_OPTIONS = ("is_field_measurements", "sim_t_event_start", "fault_duration")
_GENERATOR_IMAX_SUFFIX = "_GEN_MaxInjectedCurrentPu"


def _is_mandatory(option: str) -> bool:
    return option in _MANDATORY_OPTIONS or option.endswith(_GENERATOR_IMAX_SUFFIX)


class CurvesMetadata:
    """Metadata that the producer declares for a set of curves.

    Every option describes the curve files the producer supplies, so an option declared without
    a value cannot be replaced by a default: it is reported naming its dictionary and its name.

    Parameters
    ----------
    curves_cfg : configparser.ConfigParser
        Contents of the curves dictionary.
    dict_file : Path
        Path to the curves dictionary, used to name it in the error messages.
    """

    def __init__(self, curves_cfg: configparser.ConfigParser, dict_file: Path):
        self._curves_cfg = curves_cfg
        self._dict_file = dict_file

    @classmethod
    def from_dict_file(cls, dict_file: Path) -> "CurvesMetadata":
        """Reads the metadata declared in a curves dictionary.

        The dictionary is read tolerating repeated sections and options, so that the metadata
        can be reported even when the rest of the file still holds template placeholders.

        Parameters
        ----------
        dict_file : Path
            Path to the curves dictionary.

        Returns
        -------
        CurvesMetadata
            The metadata declared in the curves dictionary.

        Raises
        ------
        configparser.Error
            If the curves dictionary cannot be parsed.
        """
        curves_cfg = configparser.ConfigParser(inline_comment_prefixes=("#",), strict=False)
        curves_cfg.optionxform = str
        curves_cfg.read(dict_file)
        return cls(curves_cfg, dict_file)

    def get_float(self, option: str, default: float = 0.0) -> float:
        """Gets a metadata option as a float.

        Parameters
        ----------
        option : str
            Name of the metadata option.
        default : float, optional
            Value to use when the option is not declared. By default, 0.0.

        Returns
        -------
        float
            The declared value, or the default if the option is not declared.

        Raises
        ------
        ValueError
            If the option is declared without a value.
        """
        value = self.__get_declared_value(option)
        return default if value is None else float(value)

    def get_boolean(self, option: str, default: bool = False) -> bool:
        """Gets a metadata option as a boolean.

        Parameters
        ----------
        option : str
            Name of the metadata option.
        default : bool, optional
            Value to use when the option is not declared. By default, False.

        Returns
        -------
        bool
            The declared value, or the default if the option is not declared.

        Raises
        ------
        ValueError
            If the option is declared without a value.
        """
        value = self.__get_declared_value(option)
        return default if value is None else value.lower() == "true"

    def get_generators_imax(self) -> dict:
        """Gets the maximum injected current declared for each generator.

        Returns
        -------
        dict
            Maximum injected current by generator id.

        Raises
        ------
        KeyError
            If the curves dictionary has no metadata section.
        ValueError
            If a maximum injected current is declared without a value.
        """
        return {
            option.replace(_GENERATOR_IMAX_SUFFIX, ""): self.get_float(option)
            for option in self._curves_cfg[SECTION]
            if option.endswith(_GENERATOR_IMAX_SUFFIX)
        }

    def get_unfilled_options(self) -> list:
        """Gets the mandatory metadata options that are declared without a value.

        Returns
        -------
        list
            Names of the mandatory options declared without a value, in declaration order.
        """
        if not self._curves_cfg.has_section(SECTION):
            return []

        return [
            option
            for option in self._curves_cfg[SECTION]
            if _is_mandatory(option) and not self._curves_cfg.get(SECTION, option).strip()
        ]

    def __get_declared_value(self, option: str) -> Optional[str]:
        if not self._curves_cfg.has_option(SECTION, option):
            return None

        value = self._curves_cfg.get(SECTION, option).strip()
        if not value:
            raise ValueError(
                f"the option '{option}' of the '{SECTION}' section in '{self._dict_file}' has "
                f"no value, fill it in with the value that describes the supplied curves"
            )
        return value
