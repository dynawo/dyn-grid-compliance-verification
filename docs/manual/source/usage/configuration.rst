=============
Configuration
=============

Dynamic grid Compliance Verification is configured via a `config.ini` file, written in the well-known INI
format (of the `Python flavor`__). The location of this file follows the customary standard of
each platform for application data:

* Under Linux: ``$HOME/.config/dycov/``
* Under Windows: ``%APPDATA%\Local\dycov\``

The supplied INI file contains basic configuration options. They appear all commented out,
and with the default values. This way it is much easier for the user to configure anything,
and also to find out what the default value is. We also recommend the user that, whenever he wants
to set a configuration, he duplicates the line in order to preserve the information of what was the
default value, as a reminder. For the case of specific definitions of particular PCSs/Benchmarks/OCs,
the config.ini file also includes one generic example at the bottom.

Besides the ``config.ini`` file, there are two files named ``config.ini_BASIC`` and ``config.ini_ADVANCED``.
These files contain configuration parameters distinguishing between basic and advanced users. If the
user wishes, he can switch between basic and advanced user by overwriting the config.ini file with
the corresponding configuration file.

__ https://docs.python.org/3/library/configparser.html

This document describes the configuration options relevant to an user. The configuration file is
organized into sections, where each section has its own configuration options.



PCS Structure
---------------

Dynamic grid Compliance Verification is structured as a series of independent tests, these tests correspond to
the *PCS I** in the RTE's DTR document.

Each DTR document *PCS* has been implemented using the following terminology:

* PCS
    * Benchmarks
        * Operating Conditions

A *PCS* is understood to be the set of tests and/or complaince criteria necessary to validate the
producer's model.

A *Benchmark* contains the invariant description of the RTE model that will be used in the
simulation of its *PCS*. A *PCS* has one or more *Benchmarks*.

Finally, an *Operating Condition* describes the initialization conditions and/or the event conditions
of a *Benchmark*. A *Benchmark* has one or more *Operating Conditions*.



INI file Sections
-----------------

Global information
^^^^^^^^^^^^^^^^^^

In this section the global options are configured, global options are understood as those options
that do not depend on the execution mode of the tool.
The available options are:

Basic Configuration
"""""""""""""""""""

* ``electric_performance_verification_pcs``

    Comma separated list of *PCSs* that will be used in the **Performance Validation for
    synchronous production units**. Leave the parameter empty to use all *PCSs*.

* ``electric_performance_ppm_verification_pcs``

    Comma separated list  of *PCSs* that will be used in the **Performance Validation for
    non-synchronous park of generators**. Leave the parameter empty to use all *PCSs*.

* ``electric_performance_bess_verification_pcs``

    Comma separated list  of *PCSs* that will be used in the **Performance Validation for
    non-synchronous park of storages**. Leave the parameter empty to use all *PCSs*.

* ``model_ppm_validation_pcs``

    Comma separated list  of *PCSs* that will be used in the **RMS Model Validation for
    non-synchronous park of generators**. Leave the parameter empty to use all *PCSs*.

* ``model_bess_validation_pcs``

    Comma separated list  of *PCSs* that will be used in the **RMS Model Validation for
    non-synchronous park of storages**. Leave the parameter empty to use all *PCSs*.

* ``file_log_level``

    File Log level (CRITICAL,FATAL,ERROR,WARNING,INFO,DEBUG).

* ``console_log_level``

    Console Log level (CRITICAL,FATAL,ERROR,WARNING,INFO,DEBUG).


Dynawo information
^^^^^^^^^^^^^^^^^^

Under the section called ``Dynawo`` are the general options used to configure the Dynawo
simulation, regardless of the tool's execution mode.

Basic Configuration
"""""""""""""""""""

* ``simulation_limit``

    Simulation timeout for Dynawo in seconds.

* ``f_nom``

    Grid nominal frequency (fNom), for pu units.
    These are constants defined by Dynawo in: Electrical/SystemBase.mo.
    If you change them in Dynawo, make sure to change them here, too.

* ``s_nref``

    System-wide S base (SnRef), for pu units.
    These are constants defined by Dynawo in: Electrical/SystemBase.mo.
    If you change them in Dynawo, make sure to change them here, too.


Advanced Configuration
""""""""""""""""""""""

* ``simulation_start``

    The start time of the simulation in seconds.

    .. note::
        Before modifying the instant of time in which the simulation starts, consider the *PCSs*
        that will be executed to guarantee that the existing events occur within the period that
        the simulation will be executed.

* ``simulation_stop``

    The end time of the simulation in seconds.

    .. note::
        The PCS_RTE-I7 has an event that occurs in the 30th second of the simulation, to guarantee
        that the final result is stable, it is recommended to use a minimum duration of 60 seconds.

Modify the Benchmarks of a PCS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is possible to modify the list of *Benchmarks* the will be used in the validation of a
*PCS*.

#. Section
    Uncomment the 'PCS-Benchmarks' section in the configuration file.
#. Key = Value
    Uncomment the desired *PCS* and assign as **Value** a comma-separated list of the
    *BenchMarks* that will be used.

.. code-block::

    [PCS-Benchmarks]
    PCS_RTE-I1 = Benchmark1,Benchmark2

The final report of the *PCS* contains the results of the *Benchmarks* implemented in the
tool. If one of them is deleted in the configuration, the corresponding section of the report will
be empty, while the new ones will not be reflected int he report.

The input and output files of the Dynawo simulation for each configured *Benchmark* are stored
in the results directory of the *PCS*.

Modify the Operating Conditions of a Benchmark
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is possible to modify the list of *Operating Conditions* the will be used in the validation of a
*Benchmark*.

#. Section
    Uncomment the 'PCS-OperatingConditions' section in the configuration file.
#. Key = Value
    Uncomment the desired *PCS.Benchmark* and assign as **Value** a comma-separated list of the 
    *Operating Conditions* that will be used.

.. code-block::

    [PCS-OperatingConditions]
    PCS_RTE-I1.Benchmark1 = OperatingCondition1,OperatingCondition2

The final report of the *PCS* contains the results of the *Operating Conditions* implemented in the
tool. If one of them is deleted in the configuration, the corresponding section of the report will
be empty, while the new ones will not be reflected int he report.

The input and output files of the Dynawo simulation for each configured *Operating Condition* are
stored in the results directory of the *PCS*.

Modify the initial condition of a Test
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the case of modifying the initial conditions of a test of a *PCS*, it is necessary to
identify the name of the *Benchmark* (if the *PCS* only has one, its name is 'Benchmarks'),
and the name of the *Operating Condition* (if the *Benchmark* only has one should be ignored).

#. Section
    Create a new section in the configuration file called
    '`PCS`.`Benchmarks`.`OperatingCondition`.Model',where `PCS` is the name of the *PCS*,
    `Benchmarks` is the name of the *Benchmark* and `OperatingCondition` is the name of
    the *Operating Condition*.

The options that allow defining the initial condition of a test are:

* ``pdr_P``
    Defines the initial active flow at the PDR point of the model
* ``pdr_Q``
    Defines the initial reactive flow at the PDR point of the model
* ``pdr_U``
    Defines the initial voltage at the PDR point of the model

.. code-block::

    [PCS_RTE-I1.Benchmarks1.OperatingCondition1.Model]
    pdr_P = 0.5*Pmax
    pdr_Q = 0.0
    pdr_U = Udim

    [PCS_RTE-I1.Benchmarks1.OperatingCondition2.Model]
    pdr_P = 0.5*Pmax
    pdr_Q = Qmax
    pdr_U = Udim




Task-oriented configuration examples
------------------------------------

In this section we show how to carry out some typical configurations.


Configuring the KPI thresholds used for validation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Basic Configuration
"""""""""""""""""""

For voltage dip tests
~~~~~~~~~~~~~~~~~~~~~

The following thresholds apply for errors between simulation and reference signals.
Exclusion windows on transients on insertion (20 ms) and elimination of the fault
(60 ms) can be applied. For type 3 wind turbines, the producer can request a broader
exclusion (it is recognized that the behavior of the Crow bar is difficult to represent
with standard models). In no case will they exceed 140 ms when the fault is inserted
or 500 ms when the fault is cleared (see IEC 61400-27-2).
When the reference signals are simulation results, the maximum permissible errors
in pu (base Sn and In) are as follows:

+--------+--------------------+--------------------+--------------------+---------------------+
| window | active power       | reactive power     | active current     | reactive current    |
|        +------+------+------+------+------+------+------+------+------+------+------+-------+
|        | MXE  | ME   | MAE  | MXE  | ME   | MAE  | MXE  | ME   | MAE  | MXE  | ME   | MAE   |
+========+======+======+======+======+======+======+======+======+======+======+======+=======+
| Before | 0.05 | 0.02 | 0.03 | 0.05 | 0.02 | 0.03 | 0.05 | 0.02 | 0.03 | 0.05 | 0.02 | 0.03  |
+--------+------+------+------+------+------+------+------+------+------+------+------+-------+
| During | 0.08 | 0.05 | 0.07 | 0.08 | 0.05 | 0.07 | 0.08 | 0.05 | 0.07 | 0.08 | 0.05 | 0.07  |
+--------+------+------+------+------+------+------+------+------+------+------+------+-------+
| After  | 0.05 | 0.02 | 0.03 | 0.05 | 0.02 | 0.03 | 0.05 | 0.02 | 0.03 | 0.05 | 0.02 | 0.03  |
+--------+------+------+------+------+------+------+------+------+------+------+------+-------+

Below are the parameters that allow you to modify the mentioned thresholds:

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


When the reference signals are test results, the maximum permissible errors in pu
(base Sn and In) are as follows:

+--------+--------------------+--------------------+--------------------+--------------------+
| window | active power       | reactive power     | active current     | reactive current   |
|        +------+------+------+------+------+------+------+------+------+------+------+------+
|        | MXE  | ME   | MAE  | MXE  | ME   | MAE  | MXE  | ME   | MAE  | MXE  | ME   | MAE  |
+========+======+======+======+======+======+======+======+======+======+======+======+======+
| Before | 0.08 | 0.04 | 0.07 | 0.08 | 0.04 | 0.07 | 0.08 | 0.04 | 0.07 | 0.08 | 0.04 | 0.07 |
+--------+------+------+------+------+------+------+------+------+------+------+------+------+
| During | 0.10 | 0.05 | 0.08 | 0.10 | 0.05 | 0.08 | 0.10 | 0.05 | 0.08 | 0.10 | 0.05 | 0.08 |
+--------+------+------+------+------+------+------+------+------+------+------+------+------+
| After  | 0.08 | 0.04 | 0.07 | 0.08 | 0.04 | 0.07 | 0.08 | 0.04 | 0.07 | 0.08 | 0.04 | 0.07 |
+--------+------+------+------+------+------+------+------+------+------+------+------+------+

Below are the parameters that allow you to modify the mentioned thresholds:

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


For setpoint monitoring tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Regardless of the nature of the reference signal, the maximum permissible errors on the
quantity tracked in pu (base setpoint variation level) are as follow:

+--------+--------------------+
| window | quantity tracked   |
|        +------+------+------+
|        | MXE  | ME   | MAE  |
+========+======+======+======+
| Before | 0.05 | 0.02 | 0.03 |
+--------+------+------+------+
| During | 0.08 | 0.05 | 0.07 |
+--------+------+------+------+
| After  | 0.05 | 0.02 | 0.03 |
+--------+------+------+------+

Below are the parameters that allow you to modify the mentioned thresholds:

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


Configuring the aspect of graphs in the reports
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Advanced Configuration
""""""""""""""""""""""

One of the things you may want to tweak is the temporal range of the plots, in
order to show more (or less) of the signal on the graph. For instance, in cases
where you want to "zoom in" on the part of the figure where you are more
interested in. In this section we will show to control the yrange and xrange of
these plots.

Let us start with the xrange, i.e. the temporal range. The start of this xrange is
calculated by requiring that the total time window shows the window [`t_event`, `t_SS`]
_and_ a little bit of the curve before the event. This "little bit" is calculated as
being a percentage of `t_SS` - `t_event`, via the parameter `graph_preevent_trange_pct`
(default is 15%).  

The tool internally calculates the instant of time `t_SS` at which all curves can be
considered "flat" (for the purposes of plotting). This is done by applying two
tolerances, one relative (graph_rel_tol) and the other absolute (graph_abs_tol), to
check when the signal values do not differ from the last value in the curve. This check
for proximity is done in the style of Python's `isclose()` function from the math
module, in which the absolute tolerance is used to prevent problems when the numeric
values are very close to zero.  The relative tolerance is a value that applies for all
types of curves, but the absolute tolerance is scaled depending on the type of test,
because it should depend on the typical scale of the interesting features in the plot:
for step-change tests (a.k.a. "reference-tracking" tests), the scale of interest is the
magnitude of the step. Therefore the absolute tolerance `graph_abs_tol` is calculated by
multiplying the base configured value by the magnitude of the step in each type of
test. For tests that are not of the step-change type, the reference scale is assumed to
be 1pu.

To configure these tolerances:
   * Set `graph_rel_tol` and `graph_abs_tol` in the Global section of the configuration INI file.
   * If you also want to affect the absolute tolerance for reference-tracking tests,
     then you would have to override the internal definitions of the parameter
     `reference_step_size` within a specific section for each test. This entails peeking
     at the source code (`templates/PCS/model_validation/PCS_*`,
     `templates/PCS/performance/*/PCS_*`), to see how it is defined and under which
     section. Then you would write an overriding value in your user configuration. For
     instance, as in the example below.
  
.. code-block::

   [PCS_RTE-I16z1.SetPointStep.Reactive]
   reference_step_size = 0.05*Qmax


Once the `t_SS` value is calculated, the end of the xrange is calculated by adding a
small extra window that is a percentage of the [`t_event`, `t_SS`] window. This is
configured by the parameter `graph_postevent_trange_pct` (default is 20%).

Finally, remember that the xrange is first calculated separately for each signal but the
final value that is used for all figures is the *widest* one of all plotted figures.

As for the **yrange**, things are different: each figure gets its yrange calculated
individually. When the variations of the signal are large enough, the yrange is left to
be set automatically by the graphing library (matplotlib). Else, the yrange gets
calculated in order to avoid the autorange to zoom in excessively.  This avoids showing
irrelevant variations as if they were important, when it's really an almost flat
curve. The threshold at which we switch off the autorange is controlled by the parameter
`graph_minvariation_yrange_pct` (default is 2%). If the net variation of the signal,
that is, max(curve) - min(curve), is smaller than the `graph_minvariation_yrange_pct` of
its *midpoint value* (that is, (max(curve) + min(curve))/2), then the autorange is not
used, and instead we explicitly calculate the yrange:

   * we set ymin to: min(curve) - variation * `graph_bottommargin_yrange_pct`
   * we set ymax to: max(curve) + variation * `graph_topmargin_yrange_pct`




