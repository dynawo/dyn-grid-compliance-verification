=========================
GFM Envelope Generation
=========================

.. contents::
   :local:
   :depth: 2

Overview
--------

The **GFM Envelope Generation** is a specialized utility within the DyCoV toolset, accessible via the ``dycov generateEnvelopes`` command. Its purpose is to calculate and visualize the *theoretical* dynamic response of a Grid-Forming (GFM) asset under various simulated grid events.

Unlike the ``dycov validate`` or ``dycov performance`` commands, this utility **does not run a full dynamic simulation**. Instead, it analytically solves the second-order differential equations that model the physical behavior of a GFM system.

The primary output is a set of response envelopes (a nominal signal with upper and lower tolerance bands) that account for variations in key GFM parameters like **Damping (D)** and **Inertia (H)**.

Core Features:

* **Analytical Calculation:** Computes the expected response for events like Phase Jump, Amplitude Step, Rate of Change of Frequency (RoCoF), and SCR Jump.
* **Fast Execution:** Since it's a direct calculation, it runs much faster than a time-domain simulation.
* **Clear Outputs:** Generates CSV files for data analysis and plots in both static PNG and interactive HTML formats.

Basic Usage
-----------

The command is straightforward. The main requirements are an input file defining the GFM producer's parameters and an output directory.

The command syntax is:

.. code-block:: console

   dycov generateEnvelopes -i <path_to_input.ini> -o <path_to_output_directory>

**Example:**

.. code-block:: console

   dycov generateEnvelopes -i examples/gfm/my_gfm_producer.ini -o results/gfm_envelopes

This command will read the parameters from `my_gfm_producer.ini`, calculate the envelopes for all predefined GFM events, and save the results in the `results/gfm_envelopes` directory.

.. seealso::
   The specific format required for the input `.ini` file is detailed in the :ref:`GFM Producer Input <gfm_producer_input>` section of the Inputs guide.

Understanding the Output
------------------------

For each GFM producer file provided as input, the tool will create a sub-directory in your specified output folder. Inside this sub-directory, you will find the results for each simulated event.

**Example Output Structure:**

.. code-block:: text

   results/gfm_envelopes/
   └── my_gfm_producer/
       ├── GFM.PhaseJump.P0_50_Q0.csv
       ├── GFM.PhaseJump.P0_50_Q0.html
       ├── GFM.PhaseJump.P0_50_Q0.png
       ├── GFM.RoCoF.P0_100_Q0.csv
       ├── GFM.RoCoF.P0_100_Q0.html
       └── GFM.RoCoF.P0_100_Q0.png
       ... (and so on for all other events)

Each set of results consists of three files:

* **.csv**: A semicolon-separated file containing the time-series data for the time array, the nominal calculated signal, and the upper and lower envelopes.
* **.png**: A static image of the plot, suitable for inclusion in reports.
* **.html**: A fully interactive plot (powered by Plotly) that allows you to zoom, pan, and inspect data points. This is ideal for detailed analysis.
