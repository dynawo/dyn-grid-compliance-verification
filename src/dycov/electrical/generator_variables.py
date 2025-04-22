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


class GeneratorVariables:
    def __init__(
        self,
    ):
        htb1_a = config.get_float("GridCode", "HTB1_reactance_a", 0.0)
        htb2_a = config.get_float("GridCode", "HTB2_reactance_a", 0.0)
        htb3_a = config.get_float("GridCode", "HTB3_reactance_a", 0.0)
        htb1_b1 = config.get_float("GridCode", "HTB1_reactance_b_low", 0.0)
        htb2_b1 = config.get_float("GridCode", "HTB2_reactance_b_low", 0.0)
        htb3_b1 = config.get_float("GridCode", "HTB3_reactance_b_low", 0.0)
        htb1_b2 = config.get_float("GridCode", "HTB1_reactance_b_high", 0.0)
        htb2_b2 = config.get_float("GridCode", "HTB2_reactance_b_high", 0.0)
        htb3_b2 = config.get_float("GridCode", "HTB3_reactance_b_high", 0.0)
        htb1_p_max = config.get_float("GridCode", "HTB1_p_max", 0.0)
        htb2_p_max = config.get_float("GridCode", "HTB2_p_max", 0.0)
        htb3_p_max = config.get_float("GridCode", "HTB3_p_max", 0.0)
        htb1_scc = config.get_float("GridCode", "HTB1_Scc", 400.0)
        htb2_scc = config.get_float("GridCode", "HTB2_Scc", 1500.0)
        htb3_scc = config.get_float("GridCode", "HTB3_Scc", 7000.0)

        self._x_dtr_switcher = {
            "htb1": {
                "a": (htb1_a, htb1_a),
                "b": (htb1_b1, htb1_b2),
            },
            "htb2": {
                "a": (htb2_a, htb2_a),
                "b": (htb2_b1, htb2_b2),
            },
            "htb3": {
                "a": (htb3_a, htb3_a),
                "b": (htb3_b1, htb3_b2),
            },
        }
        self._p_max_switcher = {
            "htb1": htb1_p_max,
            "htb2": htb2_p_max,
            "htb3": htb3_p_max,
        }
        self._scc_switcher = {
            "htb1": htb1_scc,
            "htb2": htb2_scc,
            "htb3": htb3_scc,
        }

    def __get_generator_type(self, u_nom: float) -> str:
        # The Unom are divided into 2 lists to differentiate land from offshore.
        unom = str(u_nom)
        if unom in config.get_list("GridCode", "HTB1_Udims") or unom in config.get_list(
            "GridCode", "HTB1_External_Udims"
        ):
            return "htb1"
        elif unom in config.get_list("GridCode", "HTB2_Udims") or unom in config.get_list(
            "GridCode", "HTB2_External_Udims"
        ):
            return "htb2"
        elif unom in config.get_list("GridCode", "HTB3_Udims") or unom in config.get_list(
            "GridCode", "HTB3_External_Udims"
        ):
            return "htb3"
        return "Invalid UNom"

    def __get_generator_variables(
        self, line_xtype: str, p_max: float, u_nom: float
    ) -> tuple[float, float]:
        generator_type = self.__get_generator_type(u_nom)
        x_dtr_tuple = self._x_dtr_switcher.get(generator_type, lambda: "Invalid Type").get(
            line_xtype, lambda: "Invalid Type"
        )
        p_max_threshold = self._p_max_switcher.get(generator_type, lambda: "Invalid Type")

        if p_max < p_max_threshold:
            x_dtr = x_dtr_tuple[0]
        else:
            x_dtr = x_dtr_tuple[1]

        return x_dtr, self.get_generator_u_dim(u_nom)

    def get_generator_type(self, u_nom: float) -> str:
        """Gets the generator type by its nominal voltage.

        Parameters
        ----------
        u_nom: float
            Nominal voltage

        Returns
        -------
        str
            Generator type (HTB1, HTB2 or HTB3)
        """
        return self.__get_generator_type(u_nom).upper()

    def get_generator_u_dim(self, u_nom: float) -> float:
        """Gets the generator sizing voltage (Udim) by its nominal voltage.

        Parameters
        ----------
        u_nom: float
            Nominal voltage

        Returns
        -------
        float
            Generator sizing voltage (Udim)
        """
        generator_type = self.__get_generator_type(u_nom)
        if generator_type == "Invalid UNom":
            return "Invalid Type"

        udim_name = f"Udim_{int(u_nom)}kV"
        return config.get_float("GridCode", udim_name, 0.0)

    def get_scc(self, u_nom: float) -> float:
        """Gets the short circuit current.

        Parameters
        ----------
        u_nom: float
            Nominal voltage

        Returns
        -------
        float
            Short circuit current (Scc)
        """
        generator_type = self.__get_generator_type(u_nom)
        if generator_type == "Invalid UNom":
            return "Invalid Type"

        return self._scc_switcher.get(generator_type, lambda: "Invalid Type")

    def calculate_line_xpu(
        self, line_xtype: str, p_max_pu: float, s_nom: float, u_nom: float, s_nref: float
    ) -> float:
        """Calculate the reactance of the line.
        variables by generator's type:
          HTB1:  a=0.05 b=Pmax<50MW?0.2:0.3, Udim=90kV, Unom=90kV, SnRef=100MVA
          HTB2:  a=0.05 b=Pmax<250MW?0.3:0.54, Udim=235kV, Unom=225kV, SnRef=100MVA
          HTB3:  a=0.05 b=Pmax<800MW?0.54:0.6 Udim=405kV, Unom=400kV, SnRef=100MVA
          conversion: Xdwo = Xdtr * (Udim^2 / Unom^2) * (SnRef / Snom)

        Parameters
        ----------
        line_xtype: str
            Standard reactance value, allowed values are 'a' or 'b'
        p_max_pu: float
            Maximum active power
        s_nom: float
            Nominal apparent power
        u_nom: float
            Nominal voltage
        s_nref: float
            System-wide S base (SnRef)

        Returns
        -------
        float
            Reactance of the line
        """
        p_max = p_max_pu * -s_nref
        x_dtr, u_dim = self.__get_generator_variables(line_xtype, p_max, u_nom)

        return x_dtr * (u_dim**2 / u_nom**2) * (s_nref / s_nom)


def _get_instance():
    return GeneratorVariables()


generator_variables = _get_instance()
