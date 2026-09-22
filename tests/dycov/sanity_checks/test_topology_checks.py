#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023-2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import pytest

from dycov.model.parameters import GenParams, LineParams, LoadParams, Terminal, XfmrParams
from dycov.sanity_checks import topology_checks

# -------------------------
# Helper functions
# -------------------------


def make_generator(gen_type="S", converter_lv_control=True):
    if gen_type == "S":
        return [
            GenParams(
                id="Synch_Gen",
                lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a",
                terminals=(Terminal(connected_equipment=""),),
                s_nom=90,
                i_max=100.0,
                par_id="",
                p=0.1,
                q=0.05,
                voltage_droop=None,
                use_voltage_droop=False,
                converter_lv_control=converter_lv_control,
            )
        ]
    elif gen_type == "M":
        return [
            GenParams(
                id="Wind_Turbine1",
                lib="WTG4AWeccCurrentSource",
                terminals=(Terminal(connected_equipment=""),),
                s_nom=90,
                i_max=100.0,
                par_id="",
                p=0.1,
                q=0.05,
                voltage_droop=None,
                use_voltage_droop=False,
                converter_lv_control=converter_lv_control,
            ),
            GenParams(
                id="Wind_Turbine2",
                lib="WTG4AWeccCurrentSource",
                terminals=(Terminal(connected_equipment=""),),
                s_nom=90,
                i_max=120.0,
                par_id="",
                p=0.12,
                q=0.025,
                voltage_droop=None,
                use_voltage_droop=False,
                converter_lv_control=converter_lv_control,
            ),
        ]


def make_group_xfmr(generators=None):
    """Builds the Zone-1 group transformer, referencing the generating unit."""
    gen_id = generators[0].id if generators else ""
    return [
        XfmrParams(
            id="Group_Xfmr",
            lib=None,
            r=0.0003,
            x=0.0268,
            b=0.0,
            g=0.0,
            r_tfo=0.9574,
            alpha_tfo=0.0,
            par_id="",
            terminals=(
                Terminal(connected_equipment=gen_id),
                Terminal(connected_equipment=""),
            ),
        )
    ]


def make_main_transformer():
    return XfmrParams(
        id="Main_Xfmr",
        lib=None,
        r=0.0003,
        x=0.0268,
        b=0.0,
        g=0.0,
        r_tfo=0.9574,
        alpha_tfo=0.0,
        par_id="",
        terminals=(Terminal(connected_equipment=""), Terminal(connected_equipment="")),
    )


def make_auxiliary_load():
    return LoadParams(
        id="Aux_Load",
        lib=None,
        par_id="",
        terminals=(Terminal(connected_equipment=""),),
        p=0.1,
        q=0.05,
        u=1.0,
        u_phase=0.0,
        alpha=None,
        beta=None,
    )


def make_auxiliary_transformer():
    return XfmrParams(
        id="AuxLoad_Xfmr",
        lib=None,
        r=0.0003,
        x=0.0268,
        b=0.0,
        g=0.0,
        r_tfo=0.9574,
        alpha_tfo=0.0,
        par_id="",
        terminals=(Terminal(connected_equipment=""), Terminal(connected_equipment="")),
    )


def make_internal_line():
    return LineParams(
        id="IntNetwork_Line",
        lib=None,
        r=0.01,
        x=0.01,
        b=0.1,
        g=0.3,
        par_id="",
        terminals=(Terminal(connected_equipment=""), Terminal(connected_equipment="")),
    )


ZONE1 = 1
ZONE3 = 3

TOPOLOGIES = {
    "S": (1, False, False),
    "S+i": (1, False, True),
    "S+Aux": (1, True, False),
    "S+Aux+i": (1, True, True),
    "M": (2, False, False),
    "M+i": (2, False, True),
    "M+Aux": (2, True, False),
    "M+Aux+i": (2, True, True),
}


def _zone3_equipment(topology: str) -> dict:
    """Builds the equipment the catalog expects for a Zone-3 topology."""
    units, aux_load, int_line = TOPOLOGIES[topology]
    return {
        "generators": make_generator("S" if units == 1 else "M"),
        "transformers": [],
        "auxiliary_load": make_auxiliary_load() if aux_load else None,
        "auxiliary_transformer": make_auxiliary_transformer() if aux_load else None,
        "transformer": make_main_transformer(),
        "internal_line": make_internal_line() if int_line else None,
    }


def _check_zone3(topology: str, **overrides) -> None:
    topology_checks.check_topology(ZONE3, topology, **{**_zone3_equipment(topology), **overrides})


def _check_zone1(generators, transformers) -> None:
    topology_checks.check_topology(ZONE1, "S", generators, transformers, None, None, None, None)


# -------------------------
# Tests: Zone 3 topologies
# -------------------------


@pytest.mark.parametrize("topology", list(TOPOLOGIES))
def test_check_topology_accepts_the_catalog_equipment(topology):
    _check_zone3(topology)


@pytest.mark.parametrize("topology", list(TOPOLOGIES))
def test_check_topology_requires_the_main_transformer(topology):
    """The main transformer is now the block adjacent to the PDR in every topology."""
    with pytest.raises(ValueError) as e:
        _check_zone3(topology, transformer=None)

    assert "Main_Xfmr" in e.value.args[0]


@pytest.mark.parametrize("topology", list(TOPOLOGIES))
def test_check_topology_rejects_a_unit_transformer(topology):
    """In Zone 3 the group transformer of each unit is part of its dynamic model."""
    with pytest.raises(ValueError) as e:
        _check_zone3(topology, transformers=make_group_xfmr())

    assert "generating units" in e.value.args[0]


@pytest.mark.parametrize("topology", list(TOPOLOGIES))
def test_check_topology_rejects_the_wrong_internal_line_presence(topology):
    _, _, int_line = TOPOLOGIES[topology]
    swapped = None if int_line else make_internal_line()

    with pytest.raises(ValueError) as e:
        _check_zone3(topology, internal_line=swapped)

    assert "IntNetwork_Line" in e.value.args[0]


@pytest.mark.parametrize("topology", list(TOPOLOGIES))
def test_check_topology_rejects_the_wrong_auxiliary_presence(topology):
    _, aux_load, _ = TOPOLOGIES[topology]
    swapped_load = None if aux_load else make_auxiliary_load()
    swapped_xfmr = None if aux_load else make_auxiliary_transformer()

    with pytest.raises(ValueError) as e:
        _check_zone3(topology, auxiliary_load=swapped_load, auxiliary_transformer=swapped_xfmr)

    assert "Aux_Load" in e.value.args[0]


def test_check_topology_rejects_multiple_units_in_a_single_topology():
    with pytest.raises(ValueError) as e:
        _check_zone3("S", generators=make_generator("M"))

    assert "A single generator is expected." in e.value.args[0]


def test_check_topology_rejects_a_single_unit_in_a_multiple_topology():
    with pytest.raises(ValueError) as e:
        _check_zone3("M", generators=make_generator("S"))

    assert "Multiple generators are expected." in e.value.args[0]


def test_check_topology_rejects_an_unknown_topology():
    with pytest.raises(ValueError) as e:
        topology_checks.check_topology(
            ZONE3, "S+Main", make_generator("S"), [], None, None, make_main_transformer(), None
        )

    assert "Select one of the 8 available topologies" in e.value.args[0]


# -------------------------
# Tests: Zone 1, group transformer tied to ConverterLVControl
# -------------------------


def test_check_topology_zone1_requires_the_group_xfmr_when_lv_control_is_true():
    generators = make_generator("S", converter_lv_control=True)

    _check_zone1(generators, make_group_xfmr(generators))


def test_check_topology_zone1_omits_the_group_xfmr_when_lv_control_is_false():
    """The converter already reaches the internal node through its own transformer."""
    generators = make_generator("S", converter_lv_control=False)

    _check_zone1(generators, [])


def test_check_topology_zone1_rejects_a_missing_group_xfmr_when_lv_control_is_true():
    generators = make_generator("S", converter_lv_control=True)

    with pytest.raises(ValueError) as e:
        _check_zone1(generators, [])

    assert "ConverterLVControl = true" in e.value.args[0]


def test_check_topology_zone1_rejects_a_group_xfmr_when_lv_control_is_false():
    """Two transformers in series: the converter's own and the external one."""
    generators = make_generator("S", converter_lv_control=False)

    with pytest.raises(ValueError) as e:
        _check_zone1(generators, make_group_xfmr(generators))

    assert "ConverterLVControl = false" in e.value.args[0]


def test_check_topology_zone1_rejects_the_main_transformer():
    """Zone 1 stops at the internal node, so it has no transformer towards the PDR."""
    generators = make_generator("S", converter_lv_control=True)

    with pytest.raises(ValueError) as e:
        topology_checks.check_topology(
            ZONE1,
            "S",
            generators,
            make_group_xfmr(generators),
            None,
            None,
            make_main_transformer(),
            None,
        )

    assert "Main_Xfmr" in e.value.args[0]
