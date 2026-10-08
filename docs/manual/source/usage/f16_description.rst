.. _f16-description:

========================
The F16 declaration file
========================

PCS F16 compares the open phasor model of an installation with the records
of its commissioning tests, and the fiche fixes no test of its own: the
producer declares the tests recorded, with their records, in an
``F16Description.ini`` delivered at the root of the reference curves
directory. This chapter is the reference of that file: the kinds of test
DyCoV knows, how each one is declared, and the compliance tests and figures
that go with it. The tutorial *Declaring the on-site tests of PCS F16*
walks through a declaration step by step, and :ref:`Compliance tests
<compliance-tests>` describes what every test computes.

DyCoV reads every ``*Description.ini`` found next to the reference curves
and takes as the description of ``PCS_RTE-F16z3`` the file that names it in
its ``[PCS-Benchmarks]``. The file completes the description shipped with
the tool, which already carries the header of the PCS (its zone, its report
and the tolerances of the fiche): the producer writes only the tests. A copy
of the shipped description, with the declaration commented out and every
key explained, is left in the configuration directory under
``templates/PCS/model/<technology>/PCS_RTE-F16z3/PCSDescription.ini``.

.. code-block:: ini

   [PCS-Benchmarks]                              ; the kinds of test recorded
   [PCS-OperatingConditions]                     ; the active power levels of each one
   [PCS_RTE-F16z3.PSetPointStep]                 ; a benchmark: grid model and kind of event
   [PCS_RTE-F16z3.PSetPointStep.Pmax]            ; an operating condition
   [PCS_RTE-F16z3.PSetPointStep.Pmax.Model]      ; its grid and operating point
   [PCS_RTE-F16z3.PSetPointStep.Pmax.Event]      ; its event
   [Model-Validations]                           ; the compliance tests, per benchmark
   [ReportCurves]                                ; the figures, per benchmark


Value definitions
-----------------

Every quantity of the operating point and of the event is a *value
definition*: a number in per unit, the name of a base magnitude, or
``factor*Name`` with an optional sign:

.. code-block:: ini

   pdr_P = Pmax
   pdr_P = -0.5*PmaxConsumption
   pdr_U = 1.02*Unom
   setpoint_step_value = 0.02*Udim

The base magnitudes, case-sensitive, come from ``Producer.ini``: ``Pmax``,
``PmaxInjection``, ``PmaxConsumption`` and ``Pmin`` (the active power
limits, ``p_max_injection_at_PDR``, ``p_max_consumption_at_PDR``,
``p_min_injection_at_PDR`` and ``p_min_consumption_at_PDR``), ``Qmax`` and
``Qmin``, ``Snom`` (``s_nom``), and ``Udim`` and ``Unom`` (the dimensioning
and nominal voltages at the PDR). Powers are in pu of the 100 MVA base of
the simulation, voltages in pu of the nominal voltage. Writing
``PmaxConsumption`` in ``pdr_P`` marks a storage operating condition as a
consumption one. A definition that names an unknown magnitude aborts the
run, naming the file and line it was read from.


Benchmarks and operating conditions
-----------------------------------

.. code-block:: ini

   [PCS-Benchmarks]
   PCS_RTE-F16z3 = PSetPointStep,USetPointStep,ThreePhaseFault

   [PCS-OperatingConditions]
   PCS_RTE-F16z3.PSetPointStep = Pmin,P50,Pmax
   PCS_RTE-F16z3.USetPointStep = Pmin,P50,Pmax
   PCS_RTE-F16z3.ThreePhaseFault = Pmax

A **benchmark** is a kind of recorded test: the grid DyCoV simulates on the
TSO side of the PDR and the kind of event applied. An **operating
condition** is one record of that test, at one of the active power levels
the fiche fixes: minimum, 50 % of the maximum and maximum injection for a
PPM; maximum and 50 % consumption, 50 % and maximum injection for a BESS.
Both are free names, with one exception noted under the voltage dip and
swell; they name the sections below, the records
(``PCS_RTE-F16z3.<Benchmark>.<OperatingCondition>.csv``) and the figures.


The sections of a declared test
-------------------------------

Whatever its kind, a declared test is written in the same four sections.
The keys each kind uses are given with it below; this is what the keys
mean.

The benchmark section
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: ini

   [PCS_RTE-F16z3.PSetPointStep]
   job_name = PCS F16-Zone3 (Power Park Modules) - Active Setpoint Step
   TSO_model = RefTracking_1Line_InfBus
   Omega_model = SetPoint

``job_name``
  Name of the simulation job, free text.

``TSO_model``, ``Omega_model``
  The grid model simulated on the TSO side and the frequency reference of
  the units. Together they define the kind of test; take them from the kind
  recorded, in :ref:`The kinds of test <f16-kinds-of-test>`.

The operating-condition section
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: ini

   [PCS_RTE-F16z3.PSetPointStep.Pmax]
   report_name = report.F16z3.DeclaredTest.tex
   reference_step_size = 0.4*Pmax
   bolted_fault = false
   hiz_fault = false
   setpoint_change_test_type = PSetpoint

``report_name``
  Always ``report.F16z3.DeclaredTest.tex``, the report template DyCoV
  ships for a declared test.

``reference_step_size``
  Size of the step, used to frame the figures around it. It takes no part
  in the checks. Only for a step or a ramp.

``bolted_fault``, ``hiz_fault``
  ``true`` only for a recorded three-phase fault: DyCoV then searches the
  fault impedance that reproduces it (see that kind). ``false`` otherwise.

``setpoint_change_test_type``
  Control mode the units must be in for the test: ``PSetpoint``,
  ``QSetpoint`` or ``USetpoint`` for a setpoint step, ``Others`` for every
  other kind. For the three setpoint modes the parameters of the units are
  checked against the modes DyCoV knows; a unit in another mode makes the
  test *Not applicable*. It also selects the setpoint overlaid on the
  figures.

The ``.Model`` section
^^^^^^^^^^^^^^^^^^^^^^

The grid and the operating point **during the test**:

.. code-block:: ini

   [PCS_RTE-F16z3.PSetPointStep.Pmax.Model]
   line_XPu = b
   pdr_P = Pmax
   pdr_Q = 0
   pdr_U = Udim

The grid is given by one of three keys, the first present of this list
being the one used:

``line_XPu``
  Reactance of the line between the grid and the PDR, in pu of the 100 MVA
  base, or ``a`` / ``b``, the two reactances the DTR tabulates by voltage
  level, possibly multiplied (``3*b``). Write the value measured or
  estimated for the day of the test.

``SCR``
  Short-circuit ratio of the grid seen from the PDR, on the nominal power
  of the installation.

``Zcc``
  The short-circuit impedance the DTR fixes for the voltage level of the
  installation; its presence is enough (``Zcc = true``). It is what the
  voltage dip and swell use.

``pdr_P``, ``pdr_Q``, ``pdr_U``
  The operating point before the event, in generator convention (positive =
  injection). ``pdr_P`` is the level the fiche fixes (``Pmin``,
  ``0.5*Pmax``, ``Pmax``; for storage ``PmaxConsumption``,
  ``0.5*PmaxConsumption``, ``0.5*PmaxInjection``, ``PmaxInjection``);
  ``pdr_Q`` and ``pdr_U`` are the ones recorded before the event.

A voltage dip or swell adds to this section the profile of the voltage the
grid imposed (``u_fault``, ``delta_t_rec2``, ``delta_t_rec3``), described
with those kinds.

The ``.Event`` section
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: ini

   [PCS_RTE-F16z3.PSetPointStep.Pmax.Event]
   connect_event_to = ActivePowerSetpointPu
   sim_t_event_start = 20
   setpoint_step_value = -0.4*Pmax

``sim_t_event_start``
  Instant of the event in the simulation, in seconds. Every kind needs it.
  The record's ``.dict`` declares the same instant, which takes precedence
  for the *before*, *during* and *after* windows of every test, so both
  must agree for the curves to be aligned.

``connect_event_to``
  The magnitude the event drives, which is also the **controlled
  magnitude** the tracking tests look at: ``ActivePowerSetpointPu``,
  ``ReactivePowerSetpointPu`` or ``VoltageSetpointPu`` for a setpoint step,
  ``NetworkFrequencyPu`` for a frequency ramp. Absent for a fault, a dip, a
  swell or an islanding.

``setpoint_step_value``
  Size and sign of a step: in pu of the 100 MVA base for P and Q
  (``-0.4*Pmax``), in pu of the nominal voltage for U (``0.02*Udim``), in
  pu of the nominal frequency for a ramp. The ME, MAE and MXE of the
  controlled magnitude are expressed in pu of this value.

``fault_duration``
  Duration of a fault, a dip, a swell or a ramp, in seconds. Absent for a
  setpoint step and an islanding.

``step_event_PPu``, ``step_event_QPu``
  Only for an islanding: the step applied to the load of the island.


.. _f16-kinds-of-test:

The kinds of test
-----------------

DyCoV knows six kinds of test at the connection point of a Zone 3 model.
A commissioning can apply the setpoint steps on purpose; a fault, a dip, a
swell, a frequency excursion or an islanding is a grid event the
installation went through while recording, declared the same way. Each
kind below gives the sections of one operating condition in full, the
compliance tests that apply to it and the figures that show it.

.. list-table::
   :header-rows: 1
   :widths: 24 34 20 22

   * - Kind of test
     - ``TSO_model``
     - ``Omega_model``
     - Benchmark name
   * - Setpoint step (P, Q or U)
     - ``RefTracking_1Line_InfBus``
     - ``SetPoint``
     - free
   * - Three-phase fault
     - ``Fault_4Lines_InfBus``
     - ``SetPoint``
     - free
   * - Grid voltage dip
     - ``GridVWDisturbance_InfBusFromTab``
     - ``InfiniteBus``
     - ``GridVoltageDip``
   * - Grid voltage swell
     - ``GridVWDisturbance_InfBusFromTab``
     - ``InfiniteBus``
     - ``GridVoltageSwell``
   * - Grid frequency ramp
     - ``GridVWDisturbance_1Line_InfBus``
     - ``Ramp``
     - free
   * - Islanding
     - ``Islanding_2Loads_SynchCond``
     - ``DYNModelOmegaRef``
     - free

Setpoint step (P, Q or U)
^^^^^^^^^^^^^^^^^^^^^^^^^

A step on the active power, reactive power or voltage setpoint of the
installation, the grid being an infinite bus behind a line. It is the test
a commissioning applies, and the one the fiche describes its indicators
for: the controlled magnitude is compared with the record before, during
and after the step.

.. code-block:: ini

   [PCS_RTE-F16z3.PSetPointStep]
   job_name = PCS F16-Zone3 (Power Park Modules) - Active Setpoint Step
   TSO_model = RefTracking_1Line_InfBus
   Omega_model = SetPoint

   [PCS_RTE-F16z3.PSetPointStep.Pmax]
   report_name = report.F16z3.DeclaredTest.tex
   reference_step_size = 0.4*Pmax
   bolted_fault = false
   hiz_fault = false
   setpoint_change_test_type = PSetpoint          ; QSetpoint, USetpoint

   [PCS_RTE-F16z3.PSetPointStep.Pmax.Model]
   line_XPu = b
   pdr_P = Pmax
   pdr_Q = 0
   pdr_U = Udim

   [PCS_RTE-F16z3.PSetPointStep.Pmax.Event]
   connect_event_to = ActivePowerSetpointPu       ; ReactivePowerSetpointPu, VoltageSetpointPu
   sim_t_event_start = 20
   setpoint_step_value = -0.4*Pmax                ; 0.1*Pmax, 0.02*Udim

A reactive power step is declared with ``QSetpoint``,
``ReactivePowerSetpointPu`` and a step in pu of the 100 MVA base; a voltage
step with ``USetpoint``, ``VoltageSetpointPu`` and a step in pu of the
nominal voltage.

Compliance tests: ``reaction_time``, ``rise_time``, ``settling_time``,
``overshoot``, ``setpoint_tracking_controlled_magnitude``,
``mean_absolute_error_power_1P``, ``mean_absolute_error_injection_1P``,
``mean_absolute_error_voltage``. Optionally ``setpoint_tracking_active_power``
and ``setpoint_tracking_reactive_power``, which apply the same errors to P
or Q when they are not the controlled magnitude, and ``response_time``,
which is computed without a verdict.

Figures: ``fig_P``, ``fig_Q``, ``fig_Ip``, ``fig_Iq``, ``fig_Ustator``,
``fig_V``.

Three-phase fault
^^^^^^^^^^^^^^^^^

A three-phase fault on the grid near the PDR, cleared by tripping the
faulted line: the grid is an infinite bus and four parallel lines, the
fault sits on the fourth one, which opens at the end of the fault. DyCoV
searches the fault impedance: with ``bolted_fault = true`` the one that
leaves the residual voltage at the PDR under the threshold of a bolted
fault for the installation's size.

.. code-block:: ini

   [PCS_RTE-F16z3.ThreePhaseFault]
   job_name = PCS F16-Zone3 (Power Park Modules) - Three Phase Fault
   TSO_model = Fault_4Lines_InfBus
   Omega_model = SetPoint

   [PCS_RTE-F16z3.ThreePhaseFault.Pmax]
   report_name = report.F16z3.DeclaredTest.tex
   bolted_fault = true
   hiz_fault = false
   setpoint_change_test_type = Others

   [PCS_RTE-F16z3.ThreePhaseFault.Pmax.Model]
   line_XPu = 3*b
   pdr_P = Pmax
   pdr_Q = 0
   pdr_U = Udim

   [PCS_RTE-F16z3.ThreePhaseFault.Pmax.Event]
   sim_t_event_start = 30
   fault_duration = 0.150

``fault_duration`` is the clearing time recorded, in seconds; the record's
``.dict`` declares the same duration, which the tests use to place their
windows.

Compliance tests: ``voltage_dips_active_power``,
``voltage_dips_reactive_power``, ``voltage_dips_active_current``,
``voltage_dips_reactive_current``, ``active_power_recovery``,
``mean_absolute_error_power_1P``, ``mean_absolute_error_injection_1P``,
``mean_absolute_error_voltage``.

Figures: the six of a setpoint step plus ``fig_I``, ``fig_UIt`` and
``fig_Tap``.

Grid voltage dip
^^^^^^^^^^^^^^^^

The voltage at the PDR follows a profile imposed by the grid: the pre-fault
value, ``u_fault`` for ``fault_duration``, a linear recovery to 0.85 pu
reached ``delta_t_rec2`` seconds after the start of the event, held until
``delta_t_rec3``, then the pre-fault value. The profile is a table DyCoV
ships with the PCS under the name of the benchmark, so **the benchmark must
be named** ``GridVoltageDip``.

.. code-block:: ini

   [PCS_RTE-F16z3.GridVoltageDip]
   job_name = PCS F16-Zone3 (Power Park Modules) - Grid Voltage Dip
   TSO_model = GridVWDisturbance_InfBusFromTab
   Omega_model = InfiniteBus

   [PCS_RTE-F16z3.GridVoltageDip.Pmax]
   report_name = report.F16z3.DeclaredTest.tex
   bolted_fault = false
   hiz_fault = false
   setpoint_change_test_type = Others

   [PCS_RTE-F16z3.GridVoltageDip.Pmax.Model]
   Zcc = true
   pdr_P = Pmax
   pdr_Q = 0
   pdr_U = Udim
   u_fault = 0.05
   delta_t_rec2 = 1.15
   delta_t_rec3 = 5.0

   [PCS_RTE-F16z3.GridVoltageDip.Pmax.Event]
   sim_t_event_start = 20
   fault_duration = 0.15

``u_fault`` is the residual voltage recorded during the dip, in pu of the
nominal voltage; ``delta_t_rec2`` and ``delta_t_rec3`` are offsets from
``sim_t_event_start``, in seconds.

Compliance tests: as the three-phase fault.

Figures: the six of a setpoint step plus ``fig_I`` and ``fig_UIt``.

Grid voltage swell
^^^^^^^^^^^^^^^^^^

The voltage at the PDR rises to 1.3 pu for ``fault_duration``, then holds
1.25 pu until ``delta_t_rec2`` and 1.15 pu until ``delta_t_rec3`` before
returning to the pre-event value; the three levels are those of the DTR
swell profile and are fixed by the table, only the instants are declared.
Same models as the dip, and the same constraint: **the benchmark must be
named** ``GridVoltageSwell``.

.. code-block:: ini

   [PCS_RTE-F16z3.GridVoltageSwell]
   job_name = PCS F16-Zone3 (Power Park Modules) - Grid Voltage Swell
   TSO_model = GridVWDisturbance_InfBusFromTab
   Omega_model = InfiniteBus

   [PCS_RTE-F16z3.GridVoltageSwell.Pmax]
   report_name = report.F16z3.DeclaredTest.tex
   bolted_fault = false
   hiz_fault = false
   setpoint_change_test_type = Others

   [PCS_RTE-F16z3.GridVoltageSwell.Pmax.Model]
   Zcc = true
   pdr_P = Pmax
   pdr_Q = Qmax
   pdr_U = Udim
   delta_t_rec2 = 2.5
   delta_t_rec3 = 30.0

   [PCS_RTE-F16z3.GridVoltageSwell.Pmax.Event]
   sim_t_event_start = 20
   fault_duration = 0.05

Compliance tests: the four ``voltage_dips_*`` and the three
``mean_absolute_error_*``.

Figures: as the dip.

Grid frequency ramp
^^^^^^^^^^^^^^^^^^^

The frequency reference of the units follows a ramp, the grid being an
infinite bus behind a line. The ramp DyCoV simulates is fixed by its
``Ramp`` frequency model: +0.01 pu (0.5 Hz) over 0.25 s, starting at 20 s.
A record can only be declared as this kind of test if it shows that
excursion, and the event keys below describe that same ramp to the
compliance tests.

.. code-block:: ini

   [PCS_RTE-F16z3.GridFreqRamp]
   job_name = PCS F16-Zone3 (Power Park Modules) - Grid Frequency Ramp
   TSO_model = GridVWDisturbance_1Line_InfBus
   Omega_model = Ramp

   [PCS_RTE-F16z3.GridFreqRamp.Pmax]
   report_name = report.F16z3.DeclaredTest.tex
   reference_step_size = 0.01
   bolted_fault = false
   hiz_fault = false
   setpoint_change_test_type = Others

   [PCS_RTE-F16z3.GridFreqRamp.Pmax.Model]
   SCR = 3
   pdr_P = Pmax
   pdr_Q = 0
   pdr_U = Udim

   [PCS_RTE-F16z3.GridFreqRamp.Pmax.Event]
   connect_event_to = NetworkFrequencyPu
   sim_t_event_start = 20
   fault_duration = 0.250
   setpoint_step_value = 0.01

Compliance tests: ``ramp_time_lag``, ``ramp_error``, ``settling_time``,
``overshoot``, the four ``voltage_dips_*``,
``mean_absolute_error_power_1P`` and ``mean_absolute_error_injection_1P``.

Figures: the six of a setpoint step plus ``fig_WRef``.

Islanding
^^^^^^^^^

The installation is left feeding a load equal to its operating point, with
a line to a small inertial grid, and the load is stepped at the event by
``step_event_PPu`` and ``step_event_QPu``.

.. code-block:: ini

   [PCS_RTE-F16z3.Islanding]
   job_name = PCS F16-Zone3 (Power Park Modules) - Islanding
   TSO_model = Islanding_2Loads_SynchCond
   Omega_model = DYNModelOmegaRef

   [PCS_RTE-F16z3.Islanding.Pmax]
   report_name = report.F16z3.DeclaredTest.tex
   bolted_fault = false
   hiz_fault = false
   setpoint_change_test_type = Others

   [PCS_RTE-F16z3.Islanding.Pmax.Model]
   line_XPu = b
   pdr_P = Pmax
   pdr_Q = 0
   pdr_U = Udim

   [PCS_RTE-F16z3.Islanding.Pmax.Event]
   sim_t_event_start = 20
   step_event_PPu = 0.1*Pmax
   step_event_QPu = 0.04*Pmax

Compliance tests: the four ``voltage_dips_*`` and the three
``mean_absolute_error_*``.

Figures: the six of a setpoint step plus ``fig_WRef``, ``fig_SyncCondP``,
``fig_SyncCondQ``, ``fig_SyncCondFreq``, ``fig_LoadP`` and ``fig_LoadQ``.


The compliance tests
--------------------

``[Model-Validations]`` names, test by test, the benchmarks it applies to,
as comma-separated lists of ``PCS_RTE-F16z3.<Benchmark>``. A benchmark not
listed under a key is not checked for it. For the declaration above, with
two setpoint steps and a fault:

.. code-block:: ini

   [Model-Validations]
   reaction_time = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
   rise_time = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
   settling_time = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
   overshoot = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
   setpoint_tracking_controlled_magnitude = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
   voltage_dips_active_power = PCS_RTE-F16z3.ThreePhaseFault
   voltage_dips_reactive_power = PCS_RTE-F16z3.ThreePhaseFault
   voltage_dips_active_current = PCS_RTE-F16z3.ThreePhaseFault
   voltage_dips_reactive_current = PCS_RTE-F16z3.ThreePhaseFault
   active_power_recovery = PCS_RTE-F16z3.ThreePhaseFault
   mean_absolute_error_power_1P = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep,PCS_RTE-F16z3.ThreePhaseFault
   mean_absolute_error_injection_1P = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep,PCS_RTE-F16z3.ThreePhaseFault
   mean_absolute_error_voltage = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep,PCS_RTE-F16z3.ThreePhaseFault

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Tests
     - Kinds of test they apply to
   * - ``reaction_time``, ``rise_time``, ``settling_time``, ``overshoot``
     - Setpoint step; ``settling_time`` and ``overshoot`` also the frequency
       ramp.
   * - ``setpoint_tracking_controlled_magnitude``
     - Setpoint step. ``setpoint_tracking_active_power`` and
       ``setpoint_tracking_reactive_power`` are its optional companions.
   * - ``voltage_dips_active_power``, ``voltage_dips_reactive_power``,
       ``voltage_dips_active_current``, ``voltage_dips_reactive_current``
     - Three-phase fault, voltage dip, voltage swell, frequency ramp,
       islanding.
   * - ``active_power_recovery``
     - Three-phase fault, voltage dip.
   * - ``ramp_time_lag``, ``ramp_error``
     - Frequency ramp.
   * - ``mean_absolute_error_power_1P``, ``mean_absolute_error_injection_1P``,
       ``mean_absolute_error_voltage``
     - Every kind (the voltage one is not meaningful for the frequency
       ramp).

What each test computes and its tolerances are in :ref:`Compliance tests
<compliance-tests>`. The tolerances of the controlled magnitude are the
``thr_FT_reftrack_*`` family the shipped description of the PCS selects;
the ``voltage_dips_*`` tests use their field-measurement table when the
record's ``.dict`` says ``is_field_measurements = True``.


The figures
-----------

``[ReportCurves]`` names, for each figure, the benchmarks it is drawn for.
The six figures of the connection point apply to every kind; the others
show what a kind adds.

.. code-block:: ini

   [ReportCurves]
   fig_P = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep,PCS_RTE-F16z3.ThreePhaseFault
   fig_Q = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep,PCS_RTE-F16z3.ThreePhaseFault
   fig_Ip = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep,PCS_RTE-F16z3.ThreePhaseFault
   fig_Iq = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep,PCS_RTE-F16z3.ThreePhaseFault
   fig_Ustator = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep,PCS_RTE-F16z3.ThreePhaseFault
   fig_V = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep,PCS_RTE-F16z3.ThreePhaseFault
   fig_I = PCS_RTE-F16z3.ThreePhaseFault
   fig_UIt = PCS_RTE-F16z3.ThreePhaseFault
   fig_Tap = PCS_RTE-F16z3.ThreePhaseFault

.. list-table::
   :header-rows: 1
   :widths: 22 50 28

   * - Figure
     - Draws
     - Kinds of test
   * - ``fig_V``
     - Voltage at the PDR.
     - Every kind
   * - ``fig_P``, ``fig_Q``
     - Active and reactive power at the PDR, with the setpoint overlaid in
       a setpoint step.
     - Every kind
   * - ``fig_Ip``, ``fig_Iq``
     - Active and reactive current at the PDR.
     - Every kind
   * - ``fig_Ustator``
     - Magnitude controlled by the plant voltage regulation and its
       setpoint.
     - Every kind
   * - ``fig_I``
     - Current magnitude at the generator terminals.
     - Fault, dip, swell
   * - ``fig_UIt``
     - Voltage at the terminals of the units, with the voltage setpoint
       overlaid when the converter controls that node.
     - Fault, dip, swell
   * - ``fig_Tap``
     - Tap position of the main transformer.
     - Fault
   * - ``fig_WRef``
     - Network frequency.
     - Frequency ramp, islanding
   * - ``fig_SyncCondP``, ``fig_SyncCondQ``, ``fig_SyncCondFreq``
     - Active power, reactive power and frequency of the inertial grid of
       the island.
     - Islanding
   * - ``fig_LoadP``, ``fig_LoadQ``
     - Active and reactive power of the stepped load.
     - Islanding

Every figure also draws the record, the exclusion intervals around the
event and the markers of the checked characteristics.


The records
-----------

One record per operating condition, in the ``Producer`` directory of the
reference curves, named after it, with its ``.dict`` and its line in
``CurvesFiles.ini``:

.. code-block:: text

   ReferenceCurves/
   ├── F16Description.ini
   └── Producer/
       ├── CurvesFiles.ini
       ├── PCS_RTE-F16z3.PSetPointStep.Pmax.csv
       ├── PCS_RTE-F16z3.PSetPointStep.Pmax.dict
       └── ...

The ``.dict`` declares ``is_field_measurements = True``, the instant of the
event and its duration (the ``fault_duration`` of a fault, a dip, a swell or
a ramp; 0 for a step or an islanding), and maps the six curves Zone 3
compares (voltage, active and reactive power, active and reactive current
at the PDR, and the network frequency) to the columns of the record; see
:ref:`Reference Curves <referenceCurves>`.
