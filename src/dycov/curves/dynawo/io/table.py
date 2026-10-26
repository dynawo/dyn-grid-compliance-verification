#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import math
import re
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.curves.curves import ProducerCurves
from dycov.curves.dynawo.dictionary.translator import dynawo_translator
from dycov.curves.dynawo.io.file_variables import FileVariables
from dycov.files import replace_placeholders
from dycov.logging import dycov_logging
from dycov.model.parameters import GenInit

_TABLE_FILES = ("TableInfiniteBus.txt", "TableVariableImpedance.txt", "TableSwitchedLine.txt")
_TWO_COLUMN_TABLE = re.compile(r"^\s*double\s+(\w+)\s*\(\s*\d+\s*,\s*2\s*\)\s*$")
# The phase is quadratic over a ramp of the frequency: sampled every 10 ms, the linear
# interpolation of the table stays within 0.2 mrad of it for the steepest ramp of the Fiche I18
_PHASE_SAMPLING = 0.01


def _read_two_column_tables(text: str) -> dict:
    """The rows of every two-column table of a Dynawo table file, by table name."""
    tables = {}
    name = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("double"):
            header = _TWO_COLUMN_TABLE.match(line)
            name = header.group(1) if header else None
            if name:
                tables[name] = []
        elif name and stripped and not stripped.startswith("#"):
            time, value = stripped.split()
            tables[name].append((float(time), float(value)))
        else:
            name = None
    return tables


def _replace_table(text: str, name: str, rows: list) -> str:
    """The table file with the rows of one of its two-column tables replaced."""
    lines = []
    replacing = False
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(rf"^\s*double\s+{name}\s*\(", line):
            lines.append(f"double {name}({len(rows)},2)")
            lines.extend(f"{time:.6f} {value:.9f}" for time, value in rows)
            replacing = True
            continue
        if replacing and stripped and not stripped.startswith(("#", "double")):
            continue
        replacing = False
        lines.append(line)
    return "\n".join(lines) + "\n"


def _phase_of_frequency(profile: list, time: float, omega_nom: float) -> float:
    """The angle a grid turns by until the given time, relative to the nominal frequency,
    following a piecewise linear frequency profile in pu."""
    phase = 0.0
    for (t0, w0), (t1, w1) in zip(profile, profile[1:]):
        if time <= t0:
            break
        elapsed = min(time, t1) - t0
        slope = (w1 - w0) / (t1 - t0) if t1 > t0 else 0.0
        phase += omega_nom * ((w0 - 1.0) * elapsed + slope * elapsed**2 / 2)
    return phase


def _values_at(rows: list, time: float) -> tuple[float, float]:
    """The values of a table just before and just after a time, which differ where it steps."""
    at_time = [value for row_time, value in rows if row_time == time]
    if at_time:
        return at_time[0], at_time[-1]
    for (t0, v0), (t1, v1) in zip(rows, rows[1:]):
        if t0 < time < t1:
            value = v0 + (v1 - v0) * (time - t0) / (t1 - t0)
            return value, value
    value = rows[-1][1] if time > rows[-1][0] else rows[0][1]
    return value, value


def _sampling_times(profile: list) -> list:
    """The times at which the phase of a frequency profile is tabulated: the ends of each segment,
    and every sampling interval along a ramp."""
    times = {profile[0][0]}
    for (t0, w0), (t1, w1) in zip(profile, profile[1:]):
        times.add(t1)
        if w1 != w0:
            steps = int((t1 - t0) / _PHASE_SAMPLING)
            times.update(t0 + step * _PHASE_SAMPLING for step in range(1, steps))
    return sorted({round(time, 6) for time in times})


def _phase_following_frequency(phase_rows: list, frequency_rows: list, omega_nom: float) -> list:
    """The rows of the phase of the grid with the angle its frequency profile turns it by added
    to its own steps."""
    times = sorted(set(_sampling_times(frequency_rows)) | {time for time, _ in phase_rows})
    rows = []
    for time in times:
        before, after = _values_at(phase_rows, time)
        turned = _phase_of_frequency(frequency_rows, time, omega_nom)
        rows.append((time, turned + before))
        if after != before:
            rows.append((time, turned + after))
    return rows


class TableFile(FileVariables):
    """
    Manages the completion of the 'TableInfiniteBus.txt' file for Dynawo simulations.

    This class extends FileVariables to handle specific variables and
    placeholders related to the infinite bus parameters and event timing,
    which are crucial for defining simulation conditions.
    """

    def __init__(self, dynawo_curves: ProducerCurves, bm_section: str, oc_section: str):
        """
        Initializes the TableFile with necessary Dynawo curve information and sections.

        Parameters
        ----------
        dynawo_curves: ProducerCurves
            An object containing Dynawo producer curve data.
        bm_section: str
            The section identifier for Balance Management.
        oc_section: str
            The section identifier for Operational Contingency.
        """
        tool_variables = [
            "start_event",
            "end_event",
            "bus_u0pu",
            "bus_upu",
            "end_freq",
            "bus_uphase",
            "bus_omega0pu",
            "bus_omegapu",
            "end_frequency_settling",
        ]
        super().__init__(
            tool_variables,
            dynawo_curves,
            bm_section,
            oc_section,
        )

    def __grid_event(self, key: str) -> float:
        """The size of an event of the grid the Event section of the test declares, 0 when it
        declares none."""
        if not config.has_option(self._event_section, key):
            return 0.0
        value = self._dynawo_curves.obtain_value(
            config.get_value(self._event_section, key), origin=(self._event_section, key)
        )
        return float(value)

    def __complete_grid_events(
        self, variables_dict: dict, tso_gen: GenInit, event_params: dict
    ) -> None:
        """The steps of the voltage and of its phase, and the frequency profile, of the grid.

        Dynawo initialises a model at the nominal frequency, so a profile that starts from
        another one reaches it with a ramp over the first half of the time before the event,
        which leaves the second half for the unit to settle.
        """
        variables_dict["bus_upu"] = tso_gen.u0 + self.__grid_event("grid_voltage_step")
        variables_dict["bus_uphase"] = self.__grid_event("grid_phase_jump")

        f_nom = config.get_float("Dynawo", "f_nom", 50.0)
        frequency0 = self.__grid_event("grid_frequency0") or f_nom
        rocof = self.__grid_event("grid_rocof")
        frequency_end = frequency0 + rocof * event_params["duration_time"]
        variables_dict["bus_omega0pu"] = frequency0 / f_nom
        variables_dict["bus_omegapu"] = frequency_end / f_nom
        simulation_start = config.get_float("Dynawo", "simulation_start", 0.0)
        variables_dict["end_frequency_settling"] = (
            simulation_start + event_params["start_time"]
        ) / 2

    def __complete_Xv_entries(self, variables_dict, event_params):
        list_Xv = [s for s in event_params.keys() if s.startswith("Xv_")]
        for Xv in list_Xv:
            variables_dict[Xv] = event_params[Xv]

    def __complete_file(
        self, working_oc_dir: Path, tso_gen: GenInit, event_params: dict, filename: str
    ) -> None:
        variables_dict = replace_placeholders.get_all_variables(working_oc_dir, filename)

        variables_dict["start_event"] = event_params["start_time"]
        variables_dict["end_event"] = event_params["start_time"] + event_params["duration_time"]

        variables_dict["bus_u0pu"] = tso_gen.u0
        self.__complete_grid_events(variables_dict, tso_gen, event_params)

        # Adjust bus voltage or frequency based on the event's connection type
        if event_params["connect_to"] == "VoltageSetpointPu":
            variables_dict["bus_upu"] = tso_gen.u0 + float(event_params["step_value"])
        elif event_params["connect_to"] == "NetworkFrequencyPu":
            variables_dict["end_freq"] = 1.0 + float(event_params["step_value"])

        # Complete any additional parameters using the inherited method
        self.__complete_Xv_entries(variables_dict, event_params)
        self.complete_parameters(variables_dict, event_params)

        # Replace placeholders in the TableInfiniteBus file with the calculated variables
        replace_placeholders.dump_file(working_oc_dir, filename, variables_dict)
        self.__turn_phase_with_frequency(working_oc_dir / filename)

        # Post-procesado (configurable por evento)
        enabled = config.get_boolean("Dynawo", "transition_enabled", False)
        points = config.get_int("Dynawo", "transition_points", 3)
        half_width = config.get_float("Dynawo", "transition_half_width", 0.01)
        dycov_logging.get_logger("TableFile").debug(
            f"Post-processing {filename} with smoothing enabled={enabled}, "
            f"points={points}, half_width={half_width}"
        )
        self.__smooth_duplicate_timestamps(
            working_oc_dir / filename,
            enabled=enabled,
            points=points,
            half_width=half_width,
        )

    def __turn_phase_with_frequency(self, table_path: Path) -> None:
        """A unit that takes no frequency reference sees the frequency of the grid only as the
        rotation of its voltage, so for such a unit the phase of the infinite bus turns with the
        frequency profile of the test."""
        text = table_path.read_text(encoding="utf-8")
        tables = _read_two_column_tables(text)
        frequency_rows = tables.get("TableOmegaRefPu")
        phase_rows = tables.get("TableUPhase")
        if not frequency_rows or not phase_rows:
            return
        if all(omega == 1.0 for _, omega in frequency_rows):
            return
        if self.__unit_takes_frequency_reference():
            return

        dycov_logging.get_logger("TableFile").debug(
            "The unit takes no frequency reference: the phase of the infinite bus turns with the "
            "frequency of the test"
        )
        omega_nom = 2 * math.pi * config.get_float("Dynawo", "f_nom", 50.0)
        rows = _phase_following_frequency(phase_rows, frequency_rows, omega_nom)
        table_path.write_text(_replace_table(text, "TableUPhase", rows), encoding="utf-8")

    def __unit_takes_frequency_reference(self) -> bool:
        return any(
            dynawo_translator.get_dynawo_variable(generator.lib, "NetworkFrequencyReference")[1]
            for generator in self._dynawo_curves.get_producer().generators
        )

    def __smooth_duplicate_timestamps(
        self,
        file_path: Path,
        enabled: bool,
        points: int,
        half_width: float,
        float_tol: float = 1e-9,
    ) -> None:
        """
        Post-processes a Dynawo table file containing one or more blocks of:
            # comments
            blank lines
            double <Name>(N,K)
            <data rows>

        For each block, if smoothing is enabled, replaces any consecutive
        rows where time t is the same and the value changes, with `points`
        interpolated rows spaced in [-half_width, +half_width].

        Supports:
        - comment lines
        - blank lines
        - tables with 2 or 3 columns
        - multiple tables inside a single file
        - header update per table
        """

        if not enabled or points < 3 or points % 2 == 0 or half_width <= 0:
            return

        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()

        # Regex for table header
        header_re = re.compile(r"^\s*double\s+([A-Za-z0-9_]+)\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*$")

        out_lines = []
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]

            # Preserve comments and blank lines
            if not line.strip() or line.strip().startswith("#"):
                out_lines.append(line)
                i += 1
                continue

            # Check header
            m = header_re.match(line)
            if not m:
                # normal non-header line outside a table → copy as-is
                out_lines.append(line)
                i += 1
                continue

            table_name = m.group(1)
            # original_N = int(m.group(2))     # not used
            ncols = int(m.group(3))

            # Copy header now; N will be updated later
            header_index = len(out_lines)
            out_lines.append(None)  # placeholder

            i += 1

            # Collect all data lines until next header/comment/EOF
            data_rows = []
            while i < n:
                ln = lines[i]
                if header_re.match(ln):
                    break
                if ln.strip().startswith("#"):
                    break
                if not ln.strip():  # blank line marks end of table block
                    break
                data_rows.append(ln)
                i += 1

            parsed = []
            for row in data_rows:
                parts = row.split()
                if len(parts) != ncols:
                    parsed = None
                    break
                try:
                    t = float(parts[0])
                    if ncols == 2:
                        v = float(parts[1])
                        parsed.append((t, None, v))
                    elif ncols == 3:
                        c2 = parts[1]
                        v = float(parts[2])
                        parsed.append((t, c2, v))
                except ValueError:
                    parsed = None
                    break

            # If parsing failed → emit original block
            if parsed is None:
                # rewrite original header and data rows
                out_lines[header_index] = line
                out_lines.extend(data_rows)
                if i < n and not lines[i].strip():
                    out_lines.append("")  # preserve blank
                    i += 1
                continue

            new_rows = self.__interpolate_duplicate_rows(
                parsed, points, half_width, float_tol, ncols
            )

            out_lines[header_index] = f"double {table_name}({len(new_rows)},{ncols})"
            out_lines.extend(new_rows)

            # Ensure blank line after each table
            out_lines.append("")

            # If next line is blank, skip it to avoid duplicates
            if i < n and not lines[i].strip():
                i += 1

        file_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    def __interpolate_duplicate_rows(
        self, parsed: list, points: int, half_width: float, float_tol: float, ncols: int
    ) -> list:
        """
        Rebuilds the table rows, replacing each pair of consecutive rows that share the same
        timestamp but change value with `points` interpolated rows spaced in
        [-half_width, +half_width].
        """
        new_rows = []
        k = 0
        while k < len(parsed):
            if k + 1 < len(parsed):
                t1, c21, v1 = parsed[k]
                t2, c22, v2 = parsed[k + 1]
                if abs(t1 - t2) <= float_tol and v1 != v2:
                    pos = [(-1.0 + 2.0 * j / (points - 1)) for j in range(points)]
                    times = [t1 + half_width * p for p in pos]
                    vals = [v1 + (v2 - v1) * (j / (points - 1)) for j in range(points)]

                    if ncols == 2:
                        for tt, vv in zip(times, vals):
                            new_rows.append(f"{tt:.6f} {vv:.6f}")
                    else:
                        for tt, vv in zip(times, vals):
                            new_rows.append(f"{tt:.6f} {c21} {vv:.6f}")

                    k += 2
                    continue

            t, c2, v = parsed[k]
            if ncols == 2:
                new_rows.append(f"{t:.6f} {v:.6f}")
            else:
                new_rows.append(f"{t:.6f} {c2} {v:.6f}")
            k += 1

        return new_rows

    def complete_file(self, working_oc_dir: Path, tso_gen: GenInit, event_params: dict) -> None:
        """
        Replaces the file placeholders in the 'TableInfiniteBus.txt' file with the corresponding
        values.

        Parameters
        ----------
        working_oc_dir: Path
            The working directory where the 'TableInfiniteBus.txt' file is located.
        tso_gen: GenInit
            Parameters for the initialization of the TSO's bus side (P, Q, U, angle).
        event_params: dict
            A dictionary containing event-specific parameters, including start time,
            duration, step value, and connection type.
        """
        for table in _TABLE_FILES:
            if (working_oc_dir / table).exists():
                self.__complete_file(working_oc_dir, tso_gen, event_params, table)
