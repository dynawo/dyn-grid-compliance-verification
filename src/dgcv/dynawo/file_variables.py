from dgcv.configuration.cfg import config
from dgcv.core.simulator import Simulator
from dgcv.electrical.generator_variables import generator_variables


class FileVariables:
    def __init__(
        self, tool_variables: list, simulator: Simulator, bm_section: str, oc_section: str
    ):
        self._simulator = simulator
        self._bm_section = bm_section
        self._oc_section = oc_section
        self._model_section = f"{bm_section}.{oc_section}.Model"
        self._event_section = f"{bm_section}.{oc_section}.Event"
        self._tool_variables = tool_variables

    def __obtain_value(self, value_definition: str) -> str:
        return self._simulator.obtain_value(value_definition)

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
        generator_type = generator_variables.get_generator_type(
            self._simulator.get_producer().u_nom
        )

        for key in variables_dict:
            key_type = f"{key}_{generator_type}"
            if key in self._tool_variables:
                continue
            elif config.has_key(self._bm_section, key):
                value = self.__obtain_value(str(config.get_value(self._bm_section, key)))
            elif config.has_key(self._bm_section, key_type):
                value = self.__obtain_value(str(config.get_value(self._bm_section, key_type)))
            elif config.has_key(self._oc_section, key):
                value = self.__obtain_value(str(config.get_value(self._oc_section, key)))
            elif config.has_key(self._oc_section, key_type):
                value = self.__obtain_value(str(config.get_value(self._oc_section, key_type)))
            elif config.has_key(self._model_section, key):
                value = self.__obtain_value(str(config.get_value(self._model_section, key)))
            elif config.has_key(self._model_section, key_type):
                value = self.__obtain_value(str(config.get_value(self._model_section, key_type)))
            elif config.has_key(self._event_section, key):
                value = self.__obtain_value(str(config.get_value(self._event_section, key)))
            elif config.has_key(self._event_section, key_type):
                value = self.__obtain_value(str(config.get_value(self._event_section, key_type)))
            elif config.has_key("Dynawo", key):
                value = self.__obtain_value(str(config.get_value("Dynawo", key)))
            else:
                continue

            if key.startswith("delta_t_"):
                variables_dict[key] = event_params["start_time"] + float(value)
            else:
                variables_dict[key] = value
