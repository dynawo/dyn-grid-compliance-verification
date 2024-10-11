=======
Results
=======

The directory structure is designed to support simulations and electrical analyses results keeping
the data consistent and organized. Each directory and file plays a crucial role in organizing and
documenting the results of these simulations.

Organization of Results Folder
------------------------------

The *Results* directory has been organized based on the set of tests that make up the different
types of verifications that the tool allows:

.. figure:: figs_results/results.png
    :scale: 70

    Results structure

* ``Reports``
    The Reports folder contains essential documentation and analysis reports generated from the
    simulations. Each report is critical for understanding the implications of the simulation
    results, making it easier to communicate findings, validate models, and make informed decisions
    based on the data. These reports are used to document the simulation processes and outcomes
    comprehensively, ensuring clarity and transparency in the analysis.

* ``PCS*``
    The PCS* folders likely refer to different PCS where simulations are executed. Within each of
    these folders, there are subfolders indicating the type of Benchmark and Operating Condition
    being performed.

Reports
^^^^^^^

The Reports folder contains essential documentation and analysis reports generated from the
simulations:

.. figure:: figs_results/reports.png
    :scale: 70

    Reports structure

* ``summary_report.pdf``
    Summarizes the results of the PCS tests.
* ``report_*.pdf``
    Provides a more in-depth analysis, including detailed data interpretations,
    comparisons, and specific insights derived from the simulation results.
* ``full_report.pdf``
    All the detailed reports concatenated.
* ``HTML``
    The tool generates and stores in this directory an HTML file for each test that has been
    performed. Each HTML file has a dynamic version of the same figures that are displayed in
    the reports.

PCS Results
^^^^^^^^^^^

Each PCS Results folder has been organized in a hierarchical structure along three conceptual
levels, defined as follows:

#. **PCS**
    Is a top-level object for reporting results. Inside a PCS, the different test cases are
    organised in groups called Benchmarks.

#. **Benchmark**
    Is usually designed for a specific type of event (e.g., a fault, or a setpoint step change),
    to validate specific functionalities. A given benchmark becomes a concrete test case once one
    specifies the Operating Conditions.

#. **Operating Conditions (OC)** of a given benchmark
    Define everything that is needed to instantiate an actual test.

OC Results
~~~~~~~~~~

Finally, each OC Results folder contains the following files:

.. figure:: figs_results/operatingcondition.png
    :scale: 70

    PCS Results Contents

* CSV Files
    Contain calculated and reference curves for comparison.
* Dynawo Files (``*.dyd``, ``*.par``, ``*.jobs``, ``*.crv``)
    Defines the Transmission System Operator (TSO) model and Producer model.
* ``results.json``
    Stores the simulation results in a structured format.
* ``outputs``
    Folder with the Dynawo's simulation outputs (see `Dynawo documentation`__ for more info about
    Dynawo).

__ https://dynawo.github.io/

PDF Report
----------

All the PDF reports will follow this structure:

#. **Model**

   * Description of the Test Setup
        Each report begins by explaining the test setup used for the specific simulation or
        scenario. This includes details about the grid model, the operational points, and any
        important configurations or schematics that are relevant to the test being conducted.

#. **Initialization**

   * Simulation Parameters
        This section outlines the initial conditions and parameters for the simulation. It often
        includes a detailed description of how the system is set up before the simulation begins,
        such as the voltage levels, power settings, and the specific characteristics of the
        components involved (e.g., transformers, lines).

#. **Simulation**

   * Execution of the Test
        This part of the report documents the actual simulation process. It explains the visual
        representations (like graphs or charts) of the key metrics measured during the test, such
        as voltage, reactive power, active power, and current at various points in the system.
   * Timeline of Events
        For tests involving dynamic events (e.g., faults, setpoint changes), the timeline and
        sequence of these events are shown, often with detailed graphs showing how the system
        responds over time.

#. **Results**

   * Graphical Representation of Results
        The results are presented in graphical form, showing the behavior of the system during and
        after the test. These graphs include comparisons between the simulated results and
        reference curves, highlighting any deviations.
   * Analysis of Results
        This subsection provides an analysis of the simulation results, focusing on key performance
        indicators such as rise time, settling time, overshoot, and steady-state errors. It often
        includes statistical metrics like Maximum Error (MXE), Mean Error (ME), and Mean Absolute
        Error (MAE).

#. **Compliance**

   * Compliance Checks
        Each report concludes with a compliance check section. This part compares the simulation
        results against predefined thresholds to determine if the system meets the required
        standards. It confirms whether the system behavior is compliant with the specified
        technical requirements.
