# About the import of Reference Curves


Throughout the documentation of this tool we use the term _"Reference
Curves"_ to refer generically to any signals provided by the user,
which are typically produced by other tools (such as Eurostag,
DigSilent, PSS/E, etc.) or even obtained experimentally by any
recording means.  This is just to differentiate these curves from any
other curves produced by the Tool itself, by running Dynawo.

This Python module imports such Reference Curves. 


## Supported formats

The following formats are supported (but please read below the critical
information that is needed in addition):

  * COMTRADE:
     - All revisions of the COMTRADE standard up to C37.111-2013 are supported.
     - The curves can be provided either as a pair of DAT+CFG files (both
       must have the same name and differ only in their extension), or a
       single CFF file.

  * EUROSTAG:
     - The EXP ascii format is supported.

  * CSV:
     - Standard comma-separated-values text files are supported, but the
       field separator _must_ be the character ';'.
     - Additionally, there must be a column for the simulation time
       (see below the additional info needed).
       


## Supported types of signal (EMT vs. dycov)

The tool supports:
  * EMT-type signals in the "raw" three-phase abc frame
  * dycov-type signals, i.e. root-mean-square signals

Internally the tool converts all EMT signals to the dycov of their
positive sequence.



## CRITICAL: additional information required (DICT file)

**Regardless** of the curve format, each supplied file(s) must be
accompanied by a corresponding DICT file (same file name, but using
the `*.DICT` extension). This file is needed because it provides us
with two kinds of information that cannot possibly be inferred from
the curve files:
  * The mapping between the columns in the file and the signals
    expected by the corresponding DTR Fiche.
  * Certain simulation parameters used to generate the curves (these
    depend on the particular DTR Fiche).

The DICT file should be written in the well-known "INI" format. More
precisely, the file is interpreted using the
[`configparser`](https://docs.python.org/3/library/configparser.html)
module from the Python Standard Library. The detailed syntax is
fully described in [its
documentation](https://docs.python.org/3/library/configparser.html#supported-ini-file-structure).

The DICT file is made up of the following sections:

  * **`Curves-Metadata`**: This section reports certain parameters
    used in the dynamic simulation, which are required in order to
    perform the DTR tests. Their number varies, as this depends on the
    specific DTR Fiche (the provided DICT _templates_ will clearly
    show which ones are needed in each case). Here are some examples:
      - `sim_type`: type of simulation, EMT or dycov.
      - `sim_t_event`: Instant of time at wich an event takes place in
        the simulation (failure in a equipment,
        connection/disconnection of a equipment, etc.)
      - `fault_duration`: duration of the fault in miliseconds (in
        case the event is a fault).
      - `frequency_sampling`:sampling rate (when a timestamp data
        column is not present).

  * **`Curves-Dictionary`**: This section contains the mapping between
    the signals expected by the corresponding DTR Fiche (left-hand
    side value) and the columns in the reference curves file
    (right-hand side value). Any additional columns in the curves file
    will be ignored. For file formats without labeled columns, such as
    a CSV file without headers, the column identifier will be just the
    column number (numbering starting with 1).


**For each DTR Fiche, DICT _templates_ are provided, complete with
comments, so that the user knows which parameters are needed and which
signals need to be mapped in each case.**


Example of DICT file for FicheI3SM:
```
[Curves-Metadata]
sim_type = emt
sim_t_event = 20.0
fault_duration = 0.0
frequency_sampling = 15

[Curves-Dictionary]
time = time
LineAll_line_P2Pu = Line_P
LineAll_line_Q2Pu = Line_Q
BusPDR_bus_terminal_V_a = Bus_V_a
BusPDR_bus_terminal_V_b = Bus_V_b
BusPDR_bus_terminal_V_c = Bus_V_c
Transformer_transformer_terminal2_V = Transformer_V
SynchronousGenerator_generator_omegaPu = SynchronousGenerator_omega
SynchronousGenerator_generator_theta = SynchronousGenerator_theta
SynchronousGenerator_generator_thetaInternal = SynchronousGenerator_thetaInternal
SynchronousGenerator_voltageRegulator_UsRefPu = SynchronousGenerator_UsRef
SynchronousGenerator_generator_UStatorPu_value = SynchronousGenerator_UStator
```
