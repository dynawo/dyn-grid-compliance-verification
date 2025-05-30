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
    def __init__(
        self,
        tool_variables: list,
        dynawo_curves: ProducerCurves,
        bm_section: str,
        oc_section: str,
    ):
        self._dynawo_curves = dynawo_curves
        self._bm_section = bm_section
        self._oc_section = oc_section
        self._model_section = f"{bm_section}.{oc_section}.Model"
        self._event_section = f"{bm_section}.{oc_section}.Event"
        self._tool_variables = tool_variables

    def __obtain_value(self, value_definition: str) -> str:
        return self._dynawo_curves.obtain_value(value_definition)

    def __obtain_section_value(self, section: str, key: str, generator_type: str) -> str:
        key_type = f"{key}_{generator_type}"
        if config.has_key(section, key):
            return self.__obtain_value(config.get_value(section, key))
        elif config.has_key(section, key_type):
            return self.__obtain_value(config.get_value(section, key_type))

        return None

    def __get_value(self, key: str) -> str:
        generator_type = generator_variables.get_generator_type(
            self._dynawo_curves.get_producer().u_nom
        )

        value = self.__obtain_section_value(self._bm_section, key, generator_type)
        if value:
            return value

        value = self.__obtain_section_value(self._oc_section, key, generator_type)
        if value:
            return value

        value = self.__obtain_section_value(self._model_section, key, generator_type)
        if value:
            return value

        value = self.__obtain_section_value(self._event_section, key, generator_type)
        if value:
            return value

        if config.has_key("Dynawo", key):
            return self.__obtain_value(config.get_value("Dynawo", key))

        return None

    def complete_parameters(
        self,
        variables_dict: dict,
        event_params: dict,
    ) -> None:
        """Complete the variables dictionary with the corresponding values from configuration.

        Parameters
        ----------
        variables_dict: Path
            Variables dictionary
        event_params: dict
            Event parameters
        """
        for key in variables_dict:
            if key in self._tool_variables:
                continue

            value = self.__get_value(key)
            if not value:
                continue

            if key.startswith("delta_t_"):
                variables_dict[key] = event_params["start_time"] + float(value)
            else:
                variables_dict[key] = value
