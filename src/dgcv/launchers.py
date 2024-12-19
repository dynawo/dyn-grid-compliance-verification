#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import argparse
import os
import shutil
from pathlib import Path

from dgcv.core import initialization
from dgcv.core.execution_parameters import Parameters
from dgcv.core.input_template import create_input_template
from dgcv.core.validation import Validation
from dgcv.curves import anonymizer
from dgcv.dynawo import prepare_tool
from dgcv.logging.logging import dgcv_logging
from dgcv.model.producer import ELECTRIC_PERFORMANCE, MODEL_VALIDATION
from dgcv.validation import sanity_checks


def _compile_dynawo_models(dwo_launcher: Path, dynawo_model: str, force: bool) -> int:
    prepare_tool.precompile(dwo_launcher, dynawo_model, force=force)
    return 0


def _generate_input(dwo_launcher: Path, target: Path, topology: str, validation: str) -> int:
    create_input_template(dwo_launcher, target, topology, validation)
    return 0


def _performance_verification(
    dwo_launcher: Path,
    output_dir: Path,
    producer_model: Path,
    producer_curves: Path,
    user_pcs: str,
    only_dtr: bool,
) -> int:
    ep = Parameters(
        dwo_launcher,
        producer_model,
        producer_curves,
        None,
        user_pcs,
        output_dir,
        only_dtr,
        sim_type=ELECTRIC_PERFORMANCE,
    )

    if ep.is_valid():
        md = Validation(
            ep,
        )
        md.validate()
    else:
        return -1

    return 0


def _model_validation(
    dwo_launcher: Path,
    output_dir: Path,
    producer_model: Path,
    producer_curves: Path,
    reference_curves: Path,
    user_pcs: str,
    only_dtr: bool,
) -> int:
    ep = Parameters(
        dwo_launcher,
        producer_model,
        producer_curves,
        reference_curves,
        user_pcs,
        output_dir,
        only_dtr,
        sim_type=MODEL_VALIDATION,
    )

    if not ep.is_complete():
        return -1

    md = Validation(
        ep,
    )
    md.validate()
    return 0


def _check_launchers(dwo_launcher: str) -> None:
    try:
        sanity_checks.check_launchers(dwo_launcher)
    except OSError as e:
        dgcv_logging.get_logger("Sanity Checks").error(e)
        exit(1)


def _add_launcher_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    parser.add_argument(
        "-l",
        "--dwo_launcher",
        required=required,
        help="path to the Dynawo launcher",
        default=None,
    )


def _add_output_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    parser.add_argument(
        "-o",
        "--output_dir",
        required=required,
        help="path to the output directory",
        default=None,
    )


def _add_model_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    parser.add_argument(
        "-m",
        "--producer_model",
        required=required,
        help="path to the directory containing the producer's RMS model files (DYD, PAR, INI)",
        default=None,
    )


def _add_curves_argument(
    parser: argparse.ArgumentParser, explain: str, required: bool = False
) -> None:
    parser.add_argument(
        "-c",
        "--producer_curves",
        required=required,
        help=f"path to the directory containing producer's curves {explain}",
        default=None,
    )


def _add_verification_results_path(
    parser: argparse.ArgumentParser, required: bool = False
) -> None:
    parser.add_argument(
        "-r",
        "--results_path",
        required=required,
        help="path to the results directory of a model verification",
        default=None,
    )


def _add_reference_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "reference_curves",
        nargs="?",
        help="path to the directory containing the reference curves used for validation",
        default=None,
    )


def _add_pcs_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    parser.add_argument(
        "-p",
        "--pcs",
        required=required,
        help="run only the given Performance Checking Sheet (PCS)",
        default=None,
    )


def _add_topology_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    parser.add_argument(
        "-t",
        "--topology",
        required=required,
        help="choice of topology to implement in the DYD file",
        choices=["S", "S+i", "S+Aux", "S+Aux+i", "M", "M+i", "M+Aux", "M+Aux+i"],
        default=None,
    )


def _add_validation_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    parser.add_argument(
        "-v",
        "--validation",
        required=required,
        help="choice of processs, performance verification (SM or PPM) vs. RMS model validation",
        choices=["performance_SM", "performance_PPM", "model_PPM", "model_BESS"],
        default=None,
    )


def _add_dynamic_model_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    parser.add_argument(
        "-m",
        "--dynawo_model",
        required=required,
        help="XML file describing a custom Modelica model",
        default=None,
    )


def _add_force_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    parser.add_argument(
        "-f",
        "--force",
        required=required,
        action="store_true",
        help="force the recompilation of all Modelica models (the user's and the tool's own)",
    )


def _add_noise_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    parser.add_argument(
        "-n",
        "--noisestd",
        required=required,
        type=float,
        help="standard deviation of the noise added to the curves, in pu (recommended range:"
        " [0.01, 0.1])",
    )


def _add_frequency_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    parser.add_argument(
        "-f",
        "--frequency",
        required=required,
        type=float,
        help="cut-off frequency of the filter used for smoothing the noise, in Hz"
        " (default: 3.0, recommended range: [1.0, 5.0])",
        default=3.0,
    )


def _add_debug_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-d", "--debug", action="store_true", help="show debug messages", default=False
    )


def _add_only_dtr_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-od",
        "--only_dtr",
        action="store_true",
        help="run only the official PCS's defined in the DTR "
        "(i.e., ignore any custom defined PCS)",
        default=False,
    )


def _subcomands_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    validate = subparsers.add_parser("validate", help="run the RMS model validation process")
    group = validate.add_mutually_exclusive_group(required=False)
    _add_debug_argument(validate)
    _add_launcher_argument(validate)
    _add_model_argument(group)
    _add_curves_argument(group, explain="(when using curves instead of an RMS model)")
    _add_reference_argument(validate)
    _add_output_argument(validate)
    _add_pcs_argument(validate)
    _add_only_dtr_argument(validate)

    performance = subparsers.add_parser(
        "performance",
        help="run the electric performance verification process",
    )
    _add_debug_argument(performance)
    _add_launcher_argument(performance)
    _add_model_argument(performance)
    _add_curves_argument(
        performance, explain="(if a model is also provided, these are used only for graphing)"
    )
    _add_output_argument(performance)
    _add_pcs_argument(performance)
    _add_only_dtr_argument(performance)

    generate = subparsers.add_parser(
        "generate",
        help="create all the necessary input files through a guided process",
    )
    _add_debug_argument(generate)
    _add_launcher_argument(generate)
    _add_output_argument(generate, required=True)
    _add_topology_argument(generate, required=True)
    _add_validation_argument(generate, required=True)

    compile_model = subparsers.add_parser(
        "compile",
        help="compile custom Modelica models",
    )
    _add_debug_argument(compile_model)
    _add_launcher_argument(compile_model)
    _add_dynamic_model_argument(compile_model)
    _add_force_argument(compile_model)

    anonymize = subparsers.add_parser(
        "anonymize",
        help="generate a new set of curves from a given one, using generic var names and "
        "with (optional) noise added",
    )
    _add_debug_argument(anonymize)
    _add_curves_argument(anonymize, explain="", required=False)
    _add_output_argument(anonymize)
    _add_noise_argument(anonymize)
    _add_frequency_argument(anonymize)
    _add_verification_results_path(anonymize)

    return parser


def _get_dwo_launcher_name(p: argparse.ArgumentParser, args: argparse.Namespace) -> str:
    dwo_launcher_name = None
    if "dwo_launcher" in args:
        dwo_launcher_name = args.dwo_launcher

    if not dwo_launcher_name:
        if os.name == "nt":
            dwo_launcher_name = "dynawo.cmd"
        else:
            dwo_launcher_name = "dynawo.sh"

        if shutil.which(dwo_launcher_name) is None and args.command != "anonymize":
            p.error(
                "The default Dynawo launcher has not been found, please "
                "provide a correct path using the -l argument."
            )
            p.print_help()

    return dwo_launcher_name


def _get_dwo_launcher(args: argparse.Namespace, dwo_launcher_name: str) -> Path:
    dwo_launcher = Path(shutil.which(dwo_launcher_name)).resolve()
    _check_launchers(dwo_launcher)
    initialization.init(dwo_launcher, args.debug)

    return dwo_launcher


def _execute_anonymize(
    p: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> None:
    if args.producer_curves is None and args.results_path is None:
        p.error(
            "Missing arguments.\nFor the anonymize command, the producer_curves or the "
            "results_path argument is required."
        )
        p.print_help()

    if args.producer_curves is not None:
        producer_curves = Path(args.producer_curves)
    else:
        producer_curves = None

    if args.results_path is not None:
        results_path = Path(args.results_path)
    else:
        results_path = None

    if args.output_dir is None:
        output_dir = Path(producer_curves.parent / "Anonymize_Results")
    else:
        output_dir = Path(args.output_dir)

    anonymizer.anonymize(output_dir, args.noisestd, args.frequency, results_path, producer_curves)


def _execute_compile(
    p: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> None:
    if args.dynawo_model is None:
        dynawo_model = None
    else:
        dynawo_model = args.dynawo_model

    r = _compile_dynawo_models(dwo_launcher, dynawo_model, args.force)
    if r != 0:
        p.print_help()


def _execute_generate(
    p: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> None:
    output_dir = Path(args.output_dir)
    topology = args.topology
    validation = args.validation

    r = _generate_input(dwo_launcher, output_dir, topology, validation)
    if r != 0:
        p.print_help()


def _execute_performance(
    p: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> None:
    user_pcs = args.pcs
    if args.producer_model is None:
        producer_model = None
    else:
        producer_model = Path(args.producer_model)
        output_dir = (
            producer_model.parent / "Results" if args.output_dir is None else Path(args.output_dir)
        )
    if args.producer_curves is None:
        producer_curves = None
    else:
        producer_curves = Path(args.producer_curves)
        output_dir = (
            producer_curves.parent / "Results"
            if args.output_dir is None
            else Path(args.output_dir)
        )

    if not producer_model and not producer_curves:
        p.error("Missing arguments.\nTry 'dgcv performance -h' for more information.")
        p.print_help()
        return

    r = _performance_verification(
        dwo_launcher,
        output_dir,
        producer_model,
        producer_curves,
        user_pcs,
        args.only_dtr,
    )
    if r != 0:
        p.error("It is not possible to find the producer model or the producer curves to validate")
        p.print_help()


def _execute_validate(
    p: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> None:
    user_pcs = args.pcs
    if (
        args.producer_model is None and args.producer_curves is None
    ) or args.reference_curves is None:
        producer_model = None
        producer_curves = None
        reference_curves = None
        output_dir = None
    else:
        if args.producer_model is None:
            producer_model = None
            producer_curves = Path(args.producer_curves)
            output_dir = (
                producer_curves.parent / "Results"
                if args.output_dir is None
                else Path(args.output_dir)
            )
        elif args.producer_curves is None:
            producer_model = Path(args.producer_model)
            producer_curves = None
            output_dir = (
                producer_model.parent / "Results"
                if args.output_dir is None
                else Path(args.output_dir)
            )
        reference_curves = Path(args.reference_curves)

    if (not producer_model and not producer_curves) or not reference_curves:
        p.error("Missing arguments.\nTry 'dgcv validate -h' for more information.")
        p.print_help()
        return

    r = _model_validation(
        dwo_launcher,
        output_dir,
        producer_model,
        producer_curves,
        reference_curves,
        user_pcs,
        args.only_dtr,
    )
    if r != 0:
        p.error(
            "It is not possible to find the producer model or the producer curves "
            "to validate. You MUST provide both."
        )
        p.print_help()


def dgcv() -> None:
    p = _subcomands_parser()
    args = p.parse_args()

    dwo_launcher_name = _get_dwo_launcher_name(p, args)

    if args.command is None:
        p.error("Please provide an additional command.")
        p.print_help()

    if args.command != "anonymize":
        dwo_launcher = _get_dwo_launcher(args, dwo_launcher_name)

    if args.command == "validate":
        _execute_validate(p, args, dwo_launcher)

    elif args.command == "generate":
        _execute_generate(p, args, dwo_launcher)

    elif args.command == "compile":
        _execute_compile(p, args, dwo_launcher)

    elif args.command == "performance":
        _execute_performance(p, args, dwo_launcher)

    elif args.command == "anonymize":
        _execute_anonymize(p, args, dwo_launcher)
