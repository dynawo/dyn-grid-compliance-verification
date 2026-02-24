=============
Configuration
=============

Dynamic grid Compliance Verification has multiple configuration files, written in the
well-known INI format (of the `Python flavor`__). This guide introduces the
configuration parameters defined in each file. These configuration files are
grouped into 3 types, in order to set the overriding priority of settings. The
priority defined in the tool configuration is:

1. User Configuration
2. :ref:`PCS Configuration <pcsconf>`
3. :ref:`Dynamic grid Compliance Verification Configuration <toolconf>`


.. _pcsconf:

PCS Configuration
-------------------

This section explains the particular configuration of a *PCS*. Each
implemented *PCS* must have its own configuration PCSDescription.ini file, which is located in
the ``src/dycov/templates/PCS/`` directory of the tool.
These configuration files should only be edited by developers, and only if there is
any update of the DTR compliance document concerning the *PCS*.


PCS information
^^^^^^^^^^^^^^^^^

This is under the section ``PCS-Benchmarks`` (required).

* ``'PCSName'``

    List of *Benchmarks* of the *PCS* that will be used in the validation processes.

Under the section called ``PCS-OperatingConditions`` (required).

* ``'PCSName'.'BenchmarksName'``

    List of *Operating Conditions* of a *Benchmarks* of the *PCS* that will be used in the validation processes.

Under the section called ``Performance-Validations`` the tests that must be passed to validate a
*PCS* are defined. Each configuration parameter in this section corresponds to a Performance
Validation test implemented in Dynamic grid Compliance Verification. To configure the tests that will be used to
validate the *PCS*, the list of its *Benchmarks* or *Operating Conditions* that must pass a
test must be added to the corresponding parameter.

* ``time_5P``

    Time at which the power supplied P stays within the +/-5% tube centered on the final value of P.

* ``time_10P``

    Time at which the power supplied P stays within the +/-10% tube centered on the final value of P.

* ``time_85U``

    Time at which the the voltage at the PDR bus returns back above 0.85pu, regardless of any possible overshooting/undershooting that may take place later on.

* ``time_clear``

    Calculate the time at which the line is disconnected al both ends.

* ``time_cct``

    Calculate the fault-clearing time-threshold for the onset of rotor-angle stability.

* ``stabilized``

    Run various checks to determine if a steady state has been reached.

* ``no_disconnection_gen``

    Check that in the timeline there has been no generator disconnection caused by the simulation.

* ``no_disconnection_load``

    Check that in the timeline there has been no load disconnection caused by the simulation.

* ``AVR_5``

    Check that the magnitude controlled by the AVR (generator_UStatorPu_value) never deviates more than 5% from its setpoint.

* ``time_10P_85U``

    As soon as the voltage returns above 0.85 times pu, time when 10P is achieved.

* ``freq_1``

    Check that the fequency: a) Stays always above 49 Hz. b) Stays always below 51 Hz.

* ``freq_200``

    Check that the fequency stays in +-200 mHz.

* ``freq_250``

    Check that the fequency stays in +-250 mHz.

* ``time_10Pfloor_85U``

    As soon as the voltage returns above 0.85 times pu, time when 10P_floor is achieved.

* ``time_10Pfloor_clear``

    As soon as the voltage returns above 0.85 times pu, time when 10P_tclear is achieved.

* ``imax_reac``

    If Imax is reached, reactive support is prioritized over active power supply.

Under the section called ``Model-Validations`` the tests that must be passed to validate a
*PCS* are defined. Each configuration parameter in this section corresponds to a Model
Validation test implemented in Dynamic grid Compliance Verification. To configure the tests that will be used to
validate the *PCS*, the list of its *Benchmarks* or *Operating Conditions* that must pass a
test must be added to the corresponding parameter.

* ``reaction_time``

    Time elapsed from change of setpoint step until measured value reaches 10% of step height.

* ``rise_time``

    Time elapsed between when the measured value reaches 10% of the scale variation and when the measured value reaches 90% of the scale variation.

* ``response_time``

    Time from the issue of a step change command or start of the event until the measured value first enters the predefined tolerance range of the target value.

* ``settling_time``

    Time elapsed from the issue of a step change command or the start of the event until the observed value enters the predefined tolerance range of the target value for the last time.

* ``overshoot``

    Difference between the maximum measured value of the response and the final value at steady state.

* ``ramp_time_lag``

    Tracking error time.

* ``ramp_error``

    Tracking error value.

* ``mean_absolute_error_power_1P``

    Active and Reactive power difference in MAE should not exceed 1% of Pmax.

* ``mean_absolute_error_injection_1P``

    Active and Reactive injection difference in MAE should not exceed 1% of Pmax.

* ``mean_absolute_error_voltage``

    Voltage difference in MAE.

* ``voltage_dips_active_power``

    Active power difference in ME, MAE and MXE should not exceed certain thresholds.

* ``voltage_dips_reactive_power``

    Reactive power difference in ME, MAE and MXE should not exceed certain thresholds.

* ``voltage_dips_active_current``

    Active injection difference in ME, MAE and MXE should not exceed certain thresholds.

* ``voltage_dips_reactive_current``

    Reactive injection difference in ME, MAE and MXE should not exceed certain thresholds.

* ``setpoint_tracking_controlled_magnitude``

    Difference in ME, MAE and MXE of the controlled magnitude should not exceed certain thresholds.

* ``setpoint_tracking_active_power``

    Difference in ME, MAE and MXE of the Active power should not exceed certain thresholds.

* ``setpoint_tracking_reactive_power``

    Difference in ME, MAE and MXE of the Reactive power should not exceed certain thresholds.

Under the section called ``ReportCurves`` are the graphs included in the *PCS* report. To configure
the graphs that will be included in the *PCS* report, the list of its *Benchmarks* or
*Operating Conditions* must be added to the corresponding parameter.

* ``fig_P``

    Real power output P, measured at the PDR bus.

* ``fig_Q``

    Reactive power output Q, measured at the PDR bus.

* ``fig_Ip``

    Active current output Ip, measured at the PDR bus.

* ``fig_Iq``

    Reactive current output Iq, measured at the PDR bus.

* ``fig_Ustator``

    Stator voltage magnitude, in pu.

* ``fig_V``

    Voltage magnitude measured at the PDR bus.

* ``fig_W``

    Rotor speed.

* ``fig_Theta``

    Generator's internal angle, in pu.

* ``fig_WRef``

    Network frequency, in Hz.

* ``fig_I``

    Injected active and reactive currents.

* ``fig_Tap``

    The PPM's main transformer tap ratio.


Below are the sections necessary to configure a PCS. Under the section called ``'PCSName'`` the user
configures the variables that the entire *PCS* shares.

* ``report_name``

    Name of the latex file used to generate the *PCS* report.

* ``id``

    Indicates the identification of the *PCS*, it is used to sort the final report.

* ``zone``

    Indicates whether the current *PCS* is a representation of zone 1 or zone 3 for RMS Model Validation.

Under the section called ``'PCSName'.'BenchmarksName'`` the user configures the particular variables
of each *BenchMark*.

* ``job_name``

    Name used to populate the Dynawo JOBS file.

* ``TSO_model``

    Dynawo model name available in the tool library, which is used to implement the TSO network of the *PCS*.

* ``Omega_model``

    Dynawo model name available in the tool library, which is used to implement the Omega model of the *PCS*.

Under the section called ``'PCSName'.'BenchmarksName'.'OCName'`` the user configures
the particular variables of each *Operating Conditions*.

* ``report_name``

    Name of the latex file used to generate the *Operating Conditions* report.

* ``reference_step_size``

    Tolerance for reference tracking tests should be adapted to the magnitude of the step change. (Optional)

* ``bolted_fault``

    In the failure tests it is necessary to configure whether it is a bolted fault.

* ``hiz_fault``

    In the failure tests it is necessary to configure whether it is a HiZ fault.

* ``setpoint_change_test_type``

    In setpoint step tests it is necessary to configure the type of setpoint affected.

Under the section called ``'PCSName'.'BenchmarksName'.'OCName'.Model`` the user configures
the model variables of each *Operating Conditions*.

* ``line_XPu``

    Reactance of the line connected to the PDR point, if the *Benchmarks* does not have several *Operating Conditions*. (Optional)

* ``SCR``

    SCR stands for Short Circuit Ratio. (Optional)

* ``pdr_P``

    Initial active power in the PDR point, if the *Benchmarks* does not have several *Operating Conditions*.

* ``pdr_Q``

    Initial reactive power in the PDR point, if the *Benchmarks* does not have several *Operating Conditions*.

* ``pdr_U``

    Initial voltage power in the PDR point, if the *Benchmarks* does not have several *Operating Conditions*.


The configuration of the infinite bus tables should be located in this section of the configuration file. The tool
is designed to locate all the placeholders in the file containing the infinite bus table, and replace them with the
values present in the configuration file. If the value depends on the type of generator, the text that identifies
the generator must be added to the variable name in the configuration file.

Example of a variable that does not depend on the type of generator: ``u_ret``
Example of a variable that depends on the type of generator: ``u_ret_HTB1``

It is also possible to assign placeholders in the following TSOModel files, so that the tool will replace them with
the values present in the configuration file:

* TSOModel.jobs
* TSOModel.dyd
* TSOModel.par

Some examples available in the tool:

* ``main_P0Pu``

    Initial active power in the main load.

* ``main_Q0Pu``

    Initial reactive power in the main load.

* ``main_U0Pu``

    Initial voltage power in the main load.

* ``secondary_P0Pu``

    Initial active power in the secondary load.

* ``secondary_Q0Pu``

    Initial reactive power in the secondary load.

* ``secondary_U0Pu``

    Initial voltage power in the secondary load.

Under the section called ``'PCSName'.'BenchmarksName'.'OCName'.Event`` the user configures
the event variables of each *Operating Conditions*.

* ``connect_event_to``

    Variable of the Dynawo model where the step is connected.

* ``sim_t_event_start``

    Start time of the event (s)

* ``fault_duration``

    Fault duration time until the line is disconnected (s). If this value depends on the type of generator,
    the variables ``fault_duration_HTB1``, ``fault_duration_HTB2``, ``fault_duration_HTB3`` must be declared,
    each of them with their respective value.

* ``setpoint_step_value``

    Increment after step trigger.

.. _toolconf:

Dynamic grid Compliance Verification Configuration
--------------------------------------------------

This section explains the global configuration of the *Dynamic grid Compliance Verification Tool*.
This configuration file should only be edited by developers, and only if in any
update of the DTR compliance document, the global conditions of any implemented
*PCS* is modified. The *Dynamic grid Compliance Verification* configuration file is located
in the ``src/dycov/configuration`` directory of the tool, with the
name ``defaultConfig.ini``.

Under the section called ``Global`` of the configuration file.

* ``latex_templates_path``

    Path where the PDF templates are saved within the package

* ``templates_path``

    Path where the pcs templates are saved within the package

* ``lib_path``

    Path where the RTE models are saved within the package

* ``modelica_path``

    Path where the modelica models are saved within the package

* ``temporal_path``

    Path to store all the files needed to perform the calculations

* ``electric_performance_verification_pcs``

    List of SM pcs to be validated (If it's empty, all the SM pcs are validated)

* ``electric_performance_ppm_verification_pcs``

    List of PPM pcs to be validated (If it's empty, all the PPM pcs are validated)

* ``model_validation_pcs``

    List of model pcs to be validated (If it's empty, all the model pcs are validated)

Under the section called ``Dynawo`` of the configuration file.

* ``simulation_limit``

    Maximum time to obtain the dynamic simulation results. The tool will stop the simulator
    execution when the configured time limit is exceeded.

* ``simulation_start``

    Simulation start time in seconds.
    Before modifying the instant of time in which the simulation starts, consider the PCSs that
    will be executed to guarantee that the existing events occur within the period that the
    simulation will be executed.

* ``simulation_stop``

    Simulation end time in seconds.
    The PCSI7 has an event that occurs in the 30th second of the simulation, to guarantee that
    the final result is stable, it is recommended to use a minimum duration of 60 seconds.

* ``simulation_precision``

    Value to configure the precision of the simulator steps.

* ``f_nom``

    Grid nominal frequency (fNom), for pu units.
    These are constants defined by Dynawo in: Electrical/SystemBase.mo.
    If you change them in Dynawo, make sure to change them here, too.

* ``s_nref``

    System-wide S base (SnRef), for pu units.
    These are constants defined by Dynawo in: Electrical/SystemBase.mo.
    If you change them in Dynawo, make sure to change them here, too.



Under the section called ``GridCode`` of the configuration file.

* ``t_com``

    Common sampling interval (in seconds)
    The t_com maximum is determined by 2 times the filter Cut-off frequency t_com < 1 / (2 * cutoff)

* ``cutoff``

    Cut-off frequency (in Hz)

* ``t_integrator_tol``

    Numerical tolerance for contemplating the fact that the t_fault, t_clear, and t_stepchange may
    actually be slightly different than configured, due to the dynawo integrator

* ``t_windowLPF_excl_start``

    Exclusion windows (in seconds) at the beginning of each filtered window, to mitigate the boundary 
    artifacts of LP filtering

* ``t_windowLPF_excl_end``

    Exclusion windows (in seconds) at the end of each filtered window, to mitigate the boundary 
    artifacts of LP filtering

* ``t_faultLPF_excl``

    Exclusion windows on transients when inserting the fault to mitigate the effect of LP filtering
    (in seconds)

* ``t_faultQS_excl``

    Exclusion windows on transients when inserting the fault (in seconds)
    Current RTE PCS I16 specifies 20 ms
    In no case will exceed 140ms (see IEC 61400-27-2 Ed. 1.0 July 2020)

* ``t_clearQS_excl``

    Exclusion windows on transients when clearing the fault (in seconds)
    Current RTE PCS I16 specifies 60 ms
    In no case will exceed 500ms (see IEC 61400-27-2 Ed. 1.0 July 2020)

* ``disable_window_filtering``

    Disable window filtering of signals, filtering is performed for the whole signal

* ``stable_time``

    Minimum time required to consider a simulation as stable

* ``thr_ss_tol``

    Numerical tolerance (in % of the value) with which it is decided when a signal (in this case
    voltage) has reached the Steady State

* ``thr_reaction_time``

    Maximum value allowed for the mean absolute error (MAE) between the reaction time in the
    calculated signal and the reaction time in the reference signal.

* ``thr_rise_time``

    Maximum value allowed for the mean absolute error (MAE) between the rise time in the
    calculated signal and the rise time in the reference signal.

* ``thr_settling_time``

    Maximum value allowed for the mean absolute error (MAE) between the settling time in the
    calculated signal and the settling time in the reference signal.

* ``thr_overshoot``

    Maximum value allowed for the mean absolute error (MAE) between the overshoot in the
    calculated signal and the overshoot in the reference signal.

* ``thr_ramp_time_lag``

    Maximum value allowed for the maximum error (ME) of the ramp time lag between the
    calculated signal versus the ideal ramp.

* ``thr_ramp_error``

    Maximum value allowed for the maximum error (MXE) of the ramp error between the
    calculated signal versus the ideal ramp.

* ``thr_final_ss_mae``

    Maximum value allowed for the mean absolute error (MAE) between the calculated signal and the
    reference signal in the regime established after the event.

* ``thr_P_mxe_before``, ``thr_P_mxe_during``, ``thr_P_mxe_after``

    Maximum value allowed for the active power maximum error (MXE) between the simulation and
    the simulated reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_P_me_before``, ``thr_P_me_during``, ``thr_P_me_after``

    Maximum value allowed for the active power mean error (ME) between the simulation and
    the simulated reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_P_mae_before``, ``thr_P_mae_during``, ``thr_P_mae_after``

    Maximum value allowed for the active power mean absolute error (ME) between the simulation and
    the simulated reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_Q_mxe_before``, ``thr_Q_mxe_during``, ``thr_Q_mxe_after``

    Maximum value allowed for the reactive power maximum error (MXE) between the simulation and
    the simulated reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_Q_me_before``, ``thr_Q_me_during``, ``thr_Q_me_after``

    Maximum value allowed for the reactive power mean error (ME) between the simulation and
    the simulated reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_Q_mae_before``, ``thr_Q_mae_during``, ``thr_Q_mae_after``

    Maximum value allowed for the reactive power mean absolute error (ME) between the simulation and
    the simulated reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_Ip_mxe_before``, ``thr_Ip_mxe_during``, ``thr_Ip_mxe_after``

    Maximum value allowed for the active current maximum error (MXE) between the simulation and
    the simulated reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_Ip_me_before``, ``thr_Ip_me_during``, ``thr_Ip_me_after``

    Maximum value allowed for the active current mean error (ME) between the simulation and
    the simulated reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_Ip_mae_before``, ``thr_Ip_mae_during``, ``thr_Ip_mae_after``

    Maximum value allowed for the active current mean absolute error (ME) between the simulation and
    the simulated reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_Iq_mxe_before``, ``thr_Iq_mxe_during``, ``thr_Iq_mxe_after``

    Maximum value allowed for the reactive current maximum error (MXE) between the simulation and
    the simulated reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_Iq_me_before``, ``thr_Iq_me_during``, ``thr_Iq_me_after``

    Maximum value allowed for the reactive current mean error (ME) between the simulation and
    the simulated reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_Iq_mae_before``, ``thr_Iq_mae_during``, ``thr_Iq_mae_after``

    Maximum value allowed for the reactive current mean absolute error (ME) between the simulation and
    the simulated reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_FT_P_mxe_before``, ``thr_FT_P_mxe_during``, ``thr_FT_P_mxe_after``

    Maximum value allowed for the active power maximum error (MXE) between the simulation and
    the test reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_FT_P_me_before``, ``thr_FT_P_me_during``, ``thr_FT_P_me_after``

    Maximum value allowed for the active power mean error (ME) between the simulation and
    the test reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_FT_P_mae_before``, ``thr_FT_P_mae_during``, ``thr_FT_P_mae_after``

    Maximum value allowed for the active power mean absolute error (ME) between the simulation and
    the test reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_FT_Q_mxe_before``, ``thr_FT_Q_mxe_during``, ``thr_FT_Q_mxe_after``

    Maximum value allowed for the reactive power maximum error (MXE) between the simulation and
    the test reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_FT_Q_me_before``, ``thr_FT_Q_me_during``, ``thr_FT_Q_me_after``

    Maximum value allowed for the reactive power mean error (ME) between the simulation and
    the test reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_FT_Q_mae_before``, ``thr_FT_Q_mae_during``, ``thr_FT_Q_mae_after``

    Maximum value allowed for the reactive power mean absolute error (ME) between the simulation and
    the test reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_FT_Ip_mxe_before``, ``thr_FT_Ip_mxe_during``, ``thr_FT_Ip_mxe_after``

    Maximum value allowed for the active current maximum error (MXE) between the simulation and
    the test reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_FT_Ip_me_before``, ``thr_FT_Ip_me_during``, ``thr_FT_Ip_me_after``

    Maximum value allowed for the active current mean error (ME) between the simulation and
    the test reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_FT_Ip_mae_before``, ``thr_FT_Ip_mae_during``, ``thr_FT_Ip_mae_after``

    Maximum value allowed for the active current mean absolute error (ME) between the simulation and
    the test reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_FT_Iq_mxe_before``, ``thr_FT_Iq_mxe_during``, ``thr_FT_Iq_mxe_after``

    Maximum value allowed for the reactive current maximum error (MXE) between the simulation and
    the test reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_FT_Iq_me_before``, ``thr_FT_Iq_me_during``, ``thr_FT_Iq_me_after``

    Maximum value allowed for the reactive current mean error (ME) between the simulation and
    the test reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_FT_Iq_mae_before``, ``thr_FT_Iq_mae_during``, ``thr_FT_Iq_mae_after``

    Maximum value allowed for the reactive current mean absolute error (ME) between the simulation and
    the test reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_reftrack_mxe_before``, ``thr_reftrack_mxe_during``, ``thr_reftrack_mxe_after``

    Maximum value allowed for the maximum error (MXE) between the simulation monitored signal and
    the reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_reftrack_me_before``, ``thr_reftrack_me_during``, ``thr_reftrack_me_after``

    Maximum value allowed for the mean error (ME) between the simulation monitored signal and
    the reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``thr_reftrack_mae_before``, ``thr_reftrack_mae_during``, ``thr_reftrack_mae_after``

    Maximum value allowed for the mean absolute error (ME) between the simulation monitored signal and
    the reference signal, for each of the windows present in the test (before, during and after
    the event).

* ``HTB1_Udims``

    List of allowed Nominal voltages by generator type HTB1

* ``HTB2_Udims``

    List of allowed Nominal voltages by generator type HTB2

* ``HTB3_Udims``

    List of allowed Nominal voltages by generator type HTB3

* ``HTB1_External_Udims``

    List of allowed External Nominal voltages by generator type HTB1

* ``HTB2_External_Udims``

    List of allowed External Nominal voltages by generator type HTB2

* ``HTB3_External_Udims``

    List of allowed External Nominal voltages by generator type HTB3

* ``HTB1_reactance_a``, ``HTB2_reactance_a``, ``HTB3_reactance_a``, ``HTB1_reactance_b_low``, ``HTB1_reactance_b_high``, ``HTB2_reactance_b_low``, ``HTB2_reactance_b_high``, ``HTB3_reactance_b_low``, ``HTB3_reactance_b_high``

    Table with reactance measurements depending on the type of generator and/or active flow
      ==============  ====  ===================
      Generator Type   a             b
      ==============  ====  ===================
      HTB1            0.05  PMax < 50MW: 0.2
                            PMax >= 50MW: 0.3
      HTB2            0.05  PMax < 250MW: 0.3
                            PMax >= 250MW: 0.54
      HTB3            0.05  PMax < 800MW: 0.54
                            PMax >= 800MW: 0.6
      ==============  ====  ===================

* ``HTB1_p_max``, ``HTB2_p_max``, ``HTB3_p_max``

    Active limit for reactance calculation

* ``Udim_63kV``, ``Udim_90kV``, ``Udim_150kV``, ``Udim_225kV``, ``Udim_400kV``

    Nominal voltage for voltage levels

Under the section called ``CurvesVariables`` of the configuration file.

* ``SM``

    List of magnitudes for which the curve calculated by Dynawo is needed in Performance Validation
    for synchronous production unit

* ``PPM``

    List of magnitudes for which the curve calculated by Dynawo is needed in Performance Validation
    for non-synchronous park of generators


* ``ModelValidationZ3``

    List of magnitudes for which the curve calculated by Dynawo is needed in Zone 3 of the
    Model Validation

* ``ModelValidationZ1``

    List of magnitudes for which the curve calculated by Dynawo is needed in Zone 1 of the
    Model Validation

Under the section called ``Debug`` of the configuration file.

* ``show_figs_t0``

    Modify the time range to include t0 in the showed range

* ``show_figs_tend``

    Modify the time range to include tend in the showed range

* ``plot_all_curves_in_html``

    In the HTML output, plot all available curves, not only the ones dictated by the PCS

* ``disable_LP_filtering``

    Disable the low-pass frequency filtering of the signals

__ https://docs.python.org/3/library/configparser.html
