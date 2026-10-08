.. _pcs-description:

=========================
PCS description reference
=========================

A PCS is entirely described by one ``PCSDescription.ini``: the benchmarks it
runs, the operating conditions of each one, the compliance tests it applies
and the figures of its report. This chapter is the reference of that file,
key by key and kind of test by kind of test, so that a PCS can be read,
adapted or written from scratch. The compliance tests themselves are
described in the *Compliance tests* chapter of the user manual, and the
file a producer delivers for PCS F16 in its *The F16 declaration file*
chapter.


Where a description lives
-------------------------

DyCoV reads a PCS from up to three descriptions, which patch one another:

* the description **shipped with the tool**, under
  ``src/dycov/templates/PCS/<workflow>/<technology>/<PCS>/PCSDescription.ini``
  (``model`` or ``performance``; ``PPM``, ``BESS`` or ``SM``);
* the description a **user** writes under the same relative path of the
  configuration directory, ``~/.config/dycov/templates/PCS/...``, which only
  needs to carry the sections and keys it changes;
* for a PCS whose tests the producer declares (PCS F16), the
  ``<fiche>Description.ini`` **delivered with the reference curves**
  (``F16Description.ini``), which takes the place of the user description of
  the PCS it names in its ``[PCS-Benchmarks]``.

A key is read from the first of these that defines it, then from
``config.ini`` and the packaged defaults; :doc:`configuration` gives
the precedence rules. A new PCS can be created entirely in the configuration directory: a
directory named after it with a complete ``PCSDescription.ini`` and, under
``templates/reports/``, its report templates.

The sections of the file are named after the PCS, the benchmark and the
operating condition, joined by dots:

.. code-block:: ini

   [PCS_RTE-I16z3]                        ; the PCS
   [PCS-Benchmarks]                       ; its benchmarks
   [PCS-OperatingConditions]              ; the operating conditions of each benchmark
   [PCS_RTE-I16z3.PSetPointStep]          ; a benchmark
   [PCS_RTE-I16z3.PSetPointStep.Dec40]    ; an operating condition
   [PCS_RTE-I16z3.PSetPointStep.Dec40.Model]   ; its grid and operating point
   [PCS_RTE-I16z3.PSetPointStep.Dec40.Event]   ; its event
   [Model-Validations]                    ; the compliance tests, per benchmark
   [ReportCurves]                         ; the figures, per benchmark


Value definitions
-----------------

Every quantity of the operating point and of the event is written as a
*value definition*: a number in per unit, the name of a base magnitude, or
``factor*Name`` with an optional sign:

.. code-block:: ini

   pdr_P = Pmax
   pdr_P = -0.5*PmaxConsumption
   pdr_U = 1.05*Unom
   setpoint_step_value = 0.02*Udim
   line_XPu = 3*b

The base magnitudes, case-sensitive, are ``Pmax``, ``PmaxInjection``,
``PmaxConsumption``, ``Pmin``, ``Qmax``, ``Qmin`` and ``Snom`` (powers, in pu
of the 100 MVA base of the simulation), ``Udim`` and ``Unom`` (voltages, in
pu of the nominal voltage at the PDR), and ``line_XPu`` (the reactance
computed for the operating condition). ``Pmax`` and its two aliases resolve to
the same value; writing ``PmaxConsumption`` in ``pdr_P`` marks the operating
condition as a consumption one, which flips the sign of every ``Pmax`` of
that condition. A definition that names an unknown magnitude aborts the run,
naming the file and line it was read from.

Voltage levels
^^^^^^^^^^^^^^

Several keys exist in three variants, suffixed ``_HTB1``, ``_HTB2`` and
``_HTB3``. DyCoV picks the one of the voltage level of the installation,
from ``u_nom_at_PDR`` of ``Producer.ini``: HTB1 for 63 and 90 kV (66 kV
offshore), HTB2 for 150 and 225 kV (132 kV offshore), HTB3 for 400 kV. The
levels and their values are the ``HTB<n>_*`` keys of ``[GridCode]``.


The PCS section
---------------

.. code-block:: ini

   [PCS_RTE-I16z3]
   report_name = report.RTE-I16z3.tex
   id = 16
   zone = 3
   force_voltage_droop = false

``report_name``
  LaTeX template of the report of the whole PCS, under
  ``templates/reports/<workflow>/<technology>/<PCS>/``. Required.

``id``
  Integer that orders the PCS in the summary and the report.

``zone``
  ``1`` or ``3`` in the RMS model validation; absent in the electrical
  performance verification. It selects the producer files of the zone, the
  curves compared and the control-mode parameters applied.

``force_voltage_droop``
  Whether to switch the units to voltage-droop control regardless of the
  producer parameters. It only acts on a test whose
  ``setpoint_change_test_type`` matches no control mode (``Others``); for
  the P, Q and U setpoint tests the droop follows the mode of the test.

``setpoint_tracking_thresholds``
  Family of ``[GridCode]`` tolerances applied to the controlled magnitude of
  a setpoint test: absent for the I16 table, ``FT`` for the F16 one. See
  the *Compliance tests* chapter of the user manual.

.. code-block:: ini

   [PCS-Benchmarks]
   PCS_RTE-I16z3 = USetPointStep,PSetPointStep,QSetPointStep,ThreePhaseFault

   [PCS-OperatingConditions]
   PCS_RTE-I16z3.USetPointStep = AReactance,BReactance
   PCS_RTE-I16z3.PSetPointStep = Dec40,Inc40

``[PCS-Benchmarks]`` lists the benchmarks of the PCS, and
``[PCS-OperatingConditions]`` the operating conditions of each one. Both are
free names; they name the sections below, the records of the reference
curves (``<PCS>.<Benchmark>.<OperatingCondition>.csv``) and the figures. A
PCS whose list is empty runs nothing.


The benchmark section
---------------------

A benchmark is the grid DyCoV simulates on the TSO side of the PDR and the
kind of event it applies.

.. code-block:: ini

   [PCS_RTE-I16z3.PSetPointStep]
   job_name = PCS I16-Zone3 (Power Park Modules) - Active Setpoint Step
   TSO_model = RefTracking_1Line_InfBus
   Omega_model = SetPoint

``job_name``
  Name of the Dynawo job, written in ``TSOModel.jobs``.

``TSO_model``
  Grid model, a directory of ``src/dycov/model_lib/TSO_model/``:

  .. list-table::
     :header-rows: 1
     :widths: 32 48 20

     * - Model
       - Network
       - Kind of test
     * - ``RefTracking_1Line_InfBus``
       - Infinite bus, one line to the PDR, and a step on the setpoint
         ``connect_event_to`` names, in every unit.
       - Setpoint step
     * - ``Fault_1Line_InfBus``
       - Infinite bus, one line, and a fault at the PDR whose impedance
         DyCoV searches (Zone 1).
       - Bolted or high-impedance fault
     * - ``Fault_4Lines_InfBus``
       - Infinite bus and four parallel lines; a fault at 1 % of the fourth
         one, which is tripped at the end of the fault.
       - Three-phase fault (Zone 3, I4, I5)
     * - ``LineTrip_3Lines_InfBus``
       - Infinite bus and three parallel lines; the third one is tripped at
         the event.
       - Line trip (I3)
     * - ``GridVWDisturbance_InfBusFromTab``
       - An infinite bus directly at the PDR whose voltage follows the
         profile of ``TableInfiniteBus.txt``.
       - Voltage dip and swell
     * - ``GridVWDisturbance_1Line_InfBusFromTab``
       - The same voltage source behind one line.
       - Grid voltage step (Zone 1)
     * - ``GridVWDisturbance_1Line_VariableImpedance``
       - Infinite bus, one line, and a fault impedance at the PDR that
         follows ``TableVariableImpedance.txt``.
       - Voltage dip and swell (alternative)
     * - ``GridVWDisturbance_1Line_InfBus``
       - Infinite bus and one line, with no event of its own; the frequency
         comes from the Omega model.
       - Frequency ramp
     * - ``GridWDisturbance_2Loads_1Line``
       - One line to a bus with a large synchronous generator and two loads,
         one of them disconnected at the event.
       - Load shedding (I8)
     * - ``Islanding_2Loads``
       - A load at the PDR, alone, stepped at the event.
       - Islanding (I10, SM)
     * - ``Islanding_2Loads_SynchCond``
       - The same load plus one line to an inertial grid.
       - Islanding (I10 PPM and BESS, I16)

``Omega_model``
  Frequency reference of the units, a directory of
  ``src/dycov/model_lib/Omega/``: ``SetPoint`` (constant, 1 pu), ``Ramp``
  (the fixed ramp of the frequency test: from 20 s, 0.25 s long, +0.01 pu),
  ``InfiniteBus`` (the frequency of the voltage table, for the ``*FromTab``
  models) and ``DYNModelOmegaRef`` (the centre of inertia of the island).

A benchmark that uses a voltage table ships it in a directory named after
the benchmark, next to the description (``GridVoltageDip/TableInfiniteBus.txt``);
see :ref:`Table files <table-files>`.


The operating-condition section
-------------------------------

.. code-block:: ini

   [PCS_RTE-I16z3.PSetPointStep.Dec40]
   report_name = report.PSetPointStep.Dec40.tex
   reference_step_size = 0.4*Pmax
   bolted_fault = false
   hiz_fault = false
   setpoint_change_test_type = PSetpoint

``report_name``
  LaTeX template of the section of this operating condition in the report.
  Without it the test runs but is left out of the report.

``reference_step_size``
  Size of the step, used to frame the figures around it; it takes no part
  in the checks.

``bolted_fault``, ``hiz_fault``
  Kind of fault the operating condition applies, when it is a fault. DyCoV
  then searches the fault impedance before the final simulation: the lowest
  converging one for a bolted fault, the one that produces the voltage dip
  ``setpoint_step_value`` gives for a high-impedance fault. The errors of a
  fault are expressed in pu of the magnitude, not of a step. Only Zone 1
  searches an impedance; in Zone 3 the fault is the one of the grid model.

``setpoint_change_test_type``
  Control mode the units must be in for the test: ``PSetpoint``,
  ``QSetpoint``, ``USetpoint`` or ``Others``. For the three setpoint modes,
  the parameters of the units are checked against the modes listed in the
  control-mode dictionary of the tool; a unit in another mode makes the test
  *Not applicable*. ``Others`` applies to any model. It also selects the
  setpoint overlaid on the figures.

The ``.Model`` section
^^^^^^^^^^^^^^^^^^^^^^

The grid between the infinite bus and the PDR, and the operating point before
the event.

.. code-block:: ini

   [PCS_RTE-I16z3.PSetPointStep.Dec40.Model]
   line_XPu = b
   pdr_P = Pmax
   pdr_Q = 0
   pdr_U = Udim

**The grid impedance** is given by one of three keys; when several are
present the first of this list wins:

``line_XPu``
  Reactance of the line to the PDR: ``a`` or ``b``, the two reactances the
  DTR tabulates by voltage level (``HTB<n>_reactance_a``,
  ``HTB<n>_reactance_b_low`` and ``_high`` of ``[GridCode]``, the ``b``
  variant depending on the maximum power), a multiple of them (``3*b``), or
  a number in pu of the 100 MVA base. Used by the fiches that specify the
  line (I2, I3, I4, I5, I8, I16 Zone 3). In Zone 3 the resistance is
  ``X / XPu_r_factor``.

``SCR``
  Short-circuit ratio of an infinite grid, on the nominal power of the
  installation, with ``X / R = SCR_r_factor``. Used by I16 Zone 1.

``Zcc``
  The short-circuit impedance of the voltage level (``HTB<n>_Scc`` of
  ``[GridCode]``), with ``X / R = Ztanphi``. Used by the dips and swells
  (I6, I7, I16 Zone 3); only its presence counts (``Zcc = true``).

Whichever is chosen also becomes the ``line_XPu`` magnitude of the value
definitions of the operating condition.

**The operating point** at the connection bus, before the event:

``pdr_P``, ``pdr_Q``, ``pdr_U``
  Active power, reactive power and voltage, in generator convention
  (positive = injection), as value definitions. Required. In Zone 1 the
  connection bus is InternalNode1. In the islanding tests they also set the
  load of the island, which consumes exactly that point.

**The voltage profile** of a dip or a swell, read by the grid models that
follow a table (:ref:`Table files <table-files>`), all suffixed by voltage
level:

``u_fault_HTB<n>``, ``u_clear_HTB<n>``, ``u_rec2_HTB<n>``, ``u_rec3_HTB<n>``, ``u_swell_HTB<n>``, ``u_u0_HTB<n>``
  Voltages, in pu, of the stages of the profile: during the fault, at its
  clearing, at the second and third recovery stages, at the top of the
  swell. The ``TableInfiniteBus.txt`` of a benchmark uses the ones it names
  as placeholders; the others only serve the variable-impedance variant,
  where DyCoV turns each voltage into the fault reactance that produces it.

``delta_t_rec1``, ``delta_t_rec2``, ``delta_t_rec3`` (optionally ``_HTB<n>``)
  Instants of the recovery stages, in seconds **counted from the start of
  the event** (``sim_t_event_start``): DyCoV writes ``sim_t_event_start +
  value`` wherever the table names them.

Any other ``{{placeholder}}`` of a grid model is also looked up in this
section, which is how the loads of the islanding tests read ``pdr_P``,
``pdr_Q`` and ``pdr_U``, and how a custom grid model reads its own keys.

The ``.Event`` section
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: ini

   [PCS_RTE-I16z3.PSetPointStep.Dec40.Event]
   connect_event_to = ActivePowerSetpointPu
   sim_t_event_start = 20
   #fault_duration =
   setpoint_step_value = -0.4*Pmax

``connect_event_to``
  Magnitude the event drives: ``ActivePowerSetpointPu``,
  ``ReactivePowerSetpointPu``, ``VoltageSetpointPu`` or
  ``NetworkFrequencyPu``. In a setpoint step it names the setpoint stepped
  in every unit; in a grid voltage step, the voltage of the table; in a
  frequency ramp, the frequency. It is also the **controlled magnitude** of
  the compliance tests. Absent in faults, dips, swells, islanding, line trip
  and load shedding.

``sim_t_event_start``
  Instant of the event, in seconds. When reference curves exist their
  metadata overrides it, with a warning, so that both curves align. It is
  the base of the compliance windows and of the ``delta_t_*`` keys.

``fault_duration``, ``fault_duration_HTB<n>``
  Duration of the fault, dip or swell, in seconds; ``9999`` for a permanent
  fault. The plain key wins over the suffixed ones. For a frequency ramp,
  the duration of the ramp. It sets the end of the event, the *during*
  window and the ``*_clear`` tests.

``setpoint_step_value``
  A value definition whose meaning depends on the kind of test:

  .. list-table::
     :header-rows: 1
     :widths: 35 65

     * - Kind of test
       - Meaning
     * - P or Q setpoint step
       - Height of the step, in pu of the 100 MVA base, converted to each
         unit's base.
     * - U setpoint step
       - Height of the step, in pu of the nominal voltage (``0.02*Udim``).
     * - Grid voltage step
       - Jump of the infinite-bus voltage, in pu.
     * - High-impedance fault
       - Depth of the voltage dip to produce at the PDR; the sign is
         ignored.
     * - Frequency ramp
       - Height of the ramp, in pu, for the ramp tests.

  In every case it is also the base in which the tracking errors of the
  controlled magnitude are expressed.

``step_event_PPu``, ``step_event_QPu``
  Islanding only: the step applied to the active and reactive power of the
  load of the island at the event, in pu of the 100 MVA base, positive for
  an increase.

The validation sections
^^^^^^^^^^^^^^^^^^^^^^^

``[Model-Validations]`` and ``[Performance-Validations]`` name, test by test,
the benchmarks each compliance test applies to, and ``[ReportCurves]`` the
benchmarks each figure is drawn for; all three take comma-separated lists
of ``<PCS>.<Benchmark>``. The tests and the figures are listed in the
*Compliance tests* chapter of the user manual.

.. _table-files:

Table files
^^^^^^^^^^^

The grid models that follow a profile read it from a text file in a
directory named after the benchmark, next to the description:

.. code-block:: text

   PCS_RTE-I16z3/
   ├── PCSDescription.ini
   └── GridVoltageDip/
       ├── TableInfiniteBus.txt
       └── TableVariableImpedance.txt

``TableInfiniteBus.txt`` holds three tables of (time, value) rows,
``TableOmegaRefPu``, ``TableUPhase`` and ``TableUPu``, the last one being the
voltage profile. ``TableVariableImpedance.txt`` holds ``ImpedanceTable``
(time, 0, reactance), where 100 means no fault. Their values are
placeholders DyCoV fills from the configuration: ``simulation_start`` and
``simulation_stop`` from ``[Dynawo]``; ``start_event`` and ``end_event``
from the event; ``bus_u0pu`` (the initial voltage) and ``bus_upu`` (after a
grid voltage step) from the initialization; ``u_fault``, ``u_clear``,
``delta_t_rec1/2/3`` and the ``Xv_*`` reactances from the ``.Model`` keys.
Two rows at the same instant with different values are turned into a short
transition of ``transition_points`` rows over ``transition_half_width``
seconds (``[Dynawo]``).

The tables are read from the PCS directory shipped with the tool; a table
written in the configuration directory is used only for a PCS the tool does
not ship.


The kinds of test
-----------------

Each kind of test below names its canonical benchmark in the shipped
descriptions, which is the one to copy, the keys it needs and the compliance
tests that apply to it.

Setpoint step (P, Q or U)
^^^^^^^^^^^^^^^^^^^^^^^^^

A step on the active power, reactive power or voltage setpoint of every
unit, the grid being an infinite bus behind a line. Canonical:
``PCS_RTE-I16z3`` ``PSetPointStep.Dec40``, ``QSetPointStep.Inc10``,
``USetPointStep.AReactance``; ``PCS_RTE-I16z1`` ``SetPointStep.*`` for Zone
1; ``PCS_RTE-I2`` in the performance verification.

.. code-block:: ini

   [PCS_RTE-X.PSetPointStep]
   job_name = ... - Active Setpoint Step
   TSO_model = RefTracking_1Line_InfBus
   Omega_model = SetPoint

   [PCS_RTE-X.PSetPointStep.Dec40]
   report_name = report.PSetPointStep.Dec40.tex
   reference_step_size = 0.4*Pmax
   bolted_fault = false
   hiz_fault = false
   setpoint_change_test_type = PSetpoint      ; QSetpoint, USetpoint

   [PCS_RTE-X.PSetPointStep.Dec40.Model]
   line_XPu = b                               ; SCR = 3 in Zone 1
   pdr_P = Pmax
   pdr_Q = 0
   pdr_U = Udim

   [PCS_RTE-X.PSetPointStep.Dec40.Event]
   connect_event_to = ActivePowerSetpointPu   ; ReactivePowerSetpointPu, VoltageSetpointPu
   sim_t_event_start = 20
   setpoint_step_value = -0.4*Pmax            ; 0.1*Pmax, 0.02*Udim

Compliance tests: ``reaction_time``, ``rise_time``, ``settling_time``,
``overshoot``, ``setpoint_tracking_controlled_magnitude``,
``mean_absolute_error_power_1P``, ``mean_absolute_error_injection_1P``,
``mean_absolute_error_voltage`` (model validation); ``static_diff``,
``time_5U``, ``time_10U``, ``stabilized`` (performance, U step).

Three-phase fault
^^^^^^^^^^^^^^^^^

**Zone 3 and performance verification** (``PCS_RTE-I16z3``
``ThreePhaseFault.TransientBolted``, ``PCS_RTE-I4``, ``PCS_RTE-I5``): a
bolted fault on one of four parallel lines, tripped when the fault is
cleared. The duration depends on the voltage level.

.. code-block:: ini

   [PCS_RTE-X.ThreePhaseFault]
   TSO_model = Fault_4Lines_InfBus
   Omega_model = SetPoint

   [PCS_RTE-X.ThreePhaseFault.TransientBolted]
   report_name = report.ThreePhaseFault.TransientBolted.tex
   bolted_fault = true
   hiz_fault = false
   setpoint_change_test_type = Others

   [PCS_RTE-X.ThreePhaseFault.TransientBolted.Model]
   line_XPu = 3*b
   pdr_P = Pmax
   pdr_Q = 0
   pdr_U = Udim

   [PCS_RTE-X.ThreePhaseFault.TransientBolted.Event]
   sim_t_event_start = 30
   fault_duration_HTB1 = 0.150
   fault_duration_HTB2 = 0.085
   fault_duration_HTB3 = 0.085

**Zone 1** (``PCS_RTE-I16z1`` ``ThreePhaseFault.*``): a fault at the
internal node whose impedance DyCoV searches. ``TSO_model =
Fault_1Line_InfBus``, ``SCR`` instead of ``line_XPu``, ``bolted_fault =
true`` with a plain ``fault_duration`` (``9999`` for a permanent fault), or
``hiz_fault = true`` with ``setpoint_step_value = -0.5*Unom`` giving the
depth of the dip.

Compliance tests: ``voltage_dips_active_power``,
``voltage_dips_reactive_power``, ``voltage_dips_active_current``,
``voltage_dips_reactive_current``, ``active_power_recovery``, the three
``mean_absolute_error_*`` (model validation); ``time_5P``, ``time_10P``,
``time_85U``, ``time_clear``, ``time_10Pfloor_85U``, ``time_10Pfloor_clear``,
``imax_reac``, ``time_cct``, ``stabilized``, ``no_disconnection_gen``,
``no_disconnection_load`` (performance).

Grid voltage dip
^^^^^^^^^^^^^^^^

The voltage at the PDR follows a profile: the pre-fault value, ``u_fault``
during the fault, a linear recovery to 0.85 pu at ``delta_t_rec2``, held to
``delta_t_rec3``, then the pre-fault value. Canonical: ``PCS_RTE-I16z3``
``GridVoltageDip.Qzero``, ``PCS_RTE-I6``.

.. code-block:: ini

   [PCS_RTE-X.GridVoltageDip]
   TSO_model = GridVWDisturbance_InfBusFromTab
   Omega_model = InfiniteBus

   [PCS_RTE-X.GridVoltageDip.Qzero]
   report_name = report.GridVoltageDip.Qzero.tex
   bolted_fault = false
   hiz_fault = false
   setpoint_change_test_type = Others

   [PCS_RTE-X.GridVoltageDip.Qzero.Model]
   Zcc = true
   pdr_P = Pmax
   pdr_Q = 0
   pdr_U = Udim
   u_fault_HTB1 = 0.05
   u_fault_HTB2 = 1e-3
   u_fault_HTB3 = 1e-3
   u_clear_HTB1 = 0.05
   u_clear_HTB2 = 1e-3
   u_clear_HTB3 = 1e-3
   delta_t_rec2_HTB1 = 1.15
   delta_t_rec2_HTB2 = 1.15
   delta_t_rec2_HTB3 = 1.50
   delta_t_rec3_HTB1 = 5.0
   delta_t_rec3_HTB2 = 5.0
   delta_t_rec3_HTB3 = 5.0

   [PCS_RTE-X.GridVoltageDip.Qzero.Event]
   sim_t_event_start = 20
   fault_duration = 0.15

The benchmark ships ``GridVoltageDip/TableInfiniteBus.txt`` with that
profile; the synchronous-machine variant of I6 adds a ``u_clear`` stage up
to ``delta_t_rec1``.

Compliance tests: the four ``voltage_dips_*``, ``active_power_recovery``,
the three ``mean_absolute_error_*`` (model validation); ``time_85U``,
``time_10Pfloor_85U``, ``stabilized``, ``no_disconnection_*``
(performance).

Grid voltage swell
^^^^^^^^^^^^^^^^^^

The voltage at the PDR rises to 1.3 pu for ``fault_duration``, then 1.25 pu
to ``delta_t_rec2``, 1.15 pu to ``delta_t_rec3``, and returns. Canonical:
``PCS_RTE-I16z3`` ``GridVoltageSwell.QMax``, ``PCS_RTE-I7``. Same models and
keys as the dip, with ``u_swell_HTB<n>``, ``u_rec2_HTB<n>``,
``u_rec3_HTB<n>`` (1.3, 1.25, 1.15) for the variable-impedance variant,
``delta_t_rec1/2/3`` and ``pdr_Q = Qmax`` or ``Qmin``.

Compliance tests: as the dip.

Grid voltage step (Zone 1)
^^^^^^^^^^^^^^^^^^^^^^^^^^

A step of the infinite-bus voltage behind the line, with the unit's
setpoints untouched. Canonical: ``PCS_RTE-I16z1`` ``GridVoltageStep.Rise``
and ``Drop``.

.. code-block:: ini

   [PCS_RTE-I16z1.GridVoltageStep]
   TSO_model = GridVWDisturbance_1Line_InfBusFromTab
   Omega_model = SetPoint

   [PCS_RTE-I16z1.GridVoltageStep.Rise]
   report_name = report.GridVoltageStep.Rise.tex
   reference_step_size = 0.1
   bolted_fault = false
   hiz_fault = false
   setpoint_change_test_type = Others

   [PCS_RTE-I16z1.GridVoltageStep.Rise.Model]
   SCR = 10
   pdr_P = 0.5*Pmax
   pdr_Q = Qmin
   pdr_U = 0.95*Unom

   [PCS_RTE-I16z1.GridVoltageStep.Rise.Event]
   connect_event_to = VoltageSetpointPu
   sim_t_event_start = 30
   setpoint_step_value = 0.1

``connect_event_to = VoltageSetpointPu`` is required: it is what makes the
table step the voltage. The benchmark ships
``GridVoltageStep/TableInfiniteBus.txt``.

Compliance tests: the step-response characteristics,
``setpoint_tracking_controlled_magnitude`` and the three
``mean_absolute_error_*``.

Grid frequency ramp (Zone 3)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The frequency reference of the units follows the fixed ramp of the ``Ramp``
Omega model: +0.01 pu over 0.25 s from 20 s. Canonical: ``PCS_RTE-I16z3``
``GridFreqRamp.W500mHz250ms``.

.. code-block:: ini

   [PCS_RTE-I16z3.GridFreqRamp]
   TSO_model = GridVWDisturbance_1Line_InfBus
   Omega_model = Ramp

   [PCS_RTE-I16z3.GridFreqRamp.W500mHz250ms]
   report_name = report.GridFreqRamp.W500mHz250ms.tex
   reference_step_size = 0.01
   bolted_fault = false
   hiz_fault = false
   setpoint_change_test_type = Others

   [PCS_RTE-I16z3.GridFreqRamp.W500mHz250ms.Model]
   SCR = 3
   pdr_P = Pmax
   pdr_Q = 0
   pdr_U = Udim

   [PCS_RTE-I16z3.GridFreqRamp.W500mHz250ms.Event]
   connect_event_to = NetworkFrequencyPu
   sim_t_event_start = 20
   fault_duration = 0.250
   setpoint_step_value = 0.01

The event keys describe the ramp to the compliance tests; the simulated
ramp is the one of the Omega model, so they must match it.

Compliance tests: ``ramp_time_lag``, ``ramp_error``, ``settling_time``,
``overshoot``, the four ``voltage_dips_*`` and the three
``mean_absolute_error_*``.

Islanding
^^^^^^^^^

The installation is left alone feeding a load equal to its operating point,
which is stepped at the event. Canonical: ``PCS_RTE-I16z3``
``Islanding.DeltaP10DeltaQ4``, ``PCS_RTE-I10``.

.. code-block:: ini

   [PCS_RTE-X.Islanding]
   TSO_model = Islanding_2Loads_SynchCond      ; Islanding_2Loads for a synchronous machine
   Omega_model = DYNModelOmegaRef

   [PCS_RTE-X.Islanding.DeltaP10DeltaQ4]
   report_name = report.Islanding.DeltaP10DeltaQ4.tex
   bolted_fault = false
   hiz_fault = false
   setpoint_change_test_type = Others

   [PCS_RTE-X.Islanding.DeltaP10DeltaQ4.Model]
   line_XPu = b
   pdr_P = 0.8*Pmax
   pdr_Q = 0
   pdr_U = Udim

   [PCS_RTE-X.Islanding.DeltaP10DeltaQ4.Event]
   sim_t_event_start = 20
   step_event_PPu = 0.1*Pmax
   step_event_QPu = 0.04*Pmax

Compliance tests: the four ``voltage_dips_*`` and the three
``mean_absolute_error_*`` (model validation); ``freq_1``, ``stabilized``,
``no_disconnection_*`` (performance).

Line trip and load shedding (synchronous machines)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``PCS_RTE-I3`` trips one of three parallel lines at the event
(``LineTrip_3Lines_InfBus``, ``line_XPu = 2*b``); ``PCS_RTE-I8``
disconnects a load next to a large synchronous generator
(``GridWDisturbance_2Loads_1Line``, ``line_XPu = a``). Both need only
``sim_t_event_start`` in their event. Compliance tests: ``time_5P``,
``time_10P``, ``stabilized`` (I3); ``AVR_5``, ``freq_200``, ``freq_250``,
``stabilized`` (I8).


Writing a new PCS
-----------------

1. Create the directory of the PCS under the workflow and technology it
   belongs to, in the configuration directory for a PCS of your own
   (``~/.config/dycov/templates/PCS/model/PPM/PCS_MyTest/``) or in the
   source tree for one shipped with the tool, with a ``PCSDescription.ini``.
2. Write the PCS section (``report_name``, ``id``, ``zone``) and list the
   benchmarks and their operating conditions.
3. For each benchmark, copy the benchmark section of the canonical one of
   its kind, then one operating condition per point to test: its ``.Model``
   with the grid and the operating point, its ``.Event`` with the event.
   Copy the table files of the kind, if any, into a directory named after
   the benchmark.
4. Activate the compliance tests of each benchmark in
   ``[Model-Validations]`` or ``[Performance-Validations]``, and the figures
   in ``[ReportCurves]``, as listed for its kind.
5. Write the report templates under ``templates/reports/...``: one for the
   PCS and one per operating condition, named as the ``report_name`` keys
   say, starting from the templates of the canonical benchmark.
6. For a model validation, put a record per operating condition in the
   reference curves, named ``<PCS>.<Benchmark>.<OperatingCondition>``, with
   its ``.dict``.
7. Run it alone, ``dycov validate ... -p PCS_MyTest``, and read the summary:
   *Not applicable* points at ``setpoint_change_test_type``, *Missing some
   reference curves* at the records, an empty report section at
   ``report_name``.

The *Advanced PCS customization* tutorial walks through steps 1 to 5 on an
existing PCS, and the *Adding a new PCS* chapter of the developer manual
covers a PCS that needs a compliance test the tool does not have.
