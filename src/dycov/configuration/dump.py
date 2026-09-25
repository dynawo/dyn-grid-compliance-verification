#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

"""
Utilities to dump the **effective configuration and PCS description**
used during a DyCoV execution.

This module provides:
- a compact configuration summary (human‑oriented),
- a full effective configuration dump (forensic / diagnostic).

Nothing is persisted to disk; information is only written to logs.
"""

from __future__ import annotations

from typing import Optional, Tuple

from dycov.logging import dycov_logging


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------
def _layers_by_source(config) -> Tuple[Tuple[str, object], ...]:
    """Every layer as a (source, parser) pair, from the highest precedence to the lowest."""
    return (
        ("pcs-user", config._pcs_user_config),
        ("user", config._user_config),
        ("dtr", config._pcs_dtr_config),
        ("pcs", config._pcs_default_config),
        ("default", config._default_config),
    )


def _pcs_layers_by_source(config) -> Tuple[Tuple[str, object], ...]:
    """The layers describing a PCS, from the highest precedence to the lowest."""
    return tuple(
        (source, parser)
        for source, parser in _layers_by_source(config)
        if source in ("pcs-user", "dtr", "pcs")
    )


def _pcs_sections(config) -> set:
    """Sections defined by any of the PCS layers."""
    return {
        section for _, parser in _pcs_layers_by_source(config) for section in parser.sections()
    }


def _pcs_items(config, section: str) -> dict:
    """Options of a PCS section, with the higher precedence layers overriding the lower."""
    items = {}
    for _, parser in reversed(_pcs_layers_by_source(config)):
        if parser.has_section(section):
            items.update(parser.items(section))

    return items


def _get_effective_value_with_source(
    config, section: str, key: str
) -> Tuple[Optional[str], Optional[str]]:
    """Return effective value and its source (pcs-user | user | dtr | pcs | default)."""
    for source, parser in _layers_by_source(config):
        if parser.has_option(section, key):
            value = parser.get(section, key)
            if config._is_valid_value(value):
                return value, source

    return None, None


# -----------------------------------------------------------------------------
# Configuration dump (summary + full)
# -----------------------------------------------------------------------------
def dump_effective_config(config) -> None:
    """
    Dump the effective DyCoV configuration.

    The dump consists of:
    1) A short configuration summary (non‑default + key parameters)
    2) A full configuration dump (only in DEBUG)
    """
    logger = dycov_logging.get_logger("ConfigDump")

    # ------------------------------------------------------------------
    # Build effective config map
    # ------------------------------------------------------------------
    layers = _layers_by_source(config)
    sections = {section for _, parser in layers for section in parser.sections()}

    effective = {}
    for section in sections:
        keys = set()
        for _, parser in layers:
            if parser.has_section(section):
                keys |= set(parser.options(section))

        for key in keys:
            value, source = _get_effective_value_with_source(config, section, key)
            if value is not None:
                effective.setdefault(section, {})[key] = (value, source)

    # ------------------------------------------------------------------
    # 1) CONFIG SUMMARY
    # ------------------------------------------------------------------
    logger.debug("===== DYCOV CONFIG SUMMARY =====")

    non_default = [
        (sec, k, v, src)
        for sec, items in effective.items()
        for k, (v, src) in items.items()
        if src != "default"
    ]

    if non_default:
        logger.debug("Non-default values:")
        for sec, key, value, src in sorted(non_default):
            logger.debug("  [%s] %s = %s (%s)", sec, key, value, src)
    else:
        logger.debug("No non-default configuration values detected.")

    # Execution‑relevant defaults worth showing explicitly
    logger.debug("Execution-relevant settings:")
    for sec, key in [
        ("Global", "parallel_num_processes"),
        ("Global", "parallel_pcs_validation"),
        ("Debug", "max_simulation_retries"),
        ("Dynawo", "solver_lib"),
    ]:
        if sec in effective and key in effective[sec]:
            val, src = effective[sec][key]
            logger.debug("  [%s] %s = %s (%s)", sec, key, val, src)

    logger.debug("===== END DYCOV CONFIG SUMMARY =====")

    # ------------------------------------------------------------------
    # 2) FULL EFFECTIVE CONFIG (forensic)
    # ------------------------------------------------------------------
    logger.debug(
        "===== DYCOV EFFECTIVE CONFIGURATION "
        "(precedence: pcs-user > user > dtr > pcs > default) ====="
    )

    for section in sorted(effective):
        logger.debug("--- %s %s", section, "-" * max(1, 60 - len(section)))
        for key in sorted(effective[section]):
            value, source = effective[section][key]
            logger.debug("  %s = %s (source: %s)", key, value, source)

    logger.debug("===== END DYCOV EFFECTIVE CONFIGURATION =====")


# -----------------------------------------------------------------------------
# PCS description dump
# -----------------------------------------------------------------------------
def dump_effective_pcs_description(
    config,
    pcs: str,
    benchmark: str | None = None,
    oc: str | None = None,
) -> None:
    logger = dycov_logging.get_logger("ConfigDump")

    pcs_sections = _pcs_sections(config)

    logger.debug("===== DYCOV PCS EFFECTIVE DESCRIPTION =====")
    logger.debug("PCS       : %s", pcs)
    if benchmark:
        logger.debug("Benchmark : %s", benchmark)
    if oc:
        logger.debug("OC        : %s", oc)

    sections = [pcs]

    if benchmark:
        sections.append(f"{pcs}.{benchmark}")

    if benchmark and oc:
        base = f"{pcs}.{benchmark}.{oc}"
        sections.append(base)
        sections.extend(sorted(s for s in pcs_sections if s.startswith(base + ".")))

    for section in sections:
        if section not in pcs_sections:
            continue

        logger.debug("--- %s ------------------------------", section)
        items = _pcs_items(config, section)
        for key, value in sorted(items.items(), key=lambda kv: kv[0].lower()):
            logger.debug("  %s = %s", key, value)

    logger.debug("===== END DYCOV PCS EFFECTIVE DESCRIPTION =====")
