#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from pathlib import Path

from lxml import etree

from dycov.curves.dynawo.dictionary.translator import dynawo_translator
from dycov.logging import dycov_logging

PERFORMANCE_SM = 1
PERFORMANCE_PPM = 2
PERFORMANCE_BESS = 3

VALIDATION_PPM = 11
VALIDATION_BESS = 12

BUS_DYNAMIC_MODEL = "BUS_DYNAMIC_MODEL"
SM_DYNAMIC_MODEL = "SM_DYNAMIC_MODEL"
PPM_DYNAMIC_MODEL = "PPM_DYNAMIC_MODEL"
BESS_DYNAMIC_MODEL = "BESS_DYNAMIC_MODEL"
LINE_DYNAMIC_MODEL = "LINE_DYNAMIC_MODEL"
LOAD_DYNAMIC_MODEL = "LOAD_DYNAMIC_MODEL"
XFMR_DYNAMIC_MODEL = "XFMR_DYNAMIC_MODEL"

PDR_ID = "BusPDR"
INT_LINE_ID = "IntNetwork_Line"
MAIN_XFMR_ID = "Main_Xfmr"
INT_BUS_ID = "Int_Bus"
XFMR_AUX_ID = "AuxLoad_Xfmr"
AUX_ID = "Aux_Load"
XFMR_ID = "StepUp_Xfmr"
# Generator ids must contain a token accepted by topology_checks._is_valid_generator.
SM_ID = "Synch_Gen"
PPM_ID = "Wind_Turbine"
XFMR1_ID = "StepUp_Xfmr_1"
PPM1_ID = "Wind_Turbine_1"
XFMR2_ID = "StepUp_Xfmr_2"
PPM2_ID = "Wind_Turbine_2"
BESS_ID = "Bess"
BESS1_ID = "Bess_1"
BESS2_ID = "Bess_2"

# One placeholder for all the generator's ports (terminal + remote-control vars) so a single
# find-replace fills them; braces (not <>) to avoid XML-escaping.
MODEL_PREFIX = "{MODEL_PREFIX}"
SM_TERMINAL = "generator_terminal"
PPM_TERMINAL = f"{MODEL_PREFIX}_terminal"
BESS_TERMINAL = "BESS_terminal"
BUS_TERMINAL = "bus_terminal"
LOAD_TERMINAL = "load_terminal"
XFMR_TERMINAL1 = "transformer_terminal1"
XFMR_TERMINAL2 = "transformer_terminal2"
LINE_TERMINAL1 = "line_terminal1"
LINE_TERMINAL2 = "line_terminal2"

PLACEHOLDER_MODELS = [
    BUS_DYNAMIC_MODEL,
    SM_DYNAMIC_MODEL,
    PPM_DYNAMIC_MODEL,
    BESS_DYNAMIC_MODEL,
    LINE_DYNAMIC_MODEL,
    LOAD_DYNAMIC_MODEL,
    XFMR_DYNAMIC_MODEL,
]

PLACEHOLDER_TERMINALS = [PPM_TERMINAL]


def _add_terminal_options(dyd_root: etree.Element, terminal: str):
    if terminal != PPM_TERMINAL:
        return

    prefixes = ["photovoltaics", "WTG3", "WTG4A", "WTG4B", "WT3", "WT4A", "WT4B", "WPP", "WT"]
    dyd_root.append(
        etree.Comment(
            f"Replace '{MODEL_PREFIX}' with the model's prefix (one find-replace fills the "
            f"terminal and all remote-control ports). Available: {prefixes}"
        )
    )


def _add_lib_options(dyd_root: etree.Element, lib: str, is_model_validation: bool = False):
    if lib == BUS_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_bus_models()
    elif lib == SM_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_synchronous_machine_models()
    elif lib == PPM_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_power_park_models()
    elif lib == BESS_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_storage_models()
    elif lib == LINE_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_line_models()
    elif lib == LOAD_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_load_models()
    elif lib == XFMR_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_transformer_models()
    dyd_root.append(
        etree.Comment(f"Replace the placeholder: '{lib}', available_options: {available_models}")
    )
    if is_model_validation:
        dyd_root.append(
            etree.Comment(
                "For model validation it is essential to use the same dynamic model family in "
                "zone1 and Zone3"
            )
        )


def _add_blackbox(
    dyd_root: etree.Element,
    ns: str,
    id: str,
    lib: str,
    par_filename: str,
    par_id: str,
    show_comment: bool = False,
):
    if show_comment and lib in PLACEHOLDER_MODELS:
        _add_lib_options(dyd_root, lib)

    etree.SubElement(
        dyd_root,
        f"{{{ns}}}blackBoxModel",
        id=id,
        lib=lib,
        parFile=par_filename,
        parId=par_id,
    )


def _add_connection(
    dyd_root: etree.Element,
    ns: str,
    id_from: str,
    var_from: str,
    id_to: str,
    var_to: str,
    show_comment: bool = False,
):
    if show_comment:
        if var_from in PLACEHOLDER_TERMINALS:
            _add_terminal_options(dyd_root, var_from)
        elif var_to in PLACEHOLDER_TERMINALS:
            _add_terminal_options(dyd_root, var_to)

    etree.SubElement(
        dyd_root,
        f"{{{ns}}}connect",
        id1=id_from,
        var1=var_from,
        id2=id_to,
        var2=var_to,
    )


def _remote_control_ports(gen_terminal: str) -> dict:
    """PCC-monitoring port names derived from the gen terminal (works for the concrete
    ``<prefix>terminal`` and the ``{MODEL_PREFIX}_terminal`` placeholder alike)."""
    if gen_terminal.endswith("terminal"):
        prefix = gen_terminal[: -len("terminal")]
    else:
        prefix = gen_terminal + "_"
    return {
        "uPccPu_re": f"{prefix}uPccPu_re",
        "uPccPu_im": f"{prefix}uPccPu_im",
        "PPccPu": f"{prefix}PPccPu",
        "QPccPu": f"{prefix}QPccPu",
    }


def _plant_generators(validation_type: int, topology: str, n_generators: int = 2) -> list:
    """The (id, terminal) of the plant generators that sense the PCC — only PPM/BESS (SM has no
    plant control); ``n_generators`` of them in ``M``, one in ``S``."""
    if validation_type in (PERFORMANCE_PPM, VALIDATION_PPM):
        gen_base, gen_terminal = PPM_ID, PPM_TERMINAL
    elif validation_type in (PERFORMANCE_BESS, VALIDATION_BESS):
        gen_base, gen_terminal = BESS_ID, BESS_TERMINAL
    else:
        return []
    if topology.casefold().startswith("m"):
        return [(f"{gen_base}_{i}", gen_terminal) for i in range(1, n_generators + 1)]
    return [(gen_base, gen_terminal)]


def _add_remote_control(dyd_root: etree.Element, ns: str, gen_id: str, gen_terminal: str):
    """Wire a plant generator's PCC measurements (U, P, Q) to the PDR bus. ``Measurements`` and
    ``BusPDR`` are injected by DyCoV (referenced, not declared)."""
    ports = _remote_control_ports(gen_terminal)
    dyd_root.append(
        etree.Comment(
            "Remote voltage control: connect the plant's monitored voltage (UPcc) to the PDR bus"
        )
    )
    _add_connection(dyd_root, ns, PDR_ID, f"{BUS_TERMINAL}_V_re", gen_id, ports["uPccPu_re"])
    _add_connection(dyd_root, ns, PDR_ID, f"{BUS_TERMINAL}_V_im", gen_id, ports["uPccPu_im"])
    dyd_root.append(
        etree.Comment(
            "Remote P/Q control: connect the plant's monitored flows (PPcc, QPcc) to the PDR bus"
        )
    )
    dyd_root.append(
        etree.Comment(
            '(note this is done through a "measurements" object that is connected to the PDR bus)'
        )
    )
    _add_connection(dyd_root, ns, "Measurements", "measurements_PPu", gen_id, ports["PPccPu"])
    _add_connection(dyd_root, ns, "Measurements", "measurements_QPu", gen_id, ports["QPccPu"])


def _generator_spec(validation_type: int) -> tuple[str, str, str]:
    """The single generator's ``(id, lib placeholder, terminal)`` for an ``S``-family topology."""
    if validation_type == PERFORMANCE_SM:
        return SM_ID, SM_DYNAMIC_MODEL, SM_TERMINAL
    if validation_type in (PERFORMANCE_PPM, VALIDATION_PPM):
        return PPM_ID, PPM_DYNAMIC_MODEL, PPM_TERMINAL
    return BESS_ID, BESS_DYNAMIC_MODEL, BESS_TERMINAL


def _create_s_topology(dyd_root: etree.Element, ns: str, validation_type: int, par_filename: str):
    gen_id, gen_lib, gen_terminal = _generator_spec(validation_type)
    _add_blackbox(dyd_root, ns, XFMR_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR_ID, True)
    _add_blackbox(dyd_root, ns, gen_id, gen_lib, par_filename, gen_id, True)

    _add_connection(dyd_root, ns, XFMR_ID, XFMR_TERMINAL2, PDR_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, gen_id, gen_terminal, XFMR_ID, XFMR_TERMINAL1, True)


def _create_saux_topology(
    dyd_root: etree.Element, ns: str, validation_type: int, par_filename: str
):
    gen_id, gen_lib, gen_terminal = _generator_spec(validation_type)
    _add_blackbox(dyd_root, ns, XFMR_AUX_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR_AUX_ID, True)
    _add_blackbox(dyd_root, ns, AUX_ID, LOAD_DYNAMIC_MODEL, par_filename, AUX_ID, True)
    _add_blackbox(dyd_root, ns, XFMR_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR_ID)
    _add_blackbox(dyd_root, ns, gen_id, gen_lib, par_filename, gen_id, True)

    _add_connection(dyd_root, ns, XFMR_AUX_ID, XFMR_TERMINAL2, PDR_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR_ID, XFMR_TERMINAL2, PDR_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, AUX_ID, LOAD_TERMINAL, XFMR_AUX_ID, XFMR_TERMINAL1)
    _add_connection(dyd_root, ns, gen_id, gen_terminal, XFMR_ID, XFMR_TERMINAL1, True)


def _create_si_topology(dyd_root: etree.Element, ns: str, validation_type: int, par_filename: str):
    gen_id, gen_lib, gen_terminal = _generator_spec(validation_type)
    _add_blackbox(dyd_root, ns, INT_LINE_ID, LINE_DYNAMIC_MODEL, par_filename, INT_LINE_ID, True)
    _add_blackbox(dyd_root, ns, INT_BUS_ID, BUS_DYNAMIC_MODEL, par_filename, INT_BUS_ID, True)
    _add_blackbox(dyd_root, ns, XFMR_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR_ID, True)
    _add_blackbox(dyd_root, ns, gen_id, gen_lib, par_filename, gen_id, True)

    _add_connection(dyd_root, ns, INT_LINE_ID, LINE_TERMINAL2, PDR_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, INT_BUS_ID, BUS_TERMINAL, INT_LINE_ID, LINE_TERMINAL1)
    _add_connection(dyd_root, ns, XFMR_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, gen_id, gen_terminal, XFMR_ID, XFMR_TERMINAL1, True)


def _create_sauxi_topology(
    dyd_root: etree.Element, ns: str, validation_type: int, par_filename: str
):
    gen_id, gen_lib, gen_terminal = _generator_spec(validation_type)
    _add_blackbox(dyd_root, ns, INT_LINE_ID, LINE_DYNAMIC_MODEL, par_filename, INT_LINE_ID, True)
    _add_blackbox(dyd_root, ns, INT_BUS_ID, BUS_DYNAMIC_MODEL, par_filename, INT_BUS_ID, True)
    _add_blackbox(dyd_root, ns, XFMR_AUX_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR_AUX_ID, True)
    _add_blackbox(dyd_root, ns, AUX_ID, LOAD_DYNAMIC_MODEL, par_filename, AUX_ID, True)
    _add_blackbox(dyd_root, ns, XFMR_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR_ID)
    _add_blackbox(dyd_root, ns, gen_id, gen_lib, par_filename, gen_id, True)

    _add_connection(dyd_root, ns, INT_LINE_ID, LINE_TERMINAL2, PDR_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, INT_BUS_ID, BUS_TERMINAL, INT_LINE_ID, LINE_TERMINAL1)
    _add_connection(dyd_root, ns, XFMR_AUX_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, AUX_ID, LOAD_TERMINAL, XFMR_AUX_ID, XFMR_TERMINAL1)
    _add_connection(dyd_root, ns, gen_id, gen_terminal, XFMR_ID, XFMR_TERMINAL1, True)


def _create_m_topology(
    dyd_root: etree.Element,
    ns: str,
    validation_type: int,
    par_filename: str,
    n_generators: int = 2,
    has_aux: bool = False,
    has_i: bool = False,
):
    """Multi-generator plant (``M`` family), parametrized on ``n_generators``.

    ``n_generators`` generators, each behind its own ``StepUp_Xfmr_<i>``, join at ``Int_Bus`` and
    are grouped by ``Main_Xfmr`` → [``IntNetwork_Line`` if ``+i``] → PDR; ``+Aux`` adds the
    auxiliary load. ``n_generators`` = number of filled ``Zone1<x>`` sheets (default 2 for the
    human-template flow).
    """
    gen_base, gen_lib, gen_terminal = _generator_spec(validation_type)

    if has_i:
        _add_blackbox(dyd_root, ns, INT_LINE_ID, LINE_DYNAMIC_MODEL, par_filename, INT_LINE_ID, True)
    _add_blackbox(dyd_root, ns, MAIN_XFMR_ID, XFMR_DYNAMIC_MODEL, par_filename, MAIN_XFMR_ID, True)
    _add_blackbox(dyd_root, ns, INT_BUS_ID, BUS_DYNAMIC_MODEL, par_filename, INT_BUS_ID, True)
    if has_aux:
        _add_blackbox(dyd_root, ns, XFMR_AUX_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR_AUX_ID)
        _add_blackbox(dyd_root, ns, AUX_ID, LOAD_DYNAMIC_MODEL, par_filename, AUX_ID, True)
    units = []
    for i in range(1, n_generators + 1):
        xfmr_id, gen_id = f"{XFMR_ID}_{i}", f"{gen_base}_{i}"
        _add_blackbox(dyd_root, ns, xfmr_id, XFMR_DYNAMIC_MODEL, par_filename, xfmr_id)
        _add_blackbox(dyd_root, ns, gen_id, gen_lib, par_filename, gen_id, i == 1)
        units.append((xfmr_id, gen_id))

    if has_i:
        _add_connection(dyd_root, ns, INT_LINE_ID, LINE_TERMINAL2, PDR_ID, BUS_TERMINAL)
        _add_connection(dyd_root, ns, MAIN_XFMR_ID, XFMR_TERMINAL2, INT_LINE_ID, LINE_TERMINAL1)
    else:
        _add_connection(dyd_root, ns, MAIN_XFMR_ID, XFMR_TERMINAL2, PDR_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, INT_BUS_ID, BUS_TERMINAL, MAIN_XFMR_ID, XFMR_TERMINAL1)
    if has_aux:
        _add_connection(dyd_root, ns, XFMR_AUX_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
        _add_connection(dyd_root, ns, AUX_ID, LOAD_TERMINAL, XFMR_AUX_ID, XFMR_TERMINAL1)
    for idx, (xfmr_id, gen_id) in enumerate(units):
        _add_connection(dyd_root, ns, xfmr_id, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
        _add_connection(dyd_root, ns, gen_id, gen_terminal, xfmr_id, XFMR_TERMINAL1, idx == 0)


def _group_spacing(xml_text: str) -> str:
    """Insert a blank line at each group boundary (models | connections | voltage | P/Q control),
    matching the examples: before a connection following a model, and before a comment following a
    connection."""

    def kind(line: str) -> str:
        stripped = line.strip()
        if stripped.startswith("<dyn:blackBoxModel"):
            return "model"
        if stripped.startswith("<dyn:connect"):
            return "connect"
        if stripped.startswith("<!--"):
            return "comment"
        return "other"

    spaced = []
    previous = "other"
    for line in xml_text.splitlines():
        current = kind(line)
        if (current == "connect" and previous == "model") or (
            current == "comment" and previous == "connect"
        ):
            spaced.append("")
        spaced.append(line)
        previous = current
    return "\n".join(spaced) + "\n"


def write_producer_dyd(root: etree.Element, path: Path) -> None:
    """Serialize a producer DYD, pretty-printed with blank lines between the logical groups
    (``_group_spacing``)."""
    normalized = etree.fromstring(etree.tostring(root), etree.XMLParser(remove_blank_text=True))
    xml = etree.tostring(
        normalized, encoding="UTF-8", pretty_print=True, xml_declaration=True
    ).decode("utf-8")
    Path(path).write_text(_group_spacing(xml), encoding="utf-8")


def _check_dynamic_models(target: Path, filename: str) -> bool:
    placeholders = (
        dynawo_translator.get_bus_models()
        + dynawo_translator.get_synchronous_machine_models()
        + dynawo_translator.get_power_park_models()
        + dynawo_translator.get_storage_models()
        + dynawo_translator.get_line_models()
        + dynawo_translator.get_load_models()
        + dynawo_translator.get_transformer_models()
        + ["Measurements"]
    )

    producer_dyd_tree = etree.parse(target / filename, etree.XMLParser(remove_blank_text=True))
    producer_dyd_root = producer_dyd_tree.getroot()

    success = True
    dyn_models = []
    ns = etree.QName(producer_dyd_root).namespace
    for bbmodel in producer_dyd_root.iterfind(f"{{{ns}}}blackBoxModel"):
        if bbmodel.get("lib") not in placeholders:
            dyn_models.append(bbmodel.get("lib"))
            success = False

    if not success:
        dycov_logging.get_logger("Create DYD input").error(
            f"The DYD file contains dynamic models that are not supported by the tool.\n"
            f"Please fix {dyn_models}."
        )
    return success


def _create_producer_dyd_file(
    target: Path,
    filename: str,
    topology: str,
    validation_type: int,
    remote_control: bool = True,
    n_generators: int = 2,
) -> None:
    if (target / "Producer.dyd").exists():
        (target / "Producer.dyd").unlink()

    ns = "http://www.rte-france.com/dynawo"
    etree.register_namespace("dyn", "http://www.rte-france.com/dynawo")
    dyd_root = etree.Element(f"{{{ns}}}dynamicModelsArchitecture")
    comment = etree.Comment(f"Topology: {topology}")
    dyd_root.append(comment)

    par_filename = filename.replace(".dyd", ".par")
    if "S".casefold() == topology.casefold():
        _create_s_topology(dyd_root, ns, validation_type, par_filename)
    elif "S+i".casefold() == topology.casefold():
        _create_si_topology(dyd_root, ns, validation_type, par_filename)
    elif "S+Aux".casefold() == topology.casefold():
        _create_saux_topology(dyd_root, ns, validation_type, par_filename)
    elif "S+Aux+i".casefold() == topology.casefold():
        _create_sauxi_topology(dyd_root, ns, validation_type, par_filename)
    elif "M".casefold() == topology.casefold():
        _create_m_topology(dyd_root, ns, validation_type, par_filename, n_generators)
    elif "M+i".casefold() == topology.casefold():
        _create_m_topology(dyd_root, ns, validation_type, par_filename, n_generators, has_i=True)
    elif "M+Aux".casefold() == topology.casefold():
        _create_m_topology(dyd_root, ns, validation_type, par_filename, n_generators, has_aux=True)
    elif "M+Aux+i".casefold() == topology.casefold():
        _create_m_topology(
            dyd_root, ns, validation_type, par_filename, n_generators, has_aux=True, has_i=True
        )
    else:
        raise ValueError(
            "Select one of the 8 available topologies:\n"
            "  - S\n"
            "  - S+i\n"
            "  - S+Aux\n"
            "  - S+Aux+i\n"
            "  - M\n"
            "  - M+i\n"
            "  - M+Aux\n"
            "  - M+Aux+i\n"
        )

    if remote_control:
        for gen_id, gen_terminal in _plant_generators(validation_type, topology, n_generators):
            _add_remote_control(dyd_root, ns, gen_id, gen_terminal)

    write_producer_dyd(dyd_root, target / filename)


def create_producer_dyd_file(
    target: Path,
    topology: str,
    template: str,
    n_generators: int = 2,
) -> None:
    """Create a DYD file in target path with the selected topology.

    Parameters
    ----------
    target: Path
        Target path
    topology: str
        Topology to the DYD file
    template: str
        Input template name:
        * 'performance_SM' if it is electrical performance for Synchronous Machine Model
        * 'performance_PPM' if it is electrical performance for Power Park Module Model
        * 'performance_BESS' if it is electrical performance for Storage Model
        * 'model_PPM' if it is model validation for Power Park Module Model
        * 'model_BESS' if it is model validation for Storage Model
    n_generators: int
        Number of generators for an ``M`` topology (one per ``Zone1<x>`` sheet); default 2. In the
        model flow this yields ``Producer_G1..GN`` in ``Zone1`` and an ``M`` ``Zone3`` with N units.
    """
    if template.startswith("performance"):
        validation_type = PERFORMANCE_SM
        if template == "performance_PPM":
            validation_type = PERFORMANCE_PPM
        elif template == "performance_BESS":
            validation_type = PERFORMANCE_BESS
        _create_producer_dyd_file(
            target, "Producer.dyd", topology, validation_type, n_generators=n_generators
        )

    elif template.startswith("model"):
        validation_type = VALIDATION_PPM
        if template == "model_BESS":
            validation_type = VALIDATION_BESS
        if topology.casefold().startswith("m"):
            for i in range(1, n_generators + 1):
                _create_producer_dyd_file(
                    target / "Zone1", f"Producer_G{i}.dyd", "S", validation_type,
                    remote_control=False,
                )
        else:
            _create_producer_dyd_file(
                target / "Zone1", "Producer.dyd", "S", validation_type, remote_control=False
            )
        _create_producer_dyd_file(
            target / "Zone3", "Producer.dyd", topology, validation_type, n_generators=n_generators
        )

    else:
        raise ValueError("Unsupported template name")


def fill_producer_dyd(dyd_file: Path, libs: dict, terminals: dict, rename: dict = None) -> None:
    """Inject concrete libs and generator terminals into a placeholder DYD (Excel-driven flow).

    Parameters
    ----------
    dyd_file: Path
        DYD file to edit in place.
    libs: dict
        ``{blackBoxModel id -> concrete lib}`` (id after any rename).
    terminals: dict
        ``{generator id -> concrete terminal}``; the generator's terminal and its remote-control
        ports are replaced accordingly.
    rename: dict, optional
        ``{old id -> new id}`` applied first to ids/``parId`` and ``connect`` endpoints (e.g. the
        generic ``Wind_Turbine`` skeleton -> ``PV_Array``).
    """
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(str(dyd_file), parser)
    root = tree.getroot()
    ns = etree.QName(root).namespace

    rename = rename or {}
    for bbmodel in root.iterfind(f"{{{ns}}}blackBoxModel"):
        old = bbmodel.get("id")
        if old in rename:
            if bbmodel.get("parId") == old:
                bbmodel.set("parId", rename[old])
            bbmodel.set("id", rename[old])
    for connect in root.iterfind(f"{{{ns}}}connect"):
        for attr in ("id1", "id2"):
            if connect.get(attr) in rename:
                connect.set(attr, rename[connect.get(attr)])

    for bbmodel in root.iterfind(f"{{{ns}}}blackBoxModel"):
        if bbmodel.get("id") in libs:
            bbmodel.set("lib", libs[bbmodel.get("id")])

    placeholder_ports = _remote_control_ports(PPM_TERMINAL)
    for gen_id, terminal in terminals.items():
        concrete_ports = _remote_control_ports(terminal)
        replacements = {PPM_TERMINAL: terminal}
        for key in placeholder_ports:
            replacements[placeholder_ports[key]] = concrete_ports[key]
        for connect in root.iterfind(f"{{{ns}}}connect"):
            if gen_id in (connect.get("id1"), connect.get("id2")):
                for attr in ("var1", "var2"):
                    if connect.get(attr) in replacements:
                        connect.set(attr, replacements[connect.get(attr)])

    # Drop the "Replace the placeholder ..." instruction comments once filled.
    for comment in root.xpath("//comment()"):
        if (comment.text or "").strip().startswith("Replace"):
            comment.getparent().remove(comment)

    write_producer_dyd(root, dyd_file)


def check_dynamic_models(target: Path, template: str) -> bool:
    """Check whether all dynamic models used in the DYD file are supported by the tool.

    Parameters
    ----------
    target: Path
        Target path
    template: str
        Input template name:
        * 'performance_SM' if it is electrical performance for Synchronous Machine Model
        * 'performance_PPM' if it is electrical performance for Power Park Module Model
        * 'performance_BESS' if it is electrical performance for Storage Model
        * 'model_PPM' if it is model validation for Power Park Module Model
        * 'model_BESS' if it is model validation for Storage Model

    Returns
    -------
    bool
        True if all dynamic models in the DYD file are supported, False otherwise
    """

    if template.startswith("model"):
        dyd_files = list((target / "Zone1").glob("*.[dD][yY][dD]"))
        for dyd_file in dyd_files:
            if not _check_dynamic_models(target / "Zone1", dyd_file.name):
                return False
        check_zone3 = _check_dynamic_models(target / "Zone3", "Producer.dyd")
        return check_zone3
    else:
        return _check_dynamic_models(target, "Producer.dyd")
