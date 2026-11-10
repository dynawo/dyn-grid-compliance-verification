#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import bisect
import math

from dycov.configuration.cfg import config

_SCC_DEFAULTS = {"htb1": 400.0, "htb2": 1500.0, "htb3": 7000.0}


class GeneratorVariables:
    def __grid_code(self, key: str, technology: str | None, default: float = 0.0) -> float:
        """The value [GridCode] gives a key, that of the technology when the key carries its
        suffix: the capability specifications of the DTR give the reactances of the grid by
        technology, and a revision may change them for one technology alone."""
        option = self.__grid_code_option(key, technology) or key
        return config.get_float("GridCode", option, default)

    @staticmethod
    def __grid_code_option(key: str, technology: str | None) -> str | None:
        """The option of [GridCode] that gives a key, that of the technology first."""
        suffixes = (technology,) if technology else ()
        return config.find_option("GridCode", key, *suffixes)

    @staticmethod
    def __grid_code_floats(option: str | None) -> list[float]:
        """The values of an option of [GridCode] that holds a list; empty when no layer gives
        it."""
        if option is None:
            return []
        try:
            return [float(value) for value in config.get_list("GridCode", option) if value.strip()]
        except ValueError:
            raise ValueError(
                f"{config.describe_option('GridCode', option)} is no list of numbers."
            ) from None

    @staticmethod
    def __where(option: str | None, key: str) -> str:
        return config.describe_option("GridCode", option) if option else f"'{key}'"

    def __reactance_b(self, level: str, p_max: float, technology: str | None) -> float:
        """The reactance b of the step the maximum power of the unit falls in. The DTR splits b
        at one power or more: HTB<n>_reactance_b gives the b of every step, HTB<n>_p_max the
        powers between them, and without the first HTB<n>_reactance_b_low and _b_high give the
        two steps of one power."""
        powers_option = self.__grid_code_option(f"{level}_p_max", technology)
        powers = self.__grid_code_floats(powers_option)
        steps_option = self.__grid_code_option(f"{level}_reactance_b", technology)
        steps = self.__grid_code_floats(steps_option)
        steps_options = [(steps_option, f"{level}_reactance_b")]
        if not steps:
            keys = (f"{level}_reactance_b_low", f"{level}_reactance_b_high")
            steps_options = [(self.__grid_code_option(key, technology), key) for key in keys]
            steps = [
                config.get_float("GridCode", option or key, 0.0) for option, key in steps_options
            ]

        if len(steps) != len(powers) + 1:
            steps_given = " and ".join(self.__where(option, key) for option, key in steps_options)
            raise ValueError(
                f"b at {level} has {len(steps)} values, in {steps_given}, and {len(powers)} "
                f"power{'' if len(powers) == 1 else 's'} between them, in "
                f"{self.__where(powers_option, f'{level}_p_max')}: b needs one value more than "
                "the powers."
            )
        if any(lower >= upper for lower, upper in zip(powers, powers[1:])):
            raise ValueError(
                f"The powers between the steps of b at {level}, in "
                f"{self.__where(powers_option, f'{level}_p_max')}, have to rise from one to the "
                "next."
            )
        return steps[bisect.bisect_right(powers, p_max)]

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

    def __require_known_type(self, u_nom: float) -> str:
        generator_type = self.__get_generator_type(u_nom)
        if generator_type == "Invalid UNom":
            raise ValueError(
                f"Unexpected nominal voltage ({u_nom} kV): it is not one of the DTR's "
                "normalized PDR voltage levels (HTB1/HTB2/HTB3)."
            )
        return generator_type

    def __get_generator_variables(
        self, line_xtype: str, p_max: float, u_nom: float, technology: str | None = None
    ) -> tuple[float, float]:
        level = self.__require_known_type(u_nom).upper()
        if line_xtype == "a":
            x_dtr = self.__grid_code(f"{level}_reactance_a", technology)
        elif line_xtype == "b":
            x_dtr = self.__reactance_b(level, p_max, technology)
        else:
            raise KeyError(line_xtype)

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

    def get_generator_category(self, u_nom: float, p_max: float, is_storage: bool) -> str:
        """Gets the category of the unit, as the DTR defines it.

        The arrêté of 9 June 2020 categorises a production unit, and article 5.1.4 §5.2.3 a
        storage one. Both read the connection voltage and the maximum power at injection.

        Parameters
        ----------
        u_nom: float
            Nominal voltage of the PDR, in kV
        p_max: float
            Maximum power at injection of the unit, in MW
        is_storage: bool
            True when the unit stores energy, which the DTR categorises with its own table

        Returns
        -------
        str
            Category of the unit: A, B, C or D

        """
        if u_nom < config.get_float("GridCode", "category_voltage_threshold", 110.0):
            key = "category_thresholds"
        elif is_storage:
            key = "category_storage_thresholds_high_voltage"
        else:
            key = "category_thresholds_high_voltage"
        thresholds = [float(power) for power in config.get_list("GridCode", key)]
        return "ABCD"[bisect.bisect_right(thresholds, p_max)]

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

        Raises
        ------
        ValueError
            If ``u_nom`` is not one of the DTR's normalized PDR voltage levels.
        """
        self.__require_known_type(u_nom)
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

        Raises
        ------
        ValueError
            If ``u_nom`` is not one of the DTR's normalized PDR voltage levels.
        """
        generator_type = self.__require_known_type(u_nom)
        return config.get_float(
            "GridCode", f"{generator_type.upper()}_Scc", _SCC_DEFAULTS[generator_type]
        )

    def calculate_line_xpu(
        self,
        line_xtype: str,
        p_max_pu: float,
        s_nom: float,
        u_nom: float,
        s_nref: float,
        technology: str | None = None,
    ) -> float:
        """Calculate the reactance of the line.
        variables by generator's type, as the base revision gives them:
          HTB1:  a=0.05 b=Pmax<50MW?0.2:0.3, Udim=90kV, Unom=90kV, SnRef=100MVA
                 (a PPM: b 0.2, 0.3, 0.54 and 0.6, split at 50, 250 and 800 MW)
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
        technology: str | None
            SM, PPM or BESS, whose own values of [GridCode] win over the plain ones

        Returns
        -------
        float
            Reactance of the line
        """
        p_max = p_max_pu * -s_nref
        x_dtr, u_dim = self.__get_generator_variables(line_xtype, p_max, u_nom, technology)

        return x_dtr * (u_dim**2 / u_nom**2) * (s_nref / s_nom)

    def calculate_fault_xpu(
        self,
        p_max_pu: float,
        s_nom: float,
        u_nom: float,
        s_nref: float,
        technology: str | None = None,
    ) -> float:
        """Calculate the reactance of the impedant three-phase fault.
        The DTR gives it in the base Udim, Snom, so that the fault, behind the four lines of
        reactance 3*b, holds the PDR at 0.6 Unom while the unit injects no current:
          Xdefaut = 3/4*b / (Uinf * Udim / (0.6 * Unom) - 1)
          Uinf = sqrt(1 + (3/4*b * Pmax / Snom)^2)
          conversion: Xdwo = Xdtr * (Udim^2 / Unom^2) * (SnRef / Snom)

        Parameters
        ----------
        p_max_pu: float
            Maximum active power
        s_nom: float
            Nominal apparent power
        u_nom: float
            Nominal voltage
        s_nref: float
            System-wide S base (SnRef)
        technology: str | None
            SM, PPM or BESS, whose own values of [GridCode] win over the plain ones

        Returns
        -------
        float
            Reactance of the fault
        """
        p_max = p_max_pu * -s_nref
        b, u_dim = self.__get_generator_variables("b", p_max, u_nom, technology)
        grid_x = 0.75 * b
        u_inf = math.sqrt(1 + (grid_x * p_max / s_nom) ** 2)
        x_dtr = grid_x / (u_inf * u_dim / (0.6 * u_nom) - 1)

        return x_dtr * (u_dim**2 / u_nom**2) * (s_nref / s_nom)


def _get_instance():
    return GeneratorVariables()


generator_variables = _get_instance()
