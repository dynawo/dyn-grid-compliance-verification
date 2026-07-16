#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from __future__ import annotations

import pypowsybl.network as nw


class PypowsyblNetworkBuilder:
    """
    Builder for creating an electrical network using PyPowsybl.

    This class is responsible for materializing an electrical network
    from already-parsed logical entities. It enforces the construction
    hierarchy required by PyPowsybl:

        Substation → VoltageLevel → Bus → ElectricalEquipment

    Notes
    -----
    - This builder is intentionally minimal.
    - Each `add_*` method is a thin wrapper around the corresponding
      PyPowsybl `create_*` method.
    - The public API exposes explicit, keyword-only signatures.
    - No validation is performed here; PyPowsybl enforces all constraints.
    """

    def __init__(self, network_id: str):
        """
        Initialize a new empty network.

        Parameters
        ----------
        network_id : str
            Identifier of the network.
        """
        self._network = nw.create_empty(network_id)

    # ---------------------------------------------------------------------
    # Structural elements
    # ---------------------------------------------------------------------

    def add_substation(
        self,
        *,
        id: str,
        name: str | None = None,
        country: str | None = None,
        tso: str | None = None,
    ) -> None:
        """
        Add a substation to the network.

        In DyCoV terms, a substation represents a top-level electrical
        container grouping one or more voltage levels.

        Parameters
        ----------
        id : str
            Unique identifier of the substation.
        name : str, optional
            Human-readable name.
        country : str, optional
            Country code (e.g. 'ES', 'FR').
        tso : str, optional
            Transmission System Operator name.

        Notes
        -----
        Substations must be created before any voltage levels.
        """
        args: dict[str, object] = {"id": id}

        if name is not None:
            args["name"] = name
        if country is not None:
            args["country"] = country
        if tso is not None:
            args["TSO"] = tso

        self._network.create_substations(**args)

    def add_voltage_level(
        self,
        *,
        id: str,
        substation_id: str,
        nominal_v: float,
        topology_kind: str,
    ) -> None:
        """
        Add a voltage level to an existing substation.

        A voltage level represents a nominal voltage domain inside a
        substation.

        Parameters
        ----------
        id : str
            Unique identifier of the voltage level.
        substation_id : str
            Identifier of the parent substation.
        nominal_v : float
            Nominal voltage (in kV).
        topology_kind : str
            Topology kind ('BUS_BREAKER' or 'NODE_BREAKER').
        """
        self._network.create_voltage_levels(
            id=id,
            substation_id=substation_id,
            nominal_v=nominal_v,
            topology_kind=topology_kind,
        )

    def add_bus(
        self,
        *,
        id: str,
        voltage_level_id: str,
    ) -> None:
        """
        Add a bus to a voltage level (BUS_BREAKER topology).

        Parameters
        ----------
        id : str
            Unique identifier of the bus.
        voltage_level_id : str
            Identifier of the parent voltage level.

        Notes
        -----
        This method is only valid for BUS_BREAKER topology.
        """
        self._network.create_buses(
            id=id,
            voltage_level_id=voltage_level_id,
        )

    # ---------------------------------------------------------------------
    # Electrical equipment
    # ---------------------------------------------------------------------

    def add_generator(
        self,
        *,
        id: str,
        voltage_level_id: str,
        bus_id: str,
        min_p: float,
        max_p: float,
        target_p: float,
        target_v: float | None = None,
        voltage_regulator_on: bool | None = None,
    ) -> None:
        """
        Add a generator to the network.

        Parameters
        ----------
        id : str
            Unique identifier of the generator.
        voltage_level_id : str
            Voltage level where the generator is connected.
        bus_id : str
            Bus where the generator is connected.
        min_p : float
            Minimum active power (MW).
        max_p : float
            Maximum active power (MW).
        target_p : float
            Active power setpoint (MW).
        target_v : float, optional
            Voltage reference (kV).
        voltage_regulator_on : bool, optional
            Whether voltage regulation is enabled.

        Notes
        -----
        Reactive limits and control models are handled separately
        through PAR/DYD files.
        """
        args: dict[str, object] = {
            "id": id,
            "voltage_level_id": voltage_level_id,
            "bus_id": bus_id,
            "min_p": min_p,
            "max_p": max_p,
            "target_p": target_p,
        }

        if target_v is not None:
            args["target_v"] = target_v
        if voltage_regulator_on is not None:
            args["voltage_regulator_on"] = voltage_regulator_on

        self._network.create_generators(**args)

    def add_load(
        self,
        *,
        id: str,
        voltage_level_id: str,
        bus_id: str,
        p0: float,
        q0: float,
    ) -> None:
        """
        Add a load to the network.

        Parameters
        ----------
        id : str
            Unique identifier of the load.
        voltage_level_id : str
            Voltage level where the load is connected.
        bus_id : str
            Bus where the load is connected.
        p0 : float
            Active power consumption (MW).
        q0 : float
            Reactive power consumption (MVAr).
        """
        self._network.create_loads(
            id=id,
            voltage_level_id=voltage_level_id,
            bus_id=bus_id,
            p0=p0,
            q0=q0,
        )

    def add_line(
        self,
        *,
        id: str,
        voltage_level1_id: str,
        bus1_id: str,
        voltage_level2_id: str,
        bus2_id: str,
        r: float,
        x: float,
        b1: float = 0.0,
        b2: float = 0.0,
        g1: float = 0.0,
        g2: float = 0.0,
        name: str | None = None,
    ) -> None:
        """
        Add a line between two buses (BUS_BREAKER topology).

        A line represents a branch connecting two voltage levels via
        their respective buses.

        Parameters
        ----------
        id : str
            Unique identifier of the line.
        voltage_level1_id : str
            Voltage level on side 1.
        bus1_id : str
            Bus on side 1.
        voltage_level2_id : str
            Voltage level on side 2.
        bus2_id : str
            Bus on side 2.
        r : float
            Line resistance (Ohm).
        x : float
            Line reactance (Ohm).
        b1 : float, optional
            Shunt susceptance on side 1 (S).
        b2 : float, optional
            Shunt susceptance on side 2 (S).
        g1 : float, optional
            Shunt conductance on side 1 (S).
        g2 : float, optional
            Shunt conductance on side 2 (S).
        name : str, optional
            Human-readable name.

        Notes
        -----
        This method is restricted to BUS_BREAKER topology.
        """

        args: dict[str, object] = {
            "id": id,
            "voltage_level1_id": voltage_level1_id,
            "bus1_id": bus1_id,
            "voltage_level2_id": voltage_level2_id,
            "bus2_id": bus2_id,
            "r": r,
            "x": x,
            "b1": b1,
            "b2": b2,
            "g1": g1,
            "g2": g2,
        }

        if name is not None:
            args["name"] = name

        self._network.create_lines(**args)

    def add_two_windings_transformer(
        self,
        *,
        id: str,
        voltage_level1_id: str,
        bus1_id: str,
        voltage_level2_id: str,
        bus2_id: str,
        rated_u1: float,
        rated_u2: float,
        rated_s: float,
        r: float,
        x: float,
        b: float = 0.0,
        g: float = 0.0,
        name: str | None = None,
    ) -> None:
        """
        Add a two-windings transformer to the network (BUS_BREAKER topology).

        A two-windings transformer connects two voltage levels through
        their respective buses and allows voltage adaptation between them.

        Parameters
        ----------
        id : str
            Unique identifier of the transformer.
        voltage_level1_id : str
            Voltage level on side 1.
        bus1_id : str
            Bus on side 1.
        voltage_level2_id : str
            Voltage level on side 2.
        bus2_id : str
            Bus on side 2.
        rated_u1 : float
            Rated voltage on side 1 (kV).
        rated_u2 : float
            Rated voltage on side 2 (kV).
        rated_s : float
            Rated apparent power (MVA).
        r : float
            Transformer resistance (Ohm).
        x : float
            Transformer reactance (Ohm).
        b : float, optional
            Shunt susceptance on side 2 (S).
        g : float, optional
            Shunt conductance on side 2 (S).
        name : str, optional
            Human-readable name.

        Notes
        -----
        This method wraps PyPowsybl `create_2_windings_transformers`
        and is restricted to BUS_BREAKER topology.
        """

        args: dict[str, object] = {
            "id": id,
            "voltage_level1_id": voltage_level1_id,
            "bus1_id": bus1_id,
            "voltage_level2_id": voltage_level2_id,
            "bus2_id": bus2_id,
            "rated_u1": rated_u1,
            "rated_u2": rated_u2,
            "rated_s": rated_s,
            "r": r,
            "x": x,
            "b": b,
            "g": g,
        }

        if name is not None:
            args["name"] = name

        self._network.create_2_windings_transformers(**args)

    def add_boundary_line(
        self,
        *,
        id: str,
        voltage_level_id: str,
        bus_id: str,
        p0: float,
        q0: float,
        r: float,
        x: float,
        g: float = 0.0,
        b: float = 0.0,
        pairing_key: str | None = None,
        name: str | None = None,
    ) -> None:
        """
        Add a boundary line to the network (BUS_BREAKER topology).

        A boundary line represents an external network connection modeled
        as an equivalent injection connected to a bus.

        Parameters
        ----------
        id : str
            Unique identifier of the boundary line.
        voltage_level_id : str
            Voltage level where the boundary line is connected.
        bus_id : str
            Bus where the boundary line is connected.
        p0 : float
            Active power consumption (MW).
        q0 : float
            Reactive power consumption (MVar).
        r : float
            Resistance (Ohm).
        x : float
            Reactance (Ohm).
        g : float, optional
            Shunt conductance (S).
        b : float, optional
            Shunt susceptance (S).
        pairing_key : str, optional
            Pairing key for future tie-line creation.
        name : str, optional
            Human-readable name.

        Notes
        -----
        This method wraps PyPowsybl `create_dangling_lines` and does not
        handle the optional generation part. When boundary lines are supported in PyPowsybl,
        this method should be updated to call `create_boundary_lines` instead.
        """

        args: dict[str, object] = {
            "id": id,
            "voltage_level_id": voltage_level_id,
            "bus_id": bus_id,
            "p0": p0,
            "q0": q0,
            "r": r,
            "x": x,
            "g": g,
            "b": b,
        }

        if pairing_key is not None:
            args["pairing_key"] = pairing_key
        if name is not None:
            args["name"] = name

        # Pypowsybl 1.14 works with dangling lines, boundary lines will appear in next release.
        # When boundary lines are supported, this method should be updated to call
        # `create_boundary_lines` instead.
        self._network.create_dangling_lines(**args)

    # ---------------------------------------------------------------------
    # Finalization
    # ---------------------------------------------------------------------

    def build(self):
        """
        Finalize and return the PyPowsybl Network.

        Returns
        -------
        pypowsybl.network.Network
            The constructed electrical network.
        """
        return self._network
