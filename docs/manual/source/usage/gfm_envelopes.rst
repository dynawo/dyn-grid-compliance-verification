=======================
GFM Envelope Generation
=======================

Overview
--------

Grid-Forming (GFM) analysis is a purely analytical workflow — no dynamic
simulation is involved. Given the key parameters of a GFM unit, DyCoV solves
the second-order differential equations that govern its dynamic behavior and
computes a set of *admissible response envelopes*: upper and lower bounds on
the dynamic response for specific grid disturbances.

The result is not a pass/fail verdict but a quantitative envelope that can be:

* examined visually to assess control robustness,
* compared against external requirements or certification criteria,
* reused across multiple engineering studies.

Because the computation is analytical, it runs much faster than a time-domain
simulation and requires no Dynawo model.


Supported disturbance cases
----------------------------

DyCoV currently supports four predefined disturbance families:

* **Amplitude Step** — computes reactive current (:math:`I_q`) and reactive
  power envelopes in response to a step change in the grid voltage amplitude.

* **Phase Jump** — computes active power (:math:`P`) envelopes in response to
  a sudden change in the grid voltage phase angle. This is typically the most
  critical disturbance for GFM units.

* **RoCoF** (Rate of Change of Frequency) — computes active power envelopes
  in response to a frequency ramp. Finite-duration events are modeled by
  superimposing step responses.

* **SCR Jump** — computes stability and power response envelopes following a
  sudden change in the Short-Circuit Ratio (grid impedance), differentiated
  between overdamped and underdamped responses.


Standard mode vs. Hybrid mode
-------------------------------

DyCoV automatically detects the operating mode from the parameters defined in
the ``[GFM Parameters]`` section of the input file.

**Standard mode** uses a single set of damping and inertia constants (``D``
and ``H``) to compute one pair of upper and lower envelopes.

**Hybrid mode** is activated when both overdamped and underdamped parameter
sets are provided (``D_Overdamped``, ``H_Overdamped``, ``D_Underdamped``,
``H_Underdamped``). In this case DyCoV:

1. Computes independent envelopes for each damping regime.
2. Constructs a **merged envelope** by taking the maximum of the upper limits
   and the minimum of the lower limits across both cases.

The merged envelope provides a robust validation range that covers both dynamic
regimes simultaneously. For Hybrid mode, an INI dump file is also generated
for full traceability (see :ref:`GFM outputs <gfm_outputs>` below).

For the input file format, see :ref:`GFM Producer Input <gfm_producer_input>`.


Basic usage
-----------

.. code-block:: console

   dycov generateEnvelopes -i <path_to_input.ini>

By default, results are written to a ``Results/`` directory in the current
working directory. To specify a different output directory:

.. code-block:: console

   dycov generateEnvelopes -i examples/GFM/Overdamped/Producer.ini

The tool reads the parameters from the INI file, computes the envelopes for
all supported disturbance cases, and writes the results under ``Results/``.


.. _gfm_outputs:

Understanding the outputs
--------------------------

Results are organized hierarchically under ``Results/``:

.. code-block:: text

   Results/
   └── PCS_RTE-IGFMx/
       └── S_<Scenario>/
           └── OC<k>/
               ├── *.csv
               ├── *.png
               ├── *.html
               └── *_ini_dump.txt   (Hybrid mode only)

Where:

* ``PCS_RTE-IGFMx`` identifies the GFM PCS family.
* ``S_<Scenario>`` identifies the disturbance scenario (e.g. Phase Jump,
  Amplitude Step, RoCoF, SCR Jump).
* ``OC<k>`` identifies a specific operating condition for that scenario.

For each combination of PCS, scenario, and operating condition:

* **CSV file** — the numerical time series of the admissible envelopes (upper
  and lower bounds for the relevant signal: :math:`P`, :math:`Q`, or
  :math:`I_q`). When ``save_all_envelopes = true`` in the INI file, the CSV
  also includes the individual overdamped and underdamped traces.

* **PNG figure** — a static visualization of the envelopes alongside the PCC
  signal. In Hybrid mode, the individual over/underdamped traces can also be
  shown.

* **HTML file** — an interactive version of the same figure (powered by
  Plotly), allowing zooming, panning, and detailed data inspection.

* **INI dump file** (Hybrid mode only) — the exact set of input parameters
  used for the calculation, including internally derived values such as the
  damping ratio :math:`\varepsilon`. Intended for full traceability when hybrid
  configurations are used.


Interpretation
--------------

The envelopes define the *admissible dynamic response bounds* for a given
disturbance and operating condition. A GFM unit whose response remains within
the envelope is considered compliant with the analytical criteria.

DyCoV does not issue a pass/fail verdict for GFM analysis. Interpretation of
the envelopes is the responsibility of the user and depends on the applicable
regulatory or engineering framework.