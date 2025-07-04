#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from dycov.configuration.cfg import config
from dycov.curves.curves import ProducerCurves
from dycov.electrical.generator_variables import generator_variables


class FileVariables:
    """
    Manages the retrieval and completion of variables for Dycov based on configuration files.
    """

    def __init__(
        self,
        tool_variables: list,
        dynawo_curves: ProducerCurves,
        bm_section: str,
        oc_section: str,
    ):
        """
        Initializes the FileVariables class.

        Parameters
        ----------
        tool_variables: list
            A list of variables managed by the tool, which should not be overwritten.
        dynawo_curves: ProducerCurves
            An instance of ProducerCurves to obtain curve values.
        bm_section: str
            The base model section name in the configuration.
        oc_section: str
            The operational conditions section name in the configuration.
        """
        self._dynawo_curves = dynawo_curves
        self._bm_section = bm_section
        self._oc_section = oc_section
        # Construct the model and event section names based on bm_section and oc_section.
        self._model_section = f"{bm_section}.{oc_section}.Model"
        self._event_section = f"{bm_section}.{oc_section}.Event"
        self._tool_variables = tool_variables

    def __obtain_value(self, value_definition: str) -> str:
        """
        Obtains the actual value from a value definition using the dynawo_curves object.

        Parameters
        ----------
        value_definition: str
            The definition of the value to obtain.

        Returns
        -------
        str
            The obtained value.
        """
        return self._dynawo_curves.obtain_value(value_definition)

    def __get_value_from_section(self, section: str, key: str, generator_type: str) -> str:
        """
        Retrieves a value from a specific configuration section, considering generator type.

        This method first tries to find the key with a generator type suffix (e.g., 'key_TypeA').
        If not found, it falls back to just the key (e.g., 'key').

        Parameters
        ----------
        section: str
            The configuration section to search within.
        key: str
            The key of the variable to retrieve.
        generator_type: str
            The type of the generator, used for type-specific keys.

        Returns
        -------
        str
            The obtained value if found, otherwise None.
        """
        # Prioritize key specific to generator type
        key_type = f"{key}_{generator_type}"
        if config.has_key(section, key_type):
            return self.__obtain_value(config.get_value(section, key_type))
        # Fallback to general key if type-specific key is not found
        elif config.has_key(section, key):
            return self.__obtain_value(config.get_value(section, key))
        return None

    def __get_variable_value(self, key: str) -> str:
        """
        Retrieves the value for a given key by searching through various configuration sections.

        The search order is: base model section, operational conditions section,
        model section, event section, and finally the global 'Dynawo' section.
        Generator-specific values are prioritized.

        Parameters
        ----------
        key: str
            The key of the variable to retrieve.

        Returns
        -------
        str
            The obtained value if found, otherwise None.
        """
        # Determine the generator type based on the nominal voltage
        generator_type = generator_variables.get_generator_type(
            self._dynawo_curves.get_producer().u_nom
        )

        # Sections to search for the variable in order of precedence
        sections = [
            self._bm_section,
            self._oc_section,
            self._model_section,
            self._event_section,
        ]

        # Search for the key in defined sections, considering generator type
        for section in sections:
            value = self.__get_value_from_section(section, key, generator_type)
            if value:
                return value

        # As a last resort, check the global 'Dynawo' section
        if config.has_key("Dynawo", key):
            return self.__obtain_value(config.get_value("Dynawo", key))

        return None

    def complete_parameters(
        self,
        variables_dict: dict,
        event_params: dict,
    ) -> None:
        """
        Completes the variables dictionary with corresponding values from the configuration.

        This method iterates through the `variables_dict`. For each key not present in
        `_tool_variables`, it attempts to find a matching value in the configuration.
        If found, the value in `variables_dict` is updated. Special handling is applied
        for keys starting with "delta_t_", where the value is added to
        `event_params["start_time"]`.

        Parameters
        ----------
        variables_dict: dict
            The dictionary of variables to be completed.
        event_params: dict
            A dictionary containing event-specific parameters, such as 'start_time'.
        """
        for key in variables_dict:
            # Skip variables that are managed by the tool
            if key in self._tool_variables:
                continue

            value = self.__get_variable_value(key)
            if not value:
                continue

            # Special handling for time-delta variables
            if key.startswith("delta_t_"):
                variables_dict[key] = event_params["start_time"] + float(value)
            else:
                variables_dict[key] = value
