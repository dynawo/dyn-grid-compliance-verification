.. _compliance-tests:

================
Compliance tests
================

Every PCS applies a selection of compliance tests to the curves of each of
its benchmarks. This chapter lists every test DyCoV implements, what it
computes, what it needs and how it is activated and configured, so that a
PCS description can be read or written key by key. The tests of the RMS
model validation compare the simulated curves with the reference curves; the
tests of the electrical performance verification examine the simulated
curves on their own.


How a test is activated
-----------------------

A test is activated in the description of a PCS — the ``F16Description.ini``
a producer delivers (see :ref:`The F16 declaration file <f16-description>`),
or the ``PCSDescription.ini`` of the PCS, described in the developer manual —
in the section of its family: ``[Model-Validations]`` for the RMS model
validation and ``[Performance-Validations]`` for the electrical performance
verification.
Each key names the benchmarks the test applies to, as a comma-separated list
of ``<PCS>.<Benchmark>``:

.. code-block:: ini

   [Model-Validations]
   reaction_time = PCS_RTE-I16z3.USetPointStep,PCS_RTE-I16z3.PSetPointStep
   voltage_dips_active_power = PCS_RTE-I16z3.ThreePhaseFault

A benchmark that no key names is not checked for that test. The keys are read
from every configuration layer, so a user ``PCSDescription.ini`` (or, for a
PCS whose tests the producer declares, the description delivered with the
reference curves) can add a benchmark to a test or remove one.

The verdict of an operating condition is the conjunction of its activated
tests. A test that cannot be computed, because a curve or a reference is
missing, is reported as *N/A* and the operating condition as not compliant.
When no reference curves are available at all, the operating condition is
reported as *Missing some reference curves* instead.

Three keys of the operating condition decide what the tests look at:

* ``connect_event_to`` (``.Event`` section) names the magnitude the event
  drives, the **controlled magnitude** the step-response and
  setpoint-tracking tests examine: ``ActivePowerSetpointPu`` (P),
  ``ReactivePowerSetpointPu`` (Q), ``VoltageSetpointPu`` (V) or
  ``NetworkFrequencyPu`` (frequency, Zone 3 only).
* ``sim_t_event_start`` and ``fault_duration`` (``.Event`` section) locate the
  event and define the three **windows** of the error metrics: *before*,
  from one second before the event to the event; *during*, from the event to
  its end, which only exists when ``fault_duration`` is not zero; and
  *after*, from the end of the event to the end of the curves. Every window
  leaves out the exclusion intervals around the event, configured by the
  ``t_*_excl`` keys of ``[GridCode]``.
* ``setpoint_step_value`` (``.Event`` section) is the size of the step, and
  the base of every error of a setpoint test: ME, MAE and MXE are expressed in
  pu of it. For a fault (``bolted_fault`` or ``hiz_fault``) the errors are
  expressed in pu of the magnitude.

The error metrics, computed per window on the difference between the
simulated and the reference curve, are the ones of IEC 61400-27-2: **ME**,
the mean error; **MAE**, the mean absolute error; **MXE**, the maximum
absolute error. A metric passes when its magnitude stays below its
threshold: the thresholds are maximum permissible errors, so a mean-error
bias fails whatever its sign, and the report keeps the signed ME.

The step-response characteristics follow IEC 61400-21-1 (see
:ref:`Step-response Characteristics <step-response-characteristics>`). Each
one is computed on the simulated and on the reference curve of the
controlled magnitude, and the test passes when the simulated value stays
within the configured relative difference of the reference one.


RMS model validation tests (``[Model-Validations]``)
----------------------------------------------------

Every test of this family needs the reference curves of the test, in the
format described in :ref:`Reference Curves <referenceCurves>`. In Zone 3 the
compared curves are the voltage, the active and reactive power and the
active and reactive current at the PDR, and the network frequency; in Zone 1
they are the voltage at InternalNode1 and InternalNode2, the active and
reactive power at the point the converter controls, and the currents Ip and
Iq at InternalNode2.

Step-response characteristics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``reaction_time``
  Interval between the step and the instant the controlled magnitude first
  reaches 10 % of the change, on the simulated and on the reference curve.
  Passes when the simulated time is within ``thr_reaction_time`` (default
  ``0.10``, i.e. 10 %) of the reference one. Needs a step on the controlled
  magnitude: a setpoint step or a grid voltage step.

``rise_time``
  Interval between the reaction time (the 10 % crossing) and the instant the
  controlled magnitude first reaches 90 % of the change, as the DTR defines
  it, so a pure delay counts once, as reaction time. Passes within
  ``thr_rise_time`` (``0.10``). Same needs as ``reaction_time``.

``settling_time``
  Interval between the step and the last instant the controlled magnitude is
  outside the tolerance band around its final value; the band is
  ``thr_ss_tol`` (``0.005``) times the step, applied to the final value.
  Passes within ``thr_settling_time`` (``0.10``). Same needs as
  ``reaction_time``; also applied to the frequency ramp of PCS I16.

``overshoot``
  How far the controlled magnitude goes beyond its final value after the
  event, in the direction of the step (the undershoot of a downward step),
  never negative, on the simulated and on the reference curve. Passes within
  ``thr_overshoot`` (``0.15``). Same needs as ``settling_time``.

``response_time``
  First instant the controlled magnitude enters the tolerance band of its
  final value, computed on both curves for information. It has no threshold
  and gives no verdict.

Tracking of the controlled magnitude
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``setpoint_tracking_controlled_magnitude``
  ME, MAE and MXE of the controlled magnitude in each window, in pu of the
  step. The thresholds are a family of ``[GridCode]`` keys named by the
  ``setpoint_tracking_thresholds`` key of the PCS: ``thr_reftrack_<metric>_<window>``
  when the PCS names none (PCS I16: 0.05/0.02/0.03 before and after the
  event, 0.08/0.05/0.07 during it, for MXE/ME/MAE) and
  ``thr_FT_reftrack_<metric>_<window>`` for ``FT`` (PCS F16: 0.05/0.03/0.04
  and 0.10/0.05/0.07). Needs a setpoint step. Activating it also narrows the
  exclusion intervals of the windows to ``t_windowLPF_excl_start``, since a
  step has no transient to leave out.

``setpoint_tracking_active_power``, ``setpoint_tracking_reactive_power``
  The same metrics and thresholds applied to the active or the reactive power
  of the zone, besides the controlled magnitude. The errors are still in pu of
  the step of the test. Needs a setpoint step.

Final steady state
^^^^^^^^^^^^^^^^^^

``mean_absolute_error_power_1P``
  In the steady state after the event, from the instant the simulated curve
  settles, the MAE between the simulated and the reference active power, and
  likewise the reactive power, below ``thr_final_ss_mae`` (``0.01``, in pu of
  the magnitude). The simulated curve must also be stable over that interval,
  within ``thr_ss_tol``. Applies to any event.

``mean_absolute_error_injection_1P``
  The same test on the active and the reactive current.

``mean_absolute_error_voltage``
  The same test on the voltage.

Faults, dips and swells
^^^^^^^^^^^^^^^^^^^^^^^

``voltage_dips_active_power``, ``voltage_dips_reactive_power``, ``voltage_dips_active_current``, ``voltage_dips_reactive_current``
  ME, MAE and MXE of P, Q, Ip or Iq in each window. The thresholds are the
  ``thr_<signal>_<metric>_<window>`` keys of ``[GridCode]`` when the
  reference curves are simulations (0.05/0.02/0.03 before and after,
  0.08/0.05/0.07 during, for MXE/ME/MAE) and the ``thr_FT_<signal>_<metric>_<window>``
  keys when they declare ``is_field_measurements = True`` (0.08/0.04/0.07 and
  0.10/0.05/0.08). Meant for faults, dips and swells, with their
  ``fault_duration``; PCS I16 also applies them to the frequency ramp and the
  islanding of Zone 3.

``active_power_recovery``
  Time to recover 90 % of the active power measured one third into the fault,
  on the simulated and on the reference curve. Passes when the difference is
  below the lesser of 10 % of the reference time and 100 ms. Needs a fault or
  a dip.

Frequency ramp
^^^^^^^^^^^^^^

``ramp_time_lag``
  Time lag of the simulated response to a frequency ramp, as the largest
  deviation of its sampling instants from the ideal ramp over the ramp
  duration. Passes below ``thr_ramp_time_lag`` (``0.10``). Needs
  ``connect_event_to = NetworkFrequencyPu`` and a ``fault_duration`` equal to
  the ramp duration.

``ramp_error``
  Largest deviation of the simulated frequency from the ideal ramp over the
  ramp duration. Passes below ``thr_ramp_error`` (``0.10``). Same needs as
  ``ramp_time_lag``.


Electrical performance tests (``[Performance-Validations]``)
------------------------------------------------------------

These tests examine the simulated curves at the PDR, with no reference. Their
thresholds are the ones the DTR fixes and are not configurable, except for
the steady-state tolerance ``thr_ss_tol`` and the nominal frequency
``f_nom`` of the ``[Dynawo]`` section. Times are measured from the event
(``sim_t_event_start``), or from the end of the fault for the ``*_clear``
tests.

Voltage control
^^^^^^^^^^^^^^^

``static_diff``
  Static difference between the magnitude controlled by the primary voltage
  regulation and its setpoint, at the end of the simulation, as a fraction of
  the setpoint, over every generating unit. Passes below 0.2 %. Needs a
  voltage setpoint step.

``time_5U``, ``time_10U``
  Instant from which the voltage at the PDR stays within a band of 5 % (10 %)
  of its change around its final value, measured from the event. Passes
  below 10 s (5 s). Needs a voltage setpoint step.

``AVR_5``
  Whether the magnitude controlled by the plant-level voltage regulation ever
  deviates more than 5 % from its setpoint after the event, per generating
  unit; a unit that leaves the band makes the test fail. It is the criterion
  of the load shedding of synchronous machines (Fiche I8).

Active power recovery
^^^^^^^^^^^^^^^^^^^^^

``time_5P``, ``time_10P``
  Instant from which the active power at the PDR stays within a band of 5 %
  (10 %) of its final value, measured from the event. Passes below 10 s
  (5 s). Meant for a line trip or a fault.

``time_85U``
  Expands into ``time_5P_85U`` and ``time_10P_85U``: the same instants
  measured from the moment the voltage at the PDR returns above 0.85 pu.
  Pass below 10 s and 5 s. Needs a fault or a dip. ``time_10P_85U`` can also
  be activated on its own.

``time_clear``
  Expands into ``time_5P_clear`` and ``time_10P_clear``: the same instants
  measured from the clearing of the fault. Pass below 10 s and 5 s.

``time_10Pfloor_85U``, ``time_10Pfloor_clear``
  Instant from which the active power stays above 90 % of its final value,
  measured from the return of the voltage above 0.85 pu or from the clearing
  of the fault. Pass below 2 s. Meant for the faults and dips of power parks
  and storage.

Stability and protections
^^^^^^^^^^^^^^^^^^^^^^^^^

``stabilized``
  Whether the voltage, the active and the reactive power at the PDR reach a
  steady state, within ``thr_ss_tol`` over the last tenth of the simulation;
  for synchronous machines, also whether every internal angle settles and
  stays within ±π. Applies to every benchmark.

``no_disconnection_gen``, ``no_disconnection_load``
  Whether the simulation timeline records the disconnection of the
  generating units or of the auxiliary load, respectively, through the
  connection transformers or the internal line. Needs a Dynawo model.

``time_cct``
  Critical fault-clearing time for the onset of rotor-angle instability,
  found by bisection on the fault duration. Reported as a value, without a
  verdict. Needs a Dynawo model of a synchronous machine and a three-phase
  fault.

Frequency and current
^^^^^^^^^^^^^^^^^^^^^

``freq_1``
  Whether the frequency stays within ±1 Hz of ``f_nom`` at every instant,
  measured at the synchronous condenser when the test models one, at the
  generating units otherwise. Meant for the islanding of PCS I10.

``freq_200``, ``freq_250``
  Draw a ±200 mHz or ±250 mHz band on the frequency figure; they compute
  nothing.

``imax_reac``
  Whether, while the current of a generating unit sits at its maximum, the
  active current never rises above its running minimum, i.e. whether the
  reactive current keeps its priority. Needs the maximum current of the
  units, read from the model. Meant for the faults of PCS I5.


Report figures (``[ReportCurves]``)
-----------------------------------

The ``[ReportCurves]`` section names, for each figure, the benchmarks it is
drawn for, with the same ``<PCS>.<Benchmark>`` lists. Every figure draws the
reference curve when there is one, the exclusion intervals around the event,
the marker of the maximum error of a checked magnitude and the markers of the
step-response characteristics when they were computed.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Key
     - Draws
   * - ``fig_V``
     - Voltage at the PDR, with the ±5 % or ±10 % band of ``time_5U`` or
       ``time_10U`` and the instant of ``time_85U`` when activated.
   * - ``fig_P``, ``fig_Q``
     - Active or reactive power compared by the zone, with the band of the
       ``time_*P*`` tests when activated and the setpoint overlaid in a
       setpoint step.
   * - ``fig_Ip``, ``fig_Iq``
     - Active or reactive current compared by the zone.
   * - ``fig_I``
     - Active and reactive current at the generator terminals, with the band
       of ``imax_reac`` when activated.
   * - ``fig_Ustator``
     - Magnitude controlled by the voltage regulation and its setpoint, with
       the ±5 % band of ``AVR_5`` when activated.
   * - ``fig_UIt``
     - Voltage at the injector terminal (Zone 1), with the voltage setpoint
       overlaid when the converter controls that node.
   * - ``fig_InternalNode1P``, ``fig_InternalNode1Q``
     - Active and reactive power at InternalNode1 (Zone 1), drawn but not
       compared.
   * - ``fig_W``
     - Rotor speed of the generating units, in Hz.
   * - ``fig_WRef``
     - Network frequency, in Hz, with the band of ``freq_1``, ``freq_250`` or
       ``freq_200`` when activated.
   * - ``fig_Theta``
     - Internal angle of the generating units.
   * - ``fig_Tap``
     - Tap position of the main transformer.
   * - ``fig_SyncCondP``, ``fig_SyncCondQ``, ``fig_SyncCondFreq``
     - Active power, reactive power and frequency of the synchronous
       condenser of an islanding test.
   * - ``fig_LoadP``, ``fig_LoadQ``
     - Active and reactive power of the loads of an islanding test.
