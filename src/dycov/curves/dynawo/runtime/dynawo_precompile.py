#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

from lxml import etree

from dycov.logging.logging import dycov_logging


def get_dynawo_version(launcher_dwo: Path) -> str:
    """
    Retrieves the version of the Dynawo launcher.

    Parameters
    ----------
    launcher_dwo : Path
        Path to the Dynawo launcher executable.

    Returns
    -------
    str
        The Dynawo launcher version string.
    """
    result = subprocess.run(
        [launcher_dwo, "version"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def _compile_model_name(models_path: Path, model_name: str) -> Optional[str]:
    """
    Extracts the compiled model name (Modelica model ID) from a Dynawo model XML file.

    Parameters
    ----------
    models_path : Path
        The directory where the model XML file is located.
    model_name : str
        The name of the model XML file.

    Returns
    -------
    Optional[str]
        The Modelica model ID if found, otherwise None.
    """
    model_tree = etree.parse(models_path / model_name, etree.XMLParser(remove_blank_text=True))
    model_root = model_tree.getroot()
    dyn_namespace = etree.QName(model_root).namespace
    modelica_model = model_root.find(f"{{{dyn_namespace}}}modelicaModel")
    return modelica_model.get("id") if modelica_model is not None else None


def _precompile_model(
    launcher_dwo: Path,
    models_path: Path,
    model_name: str,
    output_path: Path,
) -> None:
    """
    Precompiles a Dynawo model.

    Parameters
    ----------
    launcher_dwo : Path
        Path to the Dynawo launcher executable.
    models_path : Path
        Directory where the model XML file is located.
    model_name : str
        Name of the model XML file to compile.
    output_path : Path
        Directory where the compiled model and related files will be stored.
    """
    logger = dycov_logging.get_logger("DynawoPrecompile")
    compiled_model = _compile_model_name(models_path, model_name)
    extension = ".dll" if os.name == "nt" else ".so"

    if compiled_model and (output_path / (compiled_model + extension)).is_file():
        logger.debug(f"{compiled_model} was already compiled. Skipping precompilation.")
        return

    logger.info(f"Precompiling {model_name}...")
    output_path.mkdir(parents=True, exist_ok=True)

    with open(output_path / "compile.log", "a") as log_file:
        if os.name == "nt":
            # Si en tu repo usas un envoltorio específico de Windows (p.ej., Vsx64.cmd),
            # adáptalo aquí. Por defecto se invoca el launcher con 'jobs'.
            cmd = [
                launcher_dwo,
                "jobs",
                "--generate-preassembled",
                "--model-list",
                model_name,
                "--non-recursive-modelica-models-dir",
                ".",
                "--output-dir",
                output_path,
            ]
            cwd = models_path
        else:
            cmd = [
                launcher_dwo,
                "jobs",
                "--generate-preassembled",
                "--model-list",
                model_name,
                "--non-recursive-modelica-models-dir",
                ".",
                "--output-dir",
                output_path,
            ]
            cwd = models_path

        logger.info("Running command: %s", " ".join(map(str, cmd)))
        subprocess.run(cmd, cwd=cwd, stdout=log_file, stderr=subprocess.STDOUT, check=False)

        # Paso adicional para Linux: volcar la descripción del modelo
        if os.name != "nt" and compiled_model:
            dump_cmd = [
                launcher_dwo,
                "jobs",
                "--dump-model",
                "--model-file",
                compiled_model + extension,
                "--output-file",
                compiled_model + ".desc.xml",
            ]
            logger.info("Running command: %s", " ".join(map(str, dump_cmd)))
            subprocess.run(
                dump_cmd,
                cwd=output_path,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                check=False,
            )

    if compiled_model and (output_path / (compiled_model + extension)).is_file():
        logger.info("Compilation of %s succeeded.", compiled_model)
    else:
        logger.error("Compilation of %s failed.", compiled_model)


def precompile_models(
    launcher_dwo: Path,
    models_path: Path,
    user_dir: Path,
    model_name: Optional[str],
    output_path: Path,
) -> None:
    """
    Compiles the Dynawo models.
    If `model_name` is provided, only that specific model from either `models_path`
    or `user_dir` will be compiled. If `model_name` is None, all XML models
    in both directories will be compiled.

    Parameters
    ----------
    launcher_dwo : Path
        Path to the Dynawo launcher executable.
    models_path : Path
        Directory where the tool's default models are stored.
    user_dir : Path
        Directory where user-defined models are stored.
    model_name : Optional[str]
        Name of the model to compile. If None, all models in `models_path`
        and `user_dir` will be compiled.
    output_path : Path
        Directory where the compiled models will be stored.
    """
    logger = dycov_logging.get_logger("DynawoPrecompile")
    output_path.mkdir(parents=True, exist_ok=True)  # Ensure output directory exists

    models_to_compile: list[tuple[Path, str]] = []
    if model_name is None:
        # Compila todos los XML de ambos directorios
        models_to_compile += [(models_path, p.name) for p in models_path.glob("*.[xX][mM][lL]")]
        models_to_compile += [(user_dir, p.name) for p in user_dir.glob("*.[xX][mM][lL]")]
    else:
        if (models_path / model_name).is_file():
            models_to_compile.append((models_path, model_name))
        if (user_dir / model_name).is_file():
            models_to_compile.append((user_dir, model_name))

    extension = ".dll" if os.name == "nt" else ".so"

    for current_models_path, current_model_name in models_to_compile:
        compiled_model = _compile_model_name(current_models_path, current_model_name)
        # Si se pide explícitamente un modelo concreto, forzamos recompilación
        if compiled_model and (output_path / (compiled_model + extension)).is_file():
            if model_name:
                logger.debug(
                    "Removing existing compiled model: %s",
                    output_path / (compiled_model + extension),
                )
                (output_path / (compiled_model + extension)).unlink()

        _precompile_model(
            launcher_dwo,
            current_models_path,
            current_model_name,
            output_path,
        )
