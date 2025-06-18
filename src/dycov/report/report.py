#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from dycov.configuration.cfg import config
from dycov.core.execution_parameters import Parameters
from dycov.core.global_variables import (
    CASE_SEPARATOR,
    ELECTRIC_PERFORMANCE_BESS,
    ELECTRIC_PERFORMANCE_PPM,
    ELECTRIC_PERFORMANCE_SM,
    MODEL_VALIDATION,
    MODEL_VALIDATION_BESS,
    MODEL_VALIDATION_PPM,
    REPORT_NAME,
)
from dycov.curves.dynawo.dynawo import DynawoSimulator
from dycov.files.manage_files import copy_latex_files, move_report
from dycov.logging.logging import dycov_logging
from dycov.model.producer import Producer
from dycov.report import figure, html
from dycov.report.LatexReportException import LatexReportException
from dycov.report.tables import (
    active_power_recovery,
    characteristics_response,
    compliance,
    results,
    signal_error,
    solver,
    steady_state_error,
    summary,
    thresholds,
)
from dycov.templates.reports.create_figures import create_figures


def _get_verification_type(sim_type: int) -> str:
    if sim_type > MODEL_VALIDATION:
        return "Model Validation"
    return "Electrical Performance Verification"


def _get_model_type(sim_type: int) -> str:
    if sim_type == ELECTRIC_PERFORMANCE_SM:
        return "Synchronous Machines"

    elif sim_type == ELECTRIC_PERFORMANCE_PPM or sim_type == MODEL_VALIDATION_PPM:
        return "Power Park Modules"

    elif sim_type == ELECTRIC_PERFORMANCE_BESS or sim_type == MODEL_VALIDATION_BESS:
        return "Battery Energy Storage Systems"


def _create_pcs_reports(
    pcs_results: dict,
    output_path: Path,
    working_path: Path,
) -> list:
    pcs = pcs_results["pcs"]
    producer = pcs.get_producer()
    producer.set_zone(pcs.get_zone(), pcs_results["producer"])
    report_name = f"{pcs_results['producer'].replace('_', '')}.{pcs_results['report_name']}"
    return (
        True
        if _create_full_tex(
            pcs_results,
            working_path,
            output_path,
            pcs.get_figures_description(),
            report_name,
            producer,
        )
        > 0
        else False
    )


def _get_reports(
    sorted_summary: list,
    report_results: dict,
    working_path: Path,
) -> list:
    reports = []
    for pcs in sorted_summary:
        pcs_results = report_results[f"{pcs.producer_name}_{pcs.pcs}"]
        report_name = f"{pcs_results['producer'].replace('_', '')}.{pcs_results['report_name']}"
        if any(report_name.replace(".tex", "") in report for report in reports):
            continue

        if (working_path / report_name).exists():
            reports.append(f"\\input{{{report_name.replace('.tex', '')}}}")
    return reports


def _copy_pcs_latex_files(
    pcs_results: dict,
    parameters: Parameters,
    path_latex_files: Path,
    working_path: Path,
):
    pcs = pcs_results["pcs"]
    latex_template_path = (
        path_latex_files / parameters.get_producer().get_sim_type_str() / pcs.get_name()
    )

    latex_user_path = config.get_config_dir() / latex_template_path
    dycov_logging.get_logger("Report").debug(
        f"{pcs.get_name()}: User LaTeX path:{latex_user_path}"
    )
    latex_tool_path = Path(__file__).resolve().parent.parent / latex_template_path
    dycov_logging.get_logger("Report").debug(
        f"{pcs.get_name()}: Tool LaTeX path:{latex_tool_path}"
    )

    if latex_user_path.exists():
        copy_latex_files(latex_user_path, working_path, pcs_results["producer"].replace("_", ""))
    if latex_tool_path.exists():
        copy_latex_files(latex_tool_path, working_path, pcs_results["producer"].replace("_", ""))

    if not (latex_tool_path.exists() or latex_user_path.exists()):
        dycov_logging.get_logger("Report").error(f"{pcs.get_name()}: Latex Template do not exist")
        return


def _create_pcs_figures(
    pcs_results: dict,
    working_path: Path,
):
    pcs = pcs_results["pcs"]
    create_figures(
        working_path,
        pcs_results["producer"],
        pcs.get_name(),
        pcs_results["sim_type"],
    )


def _pcs_replace(
    working_path: Path, pcs_results: dict, report_name: str, producer: Producer
) -> int:

    # To avoid problems when compiling the LaTex doc, the name of the variables is abbreviated,
    #  eliminating potentially problematic characters and unnecessary information.
    producer_name = pcs_results["producer"].replace("_", "")

    subst_dict = {
        "producercommand": f"\\renewcommand{{\\Producer}}{{{pcs_results['producer']}}}",
    }
    subreports = []
    for (
        operating_condition,
        oc_results,
    ) in pcs_results.items():
        if not isinstance(oc_results, dict):
            continue

        # To avoid problems when compiling the LaTex doc, the name of the variables is abbreviated,
        #  eliminating potentially problematic characters and unnecessary information.
        operating_condition_ = operating_condition.replace(CASE_SEPARATOR, "").replace("_RTE-", "")

        html_link = f"./HTML/{pcs_results['producer']}.{operating_condition}.html"
        latex_link = f"\\href{{run:{html_link}}}{{html figures}}"
        subst_dict = subst_dict | {"link" + operating_condition_: latex_link}

        solver_map = solver.create_map(oc_results)
        results_map = results.create_map(oc_results)
        compliance_map = compliance.create_map(oc_results)
        thresholds_map = thresholds.create_map(oc_results, producer.is_field_measurements())
        error_map = signal_error.create_map(oc_results)
        steady_state_error_map = steady_state_error.create_map(oc_results)
        time_error_map = characteristics_response.create_map(oc_results)
        active_power_recovery_map = active_power_recovery.create_map(oc_results)

        subst_dict = subst_dict | {"producer": pcs_results["producer"].replace("_", "\_")}
        subst_dict = subst_dict | {"solver" + operating_condition_: solver_map}
        subst_dict = subst_dict | {"rm" + operating_condition_: results_map}
        subst_dict = subst_dict | {"cm" + operating_condition_: compliance_map}
        subst_dict = subst_dict | {"thm" + operating_condition_: thresholds_map}
        subst_dict = subst_dict | {"em" + operating_condition_: error_map}
        subst_dict = subst_dict | {"ssem" + operating_condition_: steady_state_error_map}
        subst_dict = subst_dict | {"tem" + operating_condition_: time_error_map}
        subst_dict = subst_dict | {"apr" + operating_condition_: active_power_recovery_map}
        if "steady_state_threshold" not in subst_dict:
            subst_dict = subst_dict | {
                "steady_state_threshold": config.get_float("GridCode", "thr_final_ss_mae", 0.01)
                * 100
            }

        oc_report = config.get_value(operating_condition, "report_name")
        if oc_report is not None:
            oc_report_name = f"{producer_name}.{oc_report}"
            # Process only "Compliant" and "Non-compliant" results;
            # thus ignoring FAILED simulations:
            if oc_results["summary"].show_report():
                subreports.append(f"\\input{{{oc_report_name.replace('.tex', '')}}}")

            oc_template = _get_template(working_path, oc_report_name)
            oc_subst_dict2 = {k.replace("_", ""): v for k, v in subst_dict.items()}
            oc_template.stream(oc_subst_dict2).dump(str(working_path / oc_report_name))

    subst_dict = subst_dict | {"subReports": subreports}
    # We want the LaTeX templates to be also valid LaTeX files before Jinja substitutions,
    # in order to compile them from the command line (for design purposes). Therefore, we
    # cannot use LaTeX's active characters to separate words in the Jinja placeholders. With
    # the following instruction we get the tool to use a character that separates words with
    # a valid (i.e. non-active LaTeX) character.
    template = _get_template(working_path, report_name)
    subst_dict2 = {k.replace("_", ""): v for k, v in subst_dict.items()}
    template.stream(subst_dict2).dump(str(working_path / report_name))
    return len(subreports)


def _get_template(path, template_file):
    latex_jinja_env = Environment(
        block_start_string="\\BLOCK{",
        block_end_string="}",
        variable_start_string="{{",
        variable_end_string="}}",
        comment_start_string="\\#{",
        comment_end_string="}",
        line_statement_prefix="$%",
        line_comment_prefix="%#",
        trim_blocks=True,
        autoescape=False,
        loader=FileSystemLoader(path),
    )

    template = latex_jinja_env.get_template(template_file)

    return template


def _generate_figures(
    working_path: Path,
    producer_name: str,
    figures_description: dict,
    figure_key: str,
    oc_results: dict,
    operating_condition: str,
    xmin: float,
    xmax: float,
) -> tuple[list, list]:
    plotted_curves = list()
    figures = list()

    curves = oc_results["curves"]
    if "reference_curves" in oc_results:
        reference_curves = oc_results["reference_curves"]
    else:
        reference_curves = None

    for figure_description in figures_description[figure_key]:
        plot_curves = figure.get_curves2plot(figure_description[1], curves)
        if len(plot_curves) == 0:
            continue

        plot_reference_curves = None
        if reference_curves is not None:
            plot_reference_curves = figure.get_curves2plot(
                figure_description[1], reference_curves, is_reference=True
            )
        figure.create_plot(
            list(curves["time"]),
            figure_description[1],
            plot_curves,
            list(reference_curves["time"]) if reference_curves is not None else None,
            plot_reference_curves,
            {"min": xmin, "max": xmax},
            working_path / (f"{producer_name}_{figure_description[0]}_{operating_condition}.pdf"),
            figure_description[2],
            oc_results,
            figure_description[3],
            f"{figure_description[0]}.{operating_condition}",
        )

        try:
            html_curves, html_figure = html.plotly_figures(
                figure_description, curves, reference_curves, oc_results
            )
            plotted_curves.extend(html_curves)
            if html_figure:
                figures.append(html_figure)
        except Exception as e:
            dycov_logging.get_logger("Report").error(
                f"{figure_description[0]}.{operating_condition}: "
                "A non fatal error occurred while generating the plotly figures"
            )
            dycov_logging.get_logger("Report").error(
                f"{figure_description[0]}.{operating_condition}: {e}"
            )

    return plotted_curves, figures


def _create_full_tex(
    pcs_results: dict,
    working_path: Path,
    output_path: Path,
    figures_description: dict,
    report_name: str,
    producer: Producer,
) -> int:
    """Creates the pcs LaTeX report.

    Parameters
    ----------
    pcs_results: dict
        Results of the validations applied in the pcs
    working_path: Path
        Temporal working path
    output_path: Path
        Final output path
    figures_description: dict
        Description of every figure to plot by PCS
    report_name: str
        Name of the LaTex file template
    producer: Producer
        Producer model
    """

    for operating_condition, oc_results in pcs_results.items():
        if not isinstance(oc_results, dict):
            continue

        figure_key = operating_condition.rsplit(".", 1)[0]
        if figure_key not in figures_description:
            dycov_logging.get_logger("Report").warning("Curves of " + figure_key + " do not exist")
            continue

        if oc_results["curves"] is None:
            continue

        unit_characteristics = {
            "Pmax": producer.p_max_pu,
            "Qmax": producer.q_max_pu,
            "Udim": oc_results["udim"] / producer.u_nom,
        }

        xmin, xmax = figure.get_common_time_range(
            operating_condition,
            unit_characteristics,
            figures_description,
            oc_results,
            operating_condition,
        )
        if config.get_boolean("Debug", "show_figs_t0", False):
            xmin = None
        if config.get_boolean("Debug", "show_figs_tend", False):
            xmax = None

        plotted_curves, figures = _generate_figures(
            working_path,
            pcs_results["producer"],
            figures_description,
            figure_key,
            oc_results,
            operating_condition,
            xmin,
            xmax,
        )
        try:
            if config.get_boolean("Debug", "plot_all_curves_in_html", False):
                figures.extend(html.plotly_all_curves(plotted_curves, oc_results))
            html.create_html(pcs_results["producer"], figures, operating_condition, output_path)
        except Exception as e:
            dycov_logging.get_logger("Report").error(
                f"{operating_condition}: "
                "A non fatal error occurred while generating the HTML report"
            )
            dycov_logging.get_logger("Report").error(f"{operating_condition}: {e}")

    return _pcs_replace(working_path, pcs_results, report_name, producer)


def _summary_log(
    summary_list: list,
    timestamp: str,
    dynawo_version: str,
    model_template: str,
    reference_template: str,
) -> None:
    header_txt = "\nSummary Report\n" "==============\n\n" f"***Run on {timestamp}***\n"
    if dynawo_version:
        header_txt += f"***Dynawo version: {dynawo_version}***\n"
    if model_template:
        header_txt += f"***Model: {model_template}***\n"
    if reference_template:
        header_txt += f"***Reference: {reference_template}***\n"

    header_txt += (
        "\n\n"
        f"{'Producer':20}{'PCS':15}{'Benchmark':25}"
        f"{'Operating Condition':40}{'Overall Result':30}\n"
    )
    header_txt += "-" * (20 + 15 + 25 + 40 + 30)
    header_txt += "\n"

    body_txt = ""
    for i in summary_list:
        body_txt += (
            f"{i.producer_name:20}{i.pcs:15}{i.benchmark:25}"
            f"{i.operating_condition:40}{i.compliance.to_str():30}\n"
        )
    body_txt += "\n"
    # Show the summary report on the console and save it to file
    dycov_logging.get_logger("Report").info(f"{header_txt + body_txt}")


def prepare_pcs_report(pcs_results: dict, parameters: Parameters, path_latex_files: Path):
    output_path = parameters.get_working_dir() / "Reports"
    working_path = parameters.get_working_dir() / "Latex"

    _copy_pcs_latex_files(
        pcs_results,
        parameters,
        path_latex_files,
        working_path,
    )

    _create_pcs_figures(
        pcs_results,
        working_path,
    )

    _create_pcs_reports(
        pcs_results,
        output_path,
        working_path,
    )


def create_pdf(
    sorted_summary: list,
    report_results: dict,
    parameters: Parameters,
    path_latex_files: Path,
) -> None:
    """Creates the dycov final report.

    Parameters
    ----------
    sorted_summary: list
        Sorted list of the overall test results per pcs (compliance/non-compliance)
    report_results: dict
        Results of the validations applied in each pcs
    parameters: Parameters
        Temporal working path
    path_latex_files: Path
        Path to the LaTex templates
    """

    output_path = parameters.get_working_dir() / "Reports"
    working_path = parameters.get_working_dir() / "Latex"

    latex_root_path = Path(__file__).resolve().parent.parent / path_latex_files
    dycov_logging.get_logger("Report").debug(f"Root LaTeX path:{latex_root_path}")
    if latex_root_path.exists():
        shutil.copy(latex_root_path / REPORT_NAME, working_path)
    else:
        dycov_logging.get_logger("Report").error("Latex Template do not exist")
        return

    reports = _get_reports(sorted_summary, report_results, working_path)

    summary_description = ""
    now = time.time()
    timestamp = time.strftime("%Y-%m-%d %H:%M %Z", time.localtime(now))
    summary_description += f"Run on {timestamp} \\\\"

    producer = parameters.get_producer()
    dynawo_version = None
    if producer.is_dynawo_model():
        dynawo_version = str(
            DynawoSimulator().get_dynawo_version(parameters.get_launcher_dwo())
        ).replace("\\", "\\\\")
        summary_description += f"Dynawo version: {dynawo_version} \\\\"

    model_template = str(producer.get_producer_path()).replace("\\", "\\\\")
    summary_description += f"Model: {model_template} \\\\"

    reference_template = None
    if producer.has_reference_curves_path():
        reference_template = str(producer.get_reference_path()).replace("\\", "\\\\")
        summary_description += f"Reference: {reference_template} \\\\"

    _summary_log(sorted_summary, timestamp, dynawo_version, model_template, reference_template)
    summary_map = summary.create_map(sorted_summary)

    # Extracting zones from the PCS data in the summary to identify the relevant "common" files
    # that will be included in the final LaTeX output.
    zones = set(summary_item.zone for summary_item in sorted_summary)
    commonz1_include = ""
    commonz3_include = ""
    if 1 in zones:
        commonz1_include = "\\input{{commonz1}}"
    if 3 in zones:
        commonz3_include = "\\input{{commonz3}}"

    oc_template = _get_template(working_path, REPORT_NAME)
    oc_template.stream(
        {
            "commonz1": commonz1_include,
            "commonz3": commonz3_include,
            "summary_description": summary_description.replace("_", "\_"),
            "summaryReport": summary_map,
            "reports": reports,
            "verificationtype": _get_verification_type(producer.get_sim_type()),
            "modeltype": _get_model_type(producer.get_sim_type()),
        }
    ).dump(str(working_path / REPORT_NAME))

    report_name_ = REPORT_NAME.replace(".tex", "")
    proc = subprocess.run(
        ["pdflatex", "-shell-escape", "-halt-on-error", report_name_],
        cwd=working_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc = subprocess.run(
        ["pdflatex", "-shell-escape", "-halt-on-error", report_name_],
        cwd=working_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if dycov_logging.getEffectiveLevel() == logging.DEBUG:
        if os.name == "nt":
            proc = subprocess.run(
                [
                    "del",
                    "*.toc",
                    "*.aux",
                    "*.log",
                    "*.out",
                    "*.bbl",
                    "*.blg",
                    "*.run.xml",
                    "*.bcf",
                ],
                cwd=working_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        else:
            proc = subprocess.run(
                [
                    "rm",
                    "-f",
                    "*.toc",
                    "*.aux",
                    "*.log",
                    "*.out",
                    "*.bbl",
                    "*.blg",
                    "*.run.xml",
                    "*.bcf",
                ],
                cwd=working_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    dycov_logging.get_logger("Report").debug(proc.stderr.decode("utf-8"))
    if move_report(working_path, output_path, REPORT_NAME):
        dycov_logging.get_logger("Report").info("PDF done.")
    else:
        raise LatexReportException("PDFLatex Error.")
