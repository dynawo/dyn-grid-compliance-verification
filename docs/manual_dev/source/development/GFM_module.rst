================================
GFM Envelope Generation Module
================================

Overview
--------

The Grid-Forming (GFM) Envelope Generation Module computes and visualizes the
theoretical dynamic response envelopes of a GFM asset under various simulated
grid events. It works analytically — no time-domain simulation is involved.

Given a set of GFM unit parameters (damping, inertia, effective reactance),
the module solves the second-order differential equations that govern the
unit's dynamic behavior and generates a nominal response signal together with
upper and lower tolerance envelopes. These envelopes account for the
parametric variations in **Damping (D)** and **Inertia (H)** that characterize
the uncertainty band of the GFM response.

The module handles four disturbance families:

* **Phase Jump** — active power response to a sudden grid voltage angle change.
* **Amplitude Step** — reactive current response to a grid voltage amplitude step.
* **RoCoF** (Rate of Change of Frequency) — active power response to a
  frequency ramp.
* **SCR Jump** (Short-Circuit Ratio Jump) — active power response to a sudden
  change in grid impedance.

For each disturbance, the module exports semicolon-separated **CSV files**
with the time-series data, and generates both static **PNG** figures (via
Matplotlib) and interactive **HTML** figures (via Plotly).


Code architecture
------------------

The module is organized around a clear separation of concerns. The following
diagram shows the overall structure:

.. image:: ../figs_structure/flowchart.*
   :width: 80%
   :align: center
   :alt: GFM module execution flowchart

Orchestration layer
^^^^^^^^^^^^^^^^^^^^

``generator.py`` is the main entry point. The ``GFMGeneration`` class manages
the entire execution: it identifies which Producer/PCS combinations need to be
run, prepares the task list, and dispatches them — either sequentially or in
parallel using Python's ``multiprocessing`` library.

``gfm.py`` contains the ``GridForming`` class, which handles a *single*
simulation case. It coordinates the process for one specific event by loading
parameters, invoking the appropriate calculator, and calling the output
functions to save the results.

Parameter and data management
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``parameters.py`` defines the ``GFMParameters`` class, which reads all
configuration settings for a given run — grid conditions, producer
characteristics, and event definitions.

``producer.py`` defines the ``GFMProducer`` class, which parses the
producer's INI file to extract the GFM unit's specific parameters.

Core logic: the calculator module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is where the mathematical modeling lives. The structure follows the
**factory + abstract base class** pattern:

* ``calculator_factory.py`` — a simple factory function ``get_calculator``
  that returns the right calculator instance for the requested event type.

* ``gfm_calculator.py`` — defines the abstract base class ``GFMCalculator``,
  which establishes a common interface and provides shared helper methods
  (see :ref:`gfm_abc` below).

* Concrete calculators, one per disturbance family:

  * ``phase_jump.py`` (``PhaseJump``) — active power response to a phase jump.

    .. image:: ../../GFM_Flowchart/phase_jump.*
       :width: 70%
       :align: center
       :alt: Phase Jump calculation flowchart

  * ``amplitude_step.py`` (``AmplitudeStep``) — reactive current response to
    a voltage amplitude step.

    .. image:: ../../GFM_Flowchart/amplitude_step.*
       :width: 70%
       :align: center
       :alt: Amplitude Step calculation flowchart

  * ``rocof.py`` (``RoCoF``) — active power response to a frequency ramp.

    .. image:: ../../GFM_Flowchart/RoCoF.*
       :width: 70%
       :align: center
       :alt: RoCoF calculation flowchart

  * ``scr_jump.py`` (``SCRJump``) — active power response to an SCR jump.

    .. image:: ../../GFM_Flowchart/SCRJump.*
       :width: 70%
       :align: center
       :alt: SCR Jump calculation flowchart

Output and visualization
^^^^^^^^^^^^^^^^^^^^^^^^^

``outputs.py`` handles all file I/O. It saves data to CSV and generates both
PNG and HTML figures. A notable feature is intelligent signal trimming, which
removes unnecessary steady-state portions from the plots to keep them focused
on the transient of interest.


Execution flow
--------------

The following steps describe the full process for a single simulation case,
from invocation to output:

.. image:: ../../GFM_Flowchart/main_flow.*
   :width: 70%
   :align: center
   :alt: Main execution flow

1. An instance of ``GFMGeneration`` is created, which sets up the working
   directories.
2. The generator determines which Producer/PCS combinations need to be run.
3. ``GFMGeneration.generate()`` starts the process, sequentially or in
   parallel.
4. For each task, ``GridForming.generate()`` is invoked.
5. A ``GFMParameters`` object is configured for the specific case.
6. ``calculator_factory`` returns the correct calculator instance.
7. The calculator's ``calculate_envelopes()`` method performs the computation.
8. Results are passed to ``outputs.py`` to generate CSV, PNG, and HTML files.
9. Temporary working directories are removed.


.. _gfm_abc:

In depth: the GFMCalculator base class
---------------------------------------

``GFMCalculator`` provides the shared foundation for all event calculations.

Abstract interface
^^^^^^^^^^^^^^^^^^^

Every concrete calculator must implement two methods:

* ``get_plot_parameter_names()`` — returns the list of parameters to display
  on the figures for this event type.
* ``calculate_envelopes()`` — the main entry point for the calculation.

Key helper methods
^^^^^^^^^^^^^^^^^^^

``_calculate_epsilon_initial_check()``
    Computes the **damping ratio** :math:`\varepsilon` to determine whether
    the system response is overdamped (:math:`\varepsilon \ge 1`) or
    underdamped (:math:`\varepsilon < 1`). This drives the branching between
    the two analytical solution paths.

``_get_time_tunnel()``
    Calculates a time-dependent tolerance band that grows exponentially after
    the event, representing the uncertainty corridor around the nominal
    response.

``_limit_power_envelopes()``
    Applies final operational limits (``p_min_injection``, ``p_max_injection``)
    to the computed envelopes, ensuring the result stays within the unit's
    physical constraints.

Concrete calculator pattern
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Each concrete calculator follows the same internal structure:

1. **Initialization** — stores event-specific parameters.
2. **Main calculation** (``calculate_envelopes``) — orchestrates the
   computation for nominal parameters and their variations.
3. **Damping-dependent branching** — calls either ``_get_overdamped_delta_p``
   or ``_get_underdamped_delta_p`` depending on :math:`\varepsilon`.
4. **Analytical solution** — the ``_get_*damped_delta_p_base`` methods
   implement the closed-form solutions to the second-order ODEs.

As an example, the ``RoCoF`` calculator models a finite-duration frequency
ramp using the **superposition principle**: it computes the response to a
step-on ramp and subtracts the delayed response to a step-off ramp.

.. code-block:: python

   # rocof.py -> _calculate_delta_p_for_damping

   # 1. Response to the step-on ramp starting at event_time.
   p1, p_peak, t_response = calc_func(D, H, x_total, time_event_start)
   p1 = np.where(time_array < event_time, 0, p1)

   # 2. Response to the step-off ramp (negated) starting at rocof_stop_time.
   p2, _, _ = calc_func(D, H, x_total, time_event_stop)
   p2 = np.where(time_array < rocof_stop_time, 0, p2)

   # 3. The final response is the superposition of both.
   delta_p = p1 - p2


Utilities
---------

``constants.py`` centralizes all "magic numbers" used throughout the module:
default simulation times, time constants, delays, and so on. When adding or
modifying a time-based parameter, always define it here rather than
hardcoding it in the calculator — this keeps the module consistent and makes
future tuning straightforward.