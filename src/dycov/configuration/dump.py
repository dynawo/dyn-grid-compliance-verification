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
def _get_effective_value_with_source(
    config, section: str, key: str
) -> Tuple[Optional[str], Optional[str]]:
    """Return effective value and its source (user | pcs | default)."""
    if config._user_config.has_option(section, key):
        value = config._user_config.get(section, key)
        if config._is_valid_value(value):
            return value, "user"

    if config._pcs_config.has_option(section, key):
        value = config._pcs_config.get(section, key)
        if config._is_valid_value(value):
            return value, "pcs"

    if config._default_config.has_option(section, key):
        value = config._default_config.get(section, key)
        if config._is_valid_value(value):
            return value, "default"

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
    sections = (
        set(config._default_config.sections())
        | set(config._pcs_config.sections())
        | set(config._user_config.sections())
    )

    effective = {}
    for section in sections:
        keys = set()
        if config._default_config.has_section(section):
            keys |= set(config._default_config.options(section))
        if config._pcs_config.has_section(section):
            keys |= set(config._pcs_config.options(section))
        if config._user_config.has_section(section):
            keys |= set(config._user_config.options(section))

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
        if src in ("user", "pcs")
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
    logger.debug("===== DYCOV EFFECTIVE CONFIGURATION " "(precedence: user > pcs > default) =====")

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

    pcs_cfg = config._pcs_config

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
        sections.extend(sorted(s for s in pcs_cfg.sections() if s.startswith(base + ".")))

    for section in sections:
        if not pcs_cfg.has_section(section):
            continue

        logger.debug("--- %s ------------------------------", section)
        for key, value in sorted(pcs_cfg.items(section), key=lambda kv: kv[0].lower()):
            logger.debug("  %s = %s", key, value)

    logger.debug("===== END DYCOV PCS EFFECTIVE DESCRIPTION =====")
