=============
Configuration
=============

DyCoV is configured via a ``config.ini`` file, written in the standard INI
format (`Python flavor <https://docs.python.org/3/library/configparser.html>`_).
The file lives in the platform's standard application data directory:

* **Linux**: ``$HOME/.config/dycov/``
* **Windows**: ``%APPDATA%\\Local\\dycov\\``

The distributed ``config.ini`` has all options commented out, each shown with
its default value. To change a setting, uncomment the relevant line and edit
the value. We recommend duplicating the line first so you always have the
original default visible as a reminder.

Two additional profiles are provided — ``config.ini_BASIC`` and
``config.ini_ADVANCED`` — for users who want a curated subset of options.
To switch profiles, copy the desired file over ``config.ini``.


PCS Structure
--------------

DyCoV is structured as a series of independent tests corresponding to the
*PCS I\** fiches in RTE's DTR. Each fiche is organized following this
three-level hierarchy:

* **PCS** — the top-level grouping, containing one or more Benchmarks.
* **Benchmark** — defines the invariant grid-side configuration for a type of
  event. A Benchmark becomes a concrete test once its Operating Conditions
  are specified.
* **Operating Condition (OC)** — defines the initialization and event
  parameters for a specific test instance.

Understanding this hierarchy is key to interpreting both the configuration
file and the results directory.


INI file sections
------------------

Global options
^^^^^^^^^^^^^^

Options that apply regardless of the execution mode.

Basic configuration
"""""""""""""""""""

* ``electric_performance_verification_pcs``

  Comma-separated list of PCSs to run for **Electric Performance Verification
  of synchronous machines**. Leave empty to run all applicable PCSs.

* ``electric_performance_ppm_verification_pcs``

  Comma-separated list of PCSs to run for **Electric Performance Verification
  of Power Park Modules**. Leave empty to run all applicable PCSs.

* ``electric_performance_bess_verification_pcs``

  Comma-separated list of PCSs to run for **Electric Performance Verification
  of Battery Energy Storage Systems**. Leave empty to run all applicable PCSs.

* ``model_ppm_validation_pcs``

  Comma-separated list of PCSs to run for **RMS Model Validation of Power
  Park Modules**. Leave empty to run all applicable PCSs.

* ``model_bess_validation_pcs``

  Comma-separated list of PCSs to run for **RMS Model Validation of Battery
  Energy Storage Systems**. Leave empty to run all applicable PCSs.

* ``file_log_level``

  Log level for the log file. Accepted values:
  ``CRITICAL``, ``FATAL``, ``ERROR``, ``WARNING``, ``INFO``, ``DEBUG``.

* ``console_log_level``

  Log level for the console output. Same accepted values as above.


Dynawo options
^^^^^^^^^^^^^^

Options controlling the Dynawo simulation, applicable to all execution modes.

Basic configuration
"""""""""""""""""""

* ``simulation_limit``

  Simulation timeout for Dynawo, in seconds.

* ``f_nom``

  Grid nominal frequency (fNom), in pu. This must match the value defined in
  Dynawo's ``Electrical/SystemBase.mo``. If Dynawo has been customized, update
  this value accordingly.

* ``s_nref``

  System-wide S base (SnRef), in pu. Same remark as above.

Advanced configuration
""""""""""""""""""""""

* ``simulation_start``

  Simulation start time, in seconds.

  .. note::
     Before changing this value, verify that all PCS events fall within the
     configured simulation window.

* ``simulation_stop``

  Simulation end time, in seconds.

  .. note::
     PCS_RTE-I7 has an event at t=30s. To ensure the final result is stable,
     use a minimum duration of 60 seconds.


Modifying the Benchmarks of a PCS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To restrict execution to a subset of Benchmarks within a PCS, uncomment the
``[PCS-Benchmarks]`` section and specify the desired Benchmarks as a
comma-separated list:

.. code-block::

    [PCS-Benchmarks]
    PCS_RTE-I1 = Benchmark1,Benchmark2

If a Benchmark is removed from the list, its section in the final report will
be empty. Newly added Benchmarks will not appear in the report unless a
corresponding report template exists for them.

Modifying the Operating Conditions of a Benchmark
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To restrict execution to a subset of Operating Conditions within a Benchmark,
uncomment the ``[PCS-OperatingConditions]`` section:

.. code-block::

    [PCS-OperatingConditions]
    PCS_RTE-I1.Benchmark1 = OperatingCondition1,OperatingCondition2

The same report behavior applies: removed OCs leave empty report sections,
and new ones will not appear unless a template exists.

Modifying the initial conditions of a test
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To override the initial operating point of a specific test, create a section
named ``PCS.Benchmark.OperatingCondition.Model`` and set the desired values:

* ``pdr_P`` — initial active power flow at the PDR bus
* ``pdr_Q`` — initial reactive power flow at the PDR bus
* ``pdr_U`` — initial voltage at the PDR bus

.. code-block::

    [PCS_RTE-I1.Benchmarks1.OperatingCondition1.Model]
    pdr_P = 0.5*Pmax
    pdr_Q = 0.0
    pdr_U = Udim

    [PCS_RTE-I1.Benchmarks1.OperatingCondition2.Model]
    pdr_P = 0.5*Pmax
    pdr_Q = Qmax
    pdr_U = Udim


Parameter Precedence and Restriction Rules
------------------------------------------

Some parameters are defined both in the Dynawo model (**PAR file**) and in
the **Producer.ini** file.

This overlap exists only for the following parameters:

* :math:`P_{max}`
* :math:`Q_{max}`
* :math:`Q_{min}`

These parameters represent the active and reactive power limits of the
installation at the PDR.

Precedence rule
^^^^^^^^^^^^^^^

When one of these parameters is defined in both files:

* **The value defined in Producer.ini takes precedence over the value defined in the PAR file.**


Restriction rule
^^^^^^^^^^^^^^^^

The value defined in Producer.ini must be **equal to or more restrictive**
than the value defined in the PAR file.

This means:

* :math:`P_{max}` in Producer.ini must be <= PAR value
* :math:`Q_{max}` in Producer.ini must be <= PAR value
* :math:`Q_{min}` in Producer.ini must be >= PAR value

If this condition is not satisfied, DyCoV stops execution with an error.


Interpretation
^^^^^^^^^^^^^^

* The **PAR file defines the physical limits** of the model
* **Producer.ini defines the limits used during validation**

Producer.ini may therefore **restrict** the model capabilities, but never
extend them.


Task-oriented configuration examples
--------------------------------------

Configuring KPI thresholds for validation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Basic configuration
"""""""""""""""""""

**For voltage dip tests**

The following thresholds define the maximum permissible errors (in pu, base Sn
and In) between simulation and reference signals. Exclusion windows are applied
on transients at fault insertion (20 ms) and clearing (60 ms). For type 3 wind
turbines, broader exclusion windows may be requested, not exceeding 140 ms at
insertion or 500 ms at clearing (see IEC 61400-27-2).

When the reference signals come from simulation results:

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

The configurable parameters follow the pattern
``thr_<signal>_<metric>_<window>``, where:

* ``<signal>`` is one of: ``P`` (active power), ``Q`` (reactive power),
  ``Ip`` (active current), ``Iq`` (reactive current)
* ``<metric>`` is one of: ``mxe``, ``me``, ``mae``
* ``<window>`` is one of: ``before``, ``during``, ``after``

For example: ``thr_P_mxe_during``, ``thr_Iq_mae_after``.

When the reference signals come from field test measurements, the permissible
thresholds are slightly relaxed:

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

The corresponding parameters follow the same naming convention but with the
``FT_`` prefix: ``thr_FT_<signal>_<metric>_<window>``. For example:
``thr_FT_P_mxe_during``, ``thr_FT_Iq_mae_after``.

**For setpoint monitoring tests**

Regardless of the nature of the reference signal, the maximum permissible
errors on the tracked quantity (in pu, base: setpoint variation level) are:

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

Configurable parameters: ``thr_reftrack_<metric>_<window>``. For example:
``thr_reftrack_mxe_before``, ``thr_reftrack_mae_after``.


Configuring graph appearance in reports
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Advanced configuration
""""""""""""""""""""""

The temporal range (xrange) of the plots is computed automatically to show
the window from the event to the point where all curves have settled, plus a
small margin before the event. The key parameters are:

* ``graph_preevent_trange_pct`` (default: 15%) — the pre-event margin, as a
  percentage of the ``[t_event, t_SS]`` window.
* ``graph_postevent_trange_pct`` (default: 20%) — the post-settling margin,
  as a percentage of the same window.

The settling instant ``t_SS`` is determined by checking when signal values
no longer differ from the last value in the curve, using two tolerances:

* ``graph_rel_tol`` — relative tolerance (applied to all curve types).
* ``graph_abs_tol`` — absolute tolerance. For setpoint step tests, this is
  scaled by the step magnitude to reflect the relevant scale of the test.
  For other tests, it is applied directly.

To override the step magnitude used for a specific test (which affects the
absolute tolerance scaling), set ``reference_step_size`` in the corresponding
PCS section:

.. code-block::

   [PCS_RTE-I16z1.SetPointStep.Reactive]
   reference_step_size = 0.05*Qmax

Note that the xrange is first computed independently for each signal, and the
final range used across all figures is the *widest* one.

The **yrange** is handled per-figure. When the signal variation is large
enough, matplotlib's autorange is used. Otherwise, an explicit range is
calculated to avoid over-zooming on nearly flat curves. The threshold is
controlled by:

* ``graph_minvariation_yrange_pct`` (default: 2%) — if
  ``max(curve) - min(curve)`` is smaller than this percentage of the curve's
  midpoint value, autorange is disabled and the yrange is set explicitly using:

  * ``graph_bottommargin_yrange_pct`` — lower margin below ``min(curve)``
  * ``graph_topmargin_yrange_pct`` — upper margin above ``max(curve)``