#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import re
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.curves.curves import ProducerCurves
from dycov.curves.dynawo.io.file_variables import FileVariables
from dycov.files import replace_placeholders
from dycov.logging.logging import dycov_logging
from dycov.model.parameters import Gen_init


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
        ]
        super().__init__(
            tool_variables,
            dynawo_curves,
            bm_section,
            oc_section,
        )

    def __complete_Xv_entries(self, variables_dict, event_params):
        list_Xv = [s for s in event_params.keys() if s.startswith("Xv_")]
        for Xv in list_Xv:
            variables_dict[Xv] = event_params[Xv]

    def __complete_file(
        self, working_oc_dir: Path, rte_gen: Gen_init, event_params: dict, filename: str
    ) -> None:
        # Retrieve all existing variables from the TXT file
        variables_dict = replace_placeholders.get_all_variables(working_oc_dir, filename)

        # Update event timing variables
        variables_dict["start_event"] = event_params["start_time"]
        variables_dict["end_event"] = event_params["start_time"] + event_params["duration_time"]

        # Set the initial per-unit voltage for the bus
        variables_dict["bus_u0pu"] = rte_gen.U0

        # Adjust bus voltage or frequency based on the event's connection type
        if event_params["connect_to"] == "AVRSetpointPu":
            variables_dict["bus_upu"] = rte_gen.U0 + float(event_params["step_value"])
        elif event_params["connect_to"] == "NetworkFrequencyPu":
            variables_dict["end_freq"] = 1.0 + float(event_params["step_value"])

        # Complete any additional parameters using the inherited method
        self.__complete_Xv_entries(variables_dict, event_params)
        self.complete_parameters(variables_dict, event_params)

        # Replace placeholders in the TableInfiniteBus file with the calculated variables
        replace_placeholders.dump_file(working_oc_dir, filename, variables_dict)

        # Post-procesado (configurable por evento)
        enabled = config.get_boolean("Dynawo", "transition_enabled", False)
        points = config.get_int("Dynawo", "transition_points", 3)
        half_width = config.get_float("Dynawo", "transition_half_width", 0.01)
        dycov_logging.debug(
            f"Post-processing {filename} with smoothing enabled={enabled}, points={points}, half_width={half_width}"
        )
        self.__smooth_duplicate_timestamps(
            working_oc_dir / filename,
            enabled=enabled,
            points=points,
            half_width=half_width,
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

            # Extract header info
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
                l = lines[i]
                if header_re.match(l):
                    break
                if l.strip().startswith("#"):
                    break
                if not l.strip():  # blank line marks end of table block
                    break
                data_rows.append(l)
                i += 1

            # Parse data rows
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

            # SMOOTHING LOGIC ----------------------------------------------------
            new_rows = []
            k = 0
            while k < len(parsed):
                if k + 1 < len(parsed):
                    t1, c21, v1 = parsed[k]
                    t2, c22, v2 = parsed[k + 1]
                    if abs(t1 - t2) <= float_tol and v1 != v2:
                        # Interpolate
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

                # default copy
                t, c2, v = parsed[k]
                if ncols == 2:
                    new_rows.append(f"{t:.6f} {v:.6f}")
                else:
                    new_rows.append(f"{t:.6f} {c2} {v:.6f}")
                k += 1

            # Write updated header
            out_lines[header_index] = f"double {table_name}({len(new_rows)},{ncols})"
            out_lines.extend(new_rows)

            # Ensure blank line after each table
            out_lines.append("")

            # If next line is blank, skip it to avoid duplicates
            if i < n and not lines[i].strip():
                i += 1

        # Save final result
        file_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    def complete_file(self, working_oc_dir: Path, rte_gen: Gen_init, event_params: dict) -> None:
        """
        Replaces the file placeholders in the 'TableInfiniteBus.txt' file with the corresponding
        values.

        Parameters
        ----------
        working_oc_dir: Path
            The working directory where the 'TableInfiniteBus.txt' file is located.
        rte_gen: Gen_init
            Parameters for the initialization of the TSO's bus side (P, Q, U, angle).
        event_params: dict
            A dictionary containing event-specific parameters, including start time,
            duration, step value, and connection type.
        """
        if (working_oc_dir / "TableInfiniteBus.txt").exists():
            self.__complete_file(working_oc_dir, rte_gen, event_params, "TableInfiniteBus.txt")
        if (working_oc_dir / "TableVariableImpedance.txt").exists():
            self.__complete_file(
                working_oc_dir, rte_gen, event_params, "TableVariableImpedance.txt"
            )
