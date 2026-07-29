=============
Configuration
=============

DyCoV uses a layered configuration system where settings can be defined at
different levels, each overriding the one below it. Understanding this
hierarchy is key to knowing where to make changes and how they propagate
through the tool.

The configuration is written in the standard INI format
(`Python flavor <https://docs.python.org/3/library/configparser.html>`_)
and organized into three levels, in decreasing order of priority:

1. **User Configuration** — settings provided by the user in
   ``~/.config/dycov/config.ini``. These always take precedence.
2. :ref:`PCS Configuration <pcsconf>` — settings defined per PCS in
   ``src/dycov/templates/PCS/``. These should only be modified when a DTR
   update changes the PCS definition.
3. :ref:`Tool Configuration <toolconf>` — global defaults in
   ``src/dycov/configuration/defaultConfig.ini``. These should only be
   modified when a DTR update changes global conditions.


.. _pcsconf:

PCS Configuration
------------------

Each PCS has its own ``PCSDescription.ini`` file, located under
``src/dycov/templates/PCS/<workflow>/<technology>/<PCSName>/``. This file
defines the complete structure of the PCS — its benchmarks, operating
conditions, validation tests, and report curves.

These files should only be edited by developers, and only when a DTR update
requires it.


PCS structure parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^

Under ``[PCS-Benchmarks]``:

* ``PCSName``
    Comma-separated list of Benchmarks that belong to the PCS.

Under ``[PCS-OperatingConditions]``:

* ``PCSName.BenchmarkName``
    Comma-separated list of Operating Conditions for the given Benchmark.


Validation tests
^^^^^^^^^^^^^^^^^

Under ``[Performance-Validations]``, define which Performance Validation tests
each Benchmark or Operating Condition must pass. Available tests:

* ``static_diff`` — static difference between the controlled quantity and the
  voltage adjustment setpoint.
* ``time_5U`` — time at which voltage stays within ±5% of its final value.
* ``time_10U`` — time at which voltage stays within ±10% of its final value.
* ``time_5P`` — time at which P stays within ±5% of its final value.
* ``time_10P`` — time at which P stays within ±10% of its final value.
* ``time_85U`` — time at which voltage at the PDR returns above 0.85 pu.
* ``time_clear`` — time at which the faulted line is disconnected at both ends.
* ``time_cct`` — fault-clearing time threshold for rotor-angle stability onset.
* ``stabilized`` — checks whether a steady state has been reached.
* ``no_disconnection_gen`` — checks that no generator disconnection occurred.
* ``no_disconnection_load`` — checks that no load disconnection occurred.
* ``AVR_5`` — checks that the magnitude controlled by the plant-level voltage
  regulation never deviates more than 5% from its setpoint.
* ``time_10P_85U`` — time when 10P is achieved, measured from when voltage
  returns above 0.85 pu.
* ``freq_1`` — checks that frequency stays between 49 Hz and 51 Hz.
* ``freq_200`` — checks that frequency stays within ±200 mHz.
* ``freq_250`` — checks that frequency stays within ±250 mHz.
* ``time_10Pfloor_85U`` — time when 10P_floor is achieved after voltage
  returns above 0.85 pu.
* ``time_10Pfloor_clear`` — time when 10P_tclear is achieved after voltage
  returns above 0.85 pu.
* ``imax_reac`` — checks that when Imax is reached, reactive support is
  prioritized over active power.

Under ``[Model-Validations]``, define which Model Validation tests each
Benchmark or Operating Condition must pass. Available tests:

* ``reaction_time`` — time from setpoint step until measured value reaches
  10% of step height.
* ``rise_time`` — time between 10% and 90% of the step variation.
* ``response_time`` — time from step command until measured value first enters
  the tolerance range of the target value.
* ``settling_time`` — time from step command until measured value enters the
  tolerance range for the last time.
* ``overshoot`` — difference between maximum response and final steady-state
  value.
* ``ramp_time_lag`` — tracking error time.
* ``ramp_error`` — tracking error value.
* ``mean_absolute_error_power_1P`` — P and Q MAE must not exceed 1% of Pmax.
* ``mean_absolute_error_injection_1P`` — active and reactive injection MAE
  must not exceed 1% of Pmax.
* ``mean_absolute_error_voltage`` — voltage MAE.
* ``voltage_dips_active_power`` — P ME, MAE and MXE within thresholds.
* ``voltage_dips_reactive_power`` — Q ME, MAE and MXE within thresholds.
* ``voltage_dips_active_current`` — active injection ME, MAE and MXE within
  thresholds.
* ``voltage_dips_reactive_current`` — reactive injection ME, MAE and MXE
  within thresholds.
* ``setpoint_tracking_controlled_magnitude`` — ME, MAE and MXE of the
  controlled magnitude within thresholds.
* ``setpoint_tracking_active_power`` — ME, MAE and MXE of active power within
  thresholds.
* ``setpoint_tracking_reactive_power`` — ME, MAE and MXE of reactive power
  within thresholds.


Report curves
^^^^^^^^^^^^^^

Under ``[ReportCurves]``, define which figures appear in the PCS report by
listing the Benchmarks or Operating Conditions that should include each graph:

* ``fig_P`` — active power at the PDR bus.
* ``fig_Q`` — reactive power at the PDR bus.
* ``fig_Ip`` — active current at the PDR bus.
* ``fig_Iq`` — reactive current at the PDR bus.
* ``fig_Ustator`` — stator voltage magnitude (pu).
* ``fig_V`` — voltage magnitude at the PDR bus.
* ``fig_W`` — rotor speed.
* ``fig_Theta`` — generator internal angle (pu).
* ``fig_WRef`` — network frequency (Hz).
* ``fig_I`` — injected active and reactive currents.
* ``fig_Tap`` — main transformer tap ratio.


PCS-level parameters
^^^^^^^^^^^^^^^^^^^^^^

Under ``[PCSName]``:

* ``report_name`` — name of the LaTeX file used for the PCS summary report.
* ``id`` — PCS identifier, used to sort the final report.
* ``zone`` — Zone 1 or Zone 3 (for RMS Model Validation only).

Under ``[PCSName.BenchmarkName]``:

* ``job_name`` — name used to populate the Dynawo JOBS file.
* ``TSO_model`` — Dynawo model name for the TSO network of the PCS.
* ``Omega_model`` — Dynawo model name for the Omega model of the PCS.

Under ``[PCSName.BenchmarkName.OCName]``:

* ``report_name`` — LaTeX file name for the Operating Condition report.
* ``reference_step_size`` — step magnitude for reference tracking tests,
  used to scale the compliance tolerance. Optional.
* ``bolted_fault`` — whether the fault test uses a bolted fault.
* ``hiz_fault`` — whether the fault test uses a Hi-Z fault.
* ``setpoint_change_test_type`` — type of setpoint affected in step tests.

Under ``[PCSName.BenchmarkName.OCName.Model]``:

* ``line_XPu`` — reactance of the line at the PDR, when the Benchmark has a
  single Operating Condition. Optional.
* ``SCR`` — Short-Circuit Ratio. Optional.
* ``pdr_P``, ``pdr_Q``, ``pdr_U`` — initial P, Q, and voltage at the PDR.

The infinite bus table configuration also lives in this section. The tool
replaces placeholders found in the ``TableInfiniteBus.txt`` file with the
values defined here. If a value depends on the generator type, append the
type identifier to the variable name (e.g. ``u_ret_HTB1``).

The same placeholder substitution applies to the TSO model files
(``TSOModel.jobs``, ``TSOModel.dyd``, ``TSOModel.par``). Commonly used
examples:

* ``main_P0Pu``, ``main_Q0Pu``, ``main_U0Pu`` — initial conditions for the
  main load.
* ``secondary_P0Pu``, ``secondary_Q0Pu``, ``secondary_U0Pu`` — initial
  conditions for the secondary load.

Under ``[PCSName.BenchmarkName.OCName.Event]``:

* ``connect_event_to`` — Dynawo model variable where the step is connected.
* ``sim_t_event_start`` — event start time (s).
* ``fault_duration`` — fault duration until line disconnection (s). When this
  depends on generator type, declare ``fault_duration_HTB1``,
  ``fault_duration_HTB2``, ``fault_duration_HTB3`` separately.
* ``setpoint_step_value`` — increment applied after the step trigger.


.. _toolconf:

Tool Configuration
-------------------

The global configuration of DyCoV lives in
``src/dycov/configuration/defaultConfig.ini``. This file should only be
modified by developers, and only when a DTR update changes the global
conditions of an implemented PCS.


Global section
^^^^^^^^^^^^^^

Logging:

* ``file_log_max_bytes`` — maximum log file size in bytes (default: 52428800 = 50 MB).
* ``file_log_level`` — log level for the log file (10=DEBUG, 20=INFO, 30=WARNING,
  40=ERROR, 50=CRITICAL).
* ``file_formatter`` — format string for log file records.
* ``console_log_level`` — log level for console output.
* ``console_formatter`` — format string for console log records.

Path configuration (these paths are relative to the package installation and
should not normally be changed):

* ``input_templates_path`` — path to input skeleton templates within the package.
* ``latex_templates_path`` — path to PDF templates within the package.
* ``templates_path`` — path to PCS templates within the package.
* ``lib_path`` — path to RTE models within the package.
* ``modelica_path`` — path to Modelica models within the package.
* ``temporal_path`` — path for temporary calculation files.

PCS execution scope (empty means "run all"):

* ``electric_performance_verification_pcs`` — SM PCSs to run.
* ``electric_performance_ppm_verification_pcs`` — PPM PCSs to run.
* ``electric_performance_bess_verification_pcs`` — BESS PCSs to run.
* ``model_ppm_validation_pcs`` — PPM model validation PCSs to run.
* ``model_bess_validation_pcs`` — BESS model validation PCSs to run.

Parallel execution:

* ``parallel_pcs_validation`` — enable parallel execution of PCS validation
  across multiple CPU cores (default: True).
* ``parallel_num_processes`` — maximum number of parallel processes (default: 4).

HiZ fault bisection:

* ``hiz_fault_max_impedance`` — maximum impedance value for the HiZ fault bisection
  method.
* ``hiz_fault_min_impedance`` — minimum impedance value.
* ``hiz_fault_rel_tol`` — relative tolerance for bisection convergence.

Bolted fault search:

* ``bolted_fault_max_impedance`` — maximum impedance value for the bolted fault search.
* ``bolted_fault_min_impedance`` — minimum impedance value (the most severe fault, tried
  first; larger values are searched by bisection only on non-convergence).
* ``bolted_fault_rel_tol`` — relative tolerance for search convergence.
* ``bolted_fault_max_voltage_small`` / ``bolted_fault_max_voltage_large`` — maximum
  residual voltage at the PDR bus (pu) for a fault to qualify as bolted, for the
  small and large reference generators. The applicable threshold is interpolated
  linearly on the producer's SNom and clamped outside the reference range.
* ``bolted_fault_snom_small`` / ``bolted_fault_snom_large`` — SNom (MVA) of the
  small and large reference generators anchoring the interpolation.

Initialization:

* ``skip_voltage_droop_adjustment`` — when True, skips voltage droop parameter
  adjustment during initialization, leaving the PAR file unmodified.


Dynawo section
^^^^^^^^^^^^^^

* ``simulation_limit`` — maximum time (s) for the dynamic simulation. DyCoV
  stops the simulator when this limit is exceeded.
* ``simulation_start`` — simulation start time (s). Before changing this,
  verify that all PCS events fall within the configured simulation window.
* ``simulation_stop`` — simulation end time (s). PCS I7 has an event at t=30s;
  use at least 60 seconds to ensure a stable final result.
* ``simulation_precision`` — simulator step precision.
* ``f_nom`` — grid nominal frequency (fNom) in pu. Must match Dynawo's
  ``Electrical/SystemBase.mo``. If Dynawo is customized, update this too.
* ``s_nref`` — system-wide S base (SnRef) in pu. Same note as above.

Solver selection:

* ``solver_lib`` — solver library to use: ``dynawo_SolverIDA`` (default) or
  ``dynawo_SolverSIM``.

IDA solver parameters (used when ``solver_lib = dynawo_SolverIDA``):

* ``ida_order`` — integration order.
* ``ida_initStep`` — initial step size.
* ``ida_minStep`` — minimum step size.
* ``ida_maxStep`` — maximum step size.
* ``ida_absAccuracy`` — absolute accuracy.
* ``ida_relAccuracy`` — relative accuracy.
* ``ida_minimalAcceptableStep`` — minimum acceptable step.

SIM solver parameters (used when ``solver_lib = dynawo_SolverSIM``):

* ``sim_hMin``, ``sim_hMax`` — minimum and maximum step sizes.
* ``sim_kReduceStep`` — step reduction factor on convergence failure.
* ``sim_maxNewtonTry`` — maximum Newton iterations per step.
* ``sim_linearSolverName`` — linear solver (default: KLU).
* ``sim_fnormtol`` — function norm tolerance.
* ``sim_minimalAcceptableStep`` — minimum acceptable step.

Transition smoothing (for table-based step changes):

* ``transition_enabled`` — enable smoothing of step transitions.
* ``transition_points`` — number of interpolation points around the event.
* ``transition_half_width`` — half-width of the smoothing window (s).


GridCode section
^^^^^^^^^^^^^^^^

Signal processing parameters:

* ``t_com`` — common sampling interval (s). Must satisfy
  ``t_com < 1 / (2 * cutoff)``.
* ``cutoff`` — low-pass filter cut-off frequency (Hz).
* ``t_integrator_tol`` — numerical tolerance for event timing (accounts for
  the fact that Dynawo's integrator may place events slightly off the
  configured time).
* ``t_windowLPF_excl_start``, ``t_windowLPF_excl_end`` — exclusion windows
  at the boundaries of each filtered window, to mitigate LP filtering
  boundary artifacts.
* ``t_faultLPF_excl`` — exclusion window at fault insertion (LP filter
  artifact mitigation).
* ``t_faultQS_excl`` — exclusion window at fault insertion for quasi-static
  transients. Current RTE PCS I16 specifies 20 ms; must not exceed 140 ms
  (IEC 61400-27-2).
* ``t_clearQS_excl`` — exclusion window at fault clearing. Current PCS I16
  specifies 60 ms; must not exceed 500 ms (IEC 61400-27-2).
* ``disable_window_filtering`` — disable windowed signal filtering (filter
  applied to the whole signal instead).
* ``stable_time`` — minimum time required to consider a simulation stable.
* ``thr_ss_tol`` — numerical tolerance (% of value) for steady-state
  detection.

Step-response time characteristic thresholds:

* ``thr_reaction_time`` — maximum allowed MAE on reaction time.
* ``thr_rise_time`` — maximum allowed MAE on rise time.
* ``thr_settling_time`` — maximum allowed MAE on settling time.
* ``thr_overshoot`` — maximum allowed MAE on overshoot.
* ``thr_ramp_time_lag`` — maximum allowed ME on ramp time lag.
* ``thr_ramp_error`` — maximum allowed MXE on ramp error.
* ``thr_final_ss_mae`` — maximum allowed MAE between simulation and reference
  in steady state after the event.

Impedance calculation factors:

* ``XPu_r_factor`` — factor to calculate RPu from XPu (Zone 3 model validation).
* ``SCR_r_factor`` — factor to calculate Rcc from Xcc.
* ``fault_r_factor`` — factor to calculate Rv from Xv.
* ``Ztanphi`` — factor to derive Xcc and Rcc from Zcc.

Signal error thresholds (simulation reference):
    For each signal ``<s>`` in {``P``, ``Q``, ``Ip``, ``Iq``} and each metric
    ``<m>`` in {``mxe``, ``me``, ``mae``}, there is a parameter
    ``thr_<s>_<m>_<w>`` for each window ``<w>`` in {``before``, ``during``,
    ``after``}. For example: ``thr_P_mxe_during``, ``thr_Iq_mae_after``.

Signal error thresholds (field test reference):
    Same structure as above, with the ``FT_`` prefix:
    ``thr_FT_<s>_<m>_<w>``. For example: ``thr_FT_P_mxe_during``.

Setpoint tracking thresholds:
    ``thr_reftrack_<m>_<w>`` for each metric and window.
    For example: ``thr_reftrack_mxe_before``.

Grid connection parameters by generator type (HTB1, HTB2, HTB3):

* ``HTB1_Udims``, ``HTB2_Udims``, ``HTB3_Udims`` — allowed nominal voltages.
* ``HTB1_External_Udims``, ``HTB2_External_Udims``, ``HTB3_External_Udims``
  — allowed external nominal voltages.
* ``HTBx_reactance_a``, ``HTBx_reactance_b_low``, ``HTBx_reactance_b_high``
  — reactance table parameters:

  .. list-table::
     :header-rows: 1

     * - Generator type
       - a
       - b
     * - HTB1
       - 0.05
       - Pmax < 50 MW: 0.2 / Pmax >= 50 MW: 0.3
     * - HTB2
       - 0.05
       - Pmax < 250 MW: 0.3 / Pmax >= 250 MW: 0.54
     * - HTB3
       - 0.05
       - Pmax < 800 MW: 0.54 / Pmax >= 800 MW: 0.6

* ``HTB1_p_max``, ``HTB2_p_max``, ``HTB3_p_max`` — active power limit for
  reactance calculation.
* ``HTB1_Scc``, ``HTB2_Scc``, ``HTB3_Scc`` — reference short-circuit power
  (MVA) by generator type (400, 1500, 7000 MVA respectively).
* ``Udim_63kV``, ``Udim_66kV``, ``Udim_90kV``, ``Udim_132kV``,
  ``Udim_150kV``, ``Udim_225kV``, ``Udim_400kV`` — nominal voltage for each
  voltage level.


GFM section
^^^^^^^^^^^^

* ``SCRmin`` — minimum Short-Circuit Ratio for GFM envelope generation.
* ``SCRmax`` — maximum Short-Circuit Ratio for GFM envelope generation.


CurvesVariables section
^^^^^^^^^^^^^^^^^^^^^^^^

Defines which Dynawo output curves are needed for each workflow:

* ``SM`` — curves for Performance Validation of synchronous machines.
* ``PPM`` — curves for Performance Validation of power park modules.
* ``ModelValidationZ3`` — curves for Zone 3 Model Validation.
* ``ModelValidationZ1`` — curves for Zone 1 Model Validation.


Debug section
^^^^^^^^^^^^^

These parameters are useful during development and debugging:

* ``show_figs_t0`` — extend the time range to include t0 in plots.
* ``show_figs_tend`` — extend the time range to include tend in plots.
* ``plot_all_curves_in_html`` — include all available curves in the HTML
  output, not just those specified by the PCS.
* ``disable_LP_filtering`` — disable low-pass filtering of signals entirely.
* ``max_simulation_retries`` — maximum number of retries for a failed
  simulation (default: 4, covering: base line, reduced step, increased
  precision, small networks, solver switch).