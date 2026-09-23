#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from __future__ import annotations

import re
from typing import Optional

from dycov.configuration.cfg import config

# Numeric values: supports integers, decimals, and leading sign; allows ".5" style.
NUMERIC_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$")

# Multiplier * name OR name only.
# - Optional signed float multiplier followed by optional '*' (requires digits, no bare '+'/'-').
# - Name is an identifier-like token (letters, digits, underscores; must start with a letter
#   or underscore).
MULTIPLIER_PATTERN = re.compile(
    r"^(?:(?P<mul>[+-]?(?:\d+(?:\.\d+)?|\.\d+))\s*\*\s*)?(?P<name>[A-Za-z_]\w*)$"
)


def extract_defined_value(
    value_definition: str, parameter: str, base_value: float, sign: int = 1
) -> float:
    """
    Converts a parameter definition to a numeric value.

    Supported forms:
      - Pure numeric: "1.2", "-0.5", ".75"
      - Parameter only: "PmaxInjection", "-PmaxInjection"  (leading sign allowed)
      - Multiplier * parameter: "2*b", "-0.8*Pmax", "+1.25*PmaxInjection"

    Behavior:
      - The definition's explicit sign/multiplier is parsed to produce a raw value.
      - The 'sign' argument is applied at the end to convert the value to the desired
        downstream sign convention (it does NOT sanitize the input; it just transforms
        the final result).

    Parameters
    ----------
    value_definition : str
        The configuration string that defines the value (may include sign/multiplier).
    parameter : str
        Expected parameter name (case-insensitive).
    base_value : float
        Base value associated with the parameter (e.g., Pmax in pu).
    sign : int
        Final sign conversion to match downstream convention (e.g., -1 to flip).

    Returns
    -------
    float
        The computed value after applying the definition and the final 'sign'.
    """
    if value_definition is None:
        raise ValueError(f"{parameter} parameter not defined.")

    s = value_definition.strip()
    if not s:
        raise ValueError(f"{parameter} parameter not defined (empty).")

    # Step 1: Capture an explicit leading sign if present, then parse the rest.
    explicit_sign = 1
    if s[0] in "+-":
        explicit_sign = -1 if s[0] == "-" else 1
        s = s[1:].strip()

    # Step 2: Pure numeric (including the explicit leading sign).
    num_candidate = ("-" if explicit_sign == -1 else "") + s
    if NUMERIC_PATTERN.fullmatch(num_candidate):
        raw_value = float(num_candidate)
        return sign * raw_value  # Apply final convention

    # Step 3: Multiplier * parameter OR parameter only.
    m = MULTIPLIER_PATTERN.fullmatch(s)
    if m:
        multiplier_str = m.group("mul")
        param_name = m.group("name")

        # Validate parameter name, case-insensitive.
        if parameter.lower() not in param_name.lower():
            raise ValueError(
                f"Parameter name mismatch: expected '{parameter}', got '{param_name}'"
            )

        multiplier = float(multiplier_str) if multiplier_str is not None else 1.0

        # Compose: explicit sign from the definition × parsed multiplier × base value.
        raw_value = explicit_sign * multiplier * base_value
        return sign * raw_value  # Apply final convention

    raise ValueError(f"Invalid format for {parameter}: '{value_definition}'")


def unit_characteristics(producer, u_dim: float, line_Xpu: float = 0.0) -> dict[str, float]:
    """Registry of base magnitudes that a value definition may reference.

    Every entry is already expressed in the per-unit Dynawo uses for the network —
    base SnRef (``s_nref``) for powers and impedances, ``Unom`` for voltages — so a
    definition such as ``0.5*Snom`` or ``Unom`` resolves directly to the value used
    elsewhere. Recognizing a new base is a matter of adding an entry here; no caller
    needs to change.

    Parameters
    ----------
    producer :
        Producer model exposing ``p_max_pu``, ``q_max_pu``, ``q_min_pu``, ``s_nom_pu``
        and ``u_nom``.
    u_dim : float
        Dimensioning voltage (kV) of the generator.
    line_Xpu : float
        Connection line reactance in pu.

    Returns
    -------
    dict[str, float]
        Base magnitude name to its per-unit value.
    """
    return {
        "Pmax": producer.p_max_pu,
        "PmaxInjection": producer.p_max_pu,
        "PmaxConsumption": producer.p_max_pu,
        "Qmax": producer.q_max_pu,
        "Qmin": producer.q_min_pu,
        "Snom": producer.s_nom_pu,
        "Udim": u_dim / producer.u_nom,
        "Unom": 1.0,
        "line_XPu": line_Xpu,
    }


def resolve_value_definition(
    value_definition: str,
    characteristics: dict[str, float],
    sign: int = 1,
    origin: Optional[tuple[str, str]] = None,
) -> float:
    """Evaluate a value definition against a registry of base magnitudes.

    Supported forms mirror :func:`extract_defined_value`, but the referenced name is
    looked up in ``characteristics`` instead of being fixed by the caller:
      - Pure numeric: ``"1.2"``, ``"-0.5"``, ``".75"``
      - Name only: ``"Snom"``, ``"-Unom"``
      - Multiplier * name: ``"0.5*Snom"``, ``"-0.05*Pmax"``

    Parameters
    ----------
    value_definition : str
        The configuration string that defines the value.
    characteristics : dict[str, float]
        Base magnitudes keyed by name (see :func:`unit_characteristics`).
    sign : int
        Final sign conversion to match the downstream convention (e.g. -1 to flip).
    origin : Optional[tuple[str, str]]
        (section, key) of the configuration option the definition was read from, used
        to point the user to the offending file and line when the definition is
        rejected.

    Returns
    -------
    float
        The computed value after applying the definition and the final ``sign``.
    """
    location = _describe_config_option(origin)
    if value_definition is None or not value_definition.strip():
        raise ValueError(
            f"Empty value definition.{location} Expected a number, a base magnitude "
            f"name, or 'multiplier*Name' (e.g. '0.5*Snom')."
        )

    s = value_definition.strip()
    explicit_sign = 1
    if s[0] in "+-":
        explicit_sign = -1 if s[0] == "-" else 1
        s = s[1:].strip()

    num_candidate = ("-" if explicit_sign == -1 else "") + s
    if NUMERIC_PATTERN.fullmatch(num_candidate):
        return sign * float(num_candidate)

    m = MULTIPLIER_PATTERN.fullmatch(s)
    if m:
        name = m.group("name")
        if name not in characteristics:
            raise ValueError(
                f"Unknown magnitude '{name}' in value definition '{value_definition}'."
                f"{location} Please check the spelling, the available magnitudes are "
                f"(all case-sensitive): {_available_magnitudes(characteristics)}."
            )
        multiplier = float(m.group("mul")) if m.group("mul") is not None else 1.0
        return sign * explicit_sign * multiplier * characteristics[name]

    raise ValueError(
        f"Invalid value definition '{value_definition}'.{location} Expected a number, "
        f"a base magnitude name, or 'multiplier*Name' (e.g. '0.5*Snom'), where the "
        f"magnitude is one of (all case-sensitive): "
        f"{_available_magnitudes(characteristics)}."
    )


def _describe_config_option(origin: Optional[tuple[str, str]]) -> str:
    """Sentence locating the configuration option a value definition was read from."""
    if origin is None:
        return ""

    return f" Defined by {config.describe_option(*origin)}."


def _available_magnitudes(characteristics: dict[str, float]) -> str:
    return ", ".join(sorted(characteristics))
