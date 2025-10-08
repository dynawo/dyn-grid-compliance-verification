================================
GFM Envelope Generation Module
================================

.. contents::
   :local:

Overview
========

This section provides a technical overview of the **Grid-Forming (GFM) Envelope Generation Module**. The primary purpose of this module is to programmatically calculate and visualize the theoretical dynamic response envelopes of a GFM asset under various simulated grid events.

The module solves the second-order differential equations that describe the physical behavior of a GFM system, generating a nominal response signal along with upper and lower tolerance envelopes. These envelopes account for variations in key GFM parameters like **Damping (D)** and **Inertia (H)**.

The core functionalities are:

* **Analytical Calculation:** It computes the expected response for events like **Phase Jump**, **Amplitude Step**, **Rate of Change of Frequency (RoCoF)**, and **Short-Circuit Ratio (SCR) Jump**.
* **Data Export:** It saves the calculated time-series data into semicolon-separated **CSV files**.
* **Visualization:** It generates both static **PNG** plots (via Matplotlib) and interactive **HTML** plots (via Plotly) for easy analysis.

---

Code Architecture
=================

The module is designed with a clear separation of concerns, dividing responsibilities across several Python scripts.

Orchestration Layer
-------------------

* ``generator.py``: This is the main entry point and orchestrator. The **`GFMGeneration`** class manages the entire execution process. It identifies which simulation cases (PCS) to run, prepares the task list, and can execute them in parallel using Python's `multiprocessing` library for efficiency.
* ``gfm.py``: This script contains the **`GridForming`** class, which acts as the engine for a *single* simulation case. It coordinates the process for one specific event by fetching parameters, invoking the appropriate calculator, and calling the output functions to save the results.

Parameter and Data Management
-----------------------------

* ``parameters.py``: The **`GFMParameters`** class is a centralized data handler. It reads all configuration settings for a given simulation run, including grid conditions and producer-specific values.
* ``producer.py``: The **`GFMProducer`** class represents the GFM unit being simulated. It is responsible for parsing the producer's ``INI`` file to extract its specific characteristics.

Core Logic: The Calculator Module
---------------------------------

This is the heart of the module, where the mathematical modeling is implemented.

* ``calculator_factory.py``: A simple factory function `get_calculator` that returns an instance of the corresponding calculator class.
* ``gfm_calculator.py``: Defines the abstract base class **`GFMCalculator`**. It establishes a common interface and provides powerful helper methods.
* **Concrete Calculators**:
    * ``phase_jump.py`` (`PhaseJump`): Implements the solution for the active power response to a sudden grid angle change.
    * ``amplitude_step.py`` (`AmplitudeStep`): Implements the solution for the reactive current response to a grid voltage step.
    * ``rocof.py`` (`RoCoF`): Models the active power response to a frequency ramp.
    * ``scr_jump.py`` (`SCRJump`): Models the active power response to a sudden change in grid impedance.

Output and Visualization
------------------------

* ``outputs.py``: This script is dedicated to file I/O. It contains functions to save data to CSV and generate plots. A key feature is intelligent signal trimming, which removes unnecessary steady-state portions from the plots.

---

Execution Flow
==============

The process from start to finish for a single simulation case follows these steps:

1.  **Initialization**: An instance of `GFMGeneration` is created, which sets up the working directories.
2.  **Task Identification**: The generator determines which Producer/PCS combinations need to be run.
3.  **Execution**: The `GFMGeneration.generate()` method starts the process, either sequentially or in parallel.
4.  **Single Case Processing**: For each task, the `GridForming.generate()` method is invoked.
5.  **Parameter Loading**: The `GFMParameters` object is configured for the specific case.
6.  **Calculator Selection**: The `calculator_factory` is called to get the correct calculator instance.
7.  **Core Calculation**: The `calculate_envelopes()` method of the calculator is called to perform the mathematical computation.
8.  **Output Generation**: The results are passed to functions in `outputs.py` to save `.csv`, `.png`, and `.html` files.
9.  **Cleanup**: Temporary working directories are removed.

---

In-Depth: The Calculator Module
===============================

GFMCalculator (Abstract Base Class)
-----------------------------------

The `GFMCalculator` provides the foundation for all event calculations.

* **Abstract Methods**:
    * `get_plot_parameter_names()`: Each subclass must define this to specify which parameters should be displayed on its plots.
    * `calculate_envelopes()`: This is the main entry point for calculations in each subclass.
* **Key Helper Methods**:
    * `_calculate_epsilon_initial_check()`: Calculates the **damping ratio (epsilon)** to determine if the system's response is **overdamped** (:math:`\epsilon \ge 1`) or **underdamped** (:math:`\epsilon < 1`).
    * `_get_time_tunnel()`: Calculates a time-dependent tolerance band that grows exponentially after an event.
    * `_limit_power_envelopes()`: Applies final operational limits (e.g., Pmin, Pmax) to the calculated envelopes.

Calculator Implementations
--------------------------

Each concrete calculator inherits from `GFMCalculator`. The general pattern is:

1.  **Initialization**: Stores event-specific parameters.
2.  **Main Calculation (`calculate_envelopes`)**: Orchestrates the calculation for nominal parameters and their variations.
3.  **Damping-Dependent Logic**: Uses `epsilon` to call either an `_get_overdamped_delta_p` or `_get_underdamped_delta_p` method.
4.  **Analytical Solutions**: The `_get_*damped_delta_p_base` methods contain the direct implementation of the analytical solutions to the second-order differential equations.

**Example: ``rocof.py``**

The `RoCoF` calculator models a finite-duration frequency ramp by applying the **superposition principle**: it calculates the response to a step-on ramp and subtracts the response to a delayed step-off ramp.

.. code-block:: python

   # In rocof.py -> _calculate_delta_p_for_damping

   # 1. Calculate the step-on response starting at event_time.
   p1, p_peak, t_response = calc_func(D, H, x_total, time_event_start)
   p1 = np.where(time_array < event_time, 0, p1)

   # 2. Calculate the step-off response (negated) starting at rocof_stop_time.
   p2, _, _ = calc_func(D, H, x_total, time_event_stop)
   p2 = np.where(time_array < rocof_stop_time, 0, p2)

   # 3. The final response is the difference between the two.
   delta_p = p1 - p2

---

Utilities
=========

* ``constants.py``: This file centralizes "magic numbers" used throughout the simulation, such as default simulation times, time constants, and delays. When adding or modifying a time-based parameter, it should be defined here to maintain consistency.
