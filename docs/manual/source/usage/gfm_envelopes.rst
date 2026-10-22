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

On its own, the result is not a pass/fail verdict but a quantitative envelope
that can be:

* examined visually to assess control robustness,
* compared against external requirements or certification criteria,
* reused across multiple engineering studies.

Because the computation is analytical, it runs much faster than a time-domain
simulation and requires no Dynawo model.

They are also what the curves of a storage unit are checked against in its
performance verification, where ``dycov performance`` gives a verdict for every
test of the DTR Fiche I18 (see :ref:`Grid Forming tests in the performance
verification <gfm_performance>`). The envelopes this command writes can be
given to it, as the fiche has them sent to the producer.


.. _gfm_tests_by_unit:

Tests by kind of unit
---------------------

Which tests a unit is given follows from what it is, declared with
``generator_type`` in the ``[DEFAULT]`` section of its input file (see
:ref:`GFM Producer Input <gfm_producer_input>`):

* ``BESS`` — a non-synchronous storage unit of type C or D, the scope of the
  DTR Fiche I18 "Grid Forming". It is given the full matrix of the fiche as
  one PCS, ``PCS_RTE-I18z1`` (``templates/PCS/gfm/BESS``), whose scenarios are
  those of the four tests of the fiche:

  .. list-table::
     :header-rows: 1

     * - I18 test
       - Scenarios
       - Operating conditions
     * - Test 1, phase jump of the voltage at the infinite bus
       - ``S_VolAngStep1`` to ``12``
       - OC1 to OC5
     * - Test 2, amplitude step of the voltage at the infinite bus
       - ``S_VolAmpStep1`` to ``6``
       - OC1 to OC7
     * - Test 3, short-circuit ratio jump
       - ``S_SCRup1``, ``S_SCRdown1``
       - OC1 to OC5
     * - Test 4, frequency variation (RoCoF)
       - ``S_Rocof1`` to ``12``
       - OC1 to OC5

  The scenarios of a test inherit its settings from the alias file next to
  the PCS (``PhaseJumpTest``, ``AmplitudeStepTest``, ``SCRJumpTest`` and
  ``RoCoFTest``). The operating points are given in pu of the rating of the
  converter, and the grid short-circuit ratios are those of the fiche:
  ``SCRmin = 2``, ``SCRmed = 10`` and ``SCRmax = 20`` (``[GFM]`` section of
  the configuration). Test 5, the faults, is for information only in the
  fiche: it has no envelope, and DyCoV does not generate it. The fiche applies
  at the PGU terminals, the Node 1 of the Zone 1 of the DTR, and so the PCS is
  one of Zone 1.

* ``PPM`` — a power park module, which the fiche does not cover. It keeps the
  four PCS built on the envelope method agreed with RTE before the fiche
  existed (``templates/PCS/gfm/PPM``).


Supported disturbance cases
---------------------------

DyCoV currently supports four predefined disturbance families:

* **Amplitude Step** — computes reactive current (:math:`I_q`) envelopes in
  response to a step change in the grid voltage amplitude.

* **Phase Jump** — computes active current (:math:`I_p`) envelopes in response
  to a sudden change in the grid voltage phase angle. This is typically the
  most critical disturbance for GFM units.

* **RoCoF** (Rate of Change of Frequency) — computes active current
  (:math:`I_p`) envelopes in response to a frequency ramp. Finite-duration
  events are modeled by superimposing step responses.

* **SCR Jump** — computes stability and power response envelopes following a
  sudden change in the Short-Circuit Ratio (grid impedance), differentiated
  between overdamped and underdamped responses.


Standard mode vs. Hybrid mode
-----------------------------

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

   dycov generate_gfm_envelopes -i <path_to_input.ini>

By default, results are written to a ``Results/`` directory created next to
the input file (inside the directory that contains it). To specify a
different output directory, use ``-o``:

.. code-block:: console

   dycov generate_gfm_envelopes -i examples/GFM/Overdamped/Producer.ini -o gfm_results

The tool reads the parameters from the INI file, computes the envelopes for
all supported disturbance cases, and writes the results under the output
directory.

EMT mode
^^^^^^^^

By default, the generated envelopes are meant to be compared against RMS
simulations. Pass ``-e``/``--emt`` to generate envelopes for comparison
against EMT simulations instead:

.. code-block:: console

   dycov generate_gfm_envelopes -i examples/GFM/Overdamped/Producer.ini -e

In EMT mode, the envelopes and the PCC signal are shifted in time by the
``emt_delay`` value (in seconds) read from the ``[GFM Parameters]`` section of
the input file, to account for the initial response of an EMT simulation. The
delay defaults to 0.02 s when the key is absent; all the shipped examples
define it explicitly. Without EMT mode, ``emt_delay`` has no effect.

A unit whose curves come from EMT simulations may declare it in its input file
instead, with ``emt = true`` in its ``[GFM Parameters]`` section: the
envelopes are then for EMT simulations without ``-e``, as they are when the
model validation generates them.


.. _gfm_outputs:

Understanding the outputs
-------------------------

Results are organized hierarchically under ``Results/``:

.. code-block:: text

   Results/
   ├── Reports/
   │   └── report.pdf
   └── <PCS>/
       └── S_<Scenario>/
           └── OC<k>/
               ├── *.csv
               ├── *.png
               ├── *.html
               ├── *_ini_dump.txt
               └── results.json

Where:

* ``<PCS>`` identifies the GFM PCS: ``PCS_RTE-I18z1`` for a storage unit,
  ``PCS_RTE-IGFM1`` to ``4`` for a power park module.
* ``S_<Scenario>`` identifies the disturbance scenario (e.g. Phase Jump,
  Amplitude Step, RoCoF, SCR Jump).
* ``OC<k>`` identifies a specific operating condition for that scenario.

The **PDF report** in ``Reports/`` gathers every test of the run. Its summary
lists them all, and each PCS has a section that describes its tests, with a
page per scenario and operating condition: the parameters of the test, the
envelope figure and a link to its HTML version. It is compiled with LaTeX, so
the packages listed in the installation instructions are needed, as for the
verification reports.

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

* **INI dump file** — the exact set of input parameters used for the
  calculation, including internally derived values such as the damping ratio
  :math:`\varepsilon`, one for each damping regime in Hybrid mode. Intended for
  full traceability.

* **results.json** — what describes the envelopes: the current they bound,
  whether they are for EMT simulations, the duration of the event and the
  parameters printed on the figure. The model validation reads it back, with
  the CSV file, when it is given the envelopes.


Interpretation
--------------

The envelopes define the *admissible dynamic response bounds* for a given
disturbance and operating condition. A GFM unit whose response remains within
the envelope is considered compliant with the analytical criteria.

On its own, this command issues no pass/fail verdict: interpretation of the
envelopes is the responsibility of the user and depends on the applicable
regulatory or engineering framework. The verdict on the curves of a storage
unit is that of the criteria of the DTR Fiche I18, which its performance
verification applies.


.. _gfm_performance:

Grid Forming tests in the performance verification
--------------------------------------------------

The performance verification of a storage unit given its curves (``dycov
performance -c``) runs the tests of the DTR Fiche I18 along with those of the
other fiches, under ``PCS_RTE-I18z1``; a power park module or a synchronous
machine is not given them. They are not simulated, and a verification run on a
Dynawo model (``-m``) leaves them out: the curves the producer delivers for
them are checked against their envelopes, which are:

* read from the directory given with ``-g``/``--gfm-envelopes``, the output of
  ``dycov generate_gfm_envelopes`` for the producer. It holds a subdirectory
  per producer, named after it, or else it is the output of a single run,
  which then serves every producer:

  .. code-block:: console

     dycov generate_gfm_envelopes -i ProducerCurves/Producer.ini -o Envelopes
     dycov performance -c ProducerCurves -g Envelopes

* or else generated from the ``[GFM Parameters]`` section of the INI file of
  the producer (see :ref:`GFM Producer Input <gfm_producer_input>`), the same
  section an envelope generation reads, so that one INI file serves both
  commands. The envelopes are for RMS simulations unless the section declares
  ``emt = true``.

The fiche tests a single converter, the PGU, so the INI file describes it: its
limits, in its ``[DEFAULT]`` section, are those the envelopes are bounded by. A
producer that declares no ``[GFM Parameters]``, and whose envelopes are not
given, has its Grid Forming tests reported as missing the envelopes. With
``-p PCS_RTE-I18z1``, the run checks the Grid Forming tests alone.

The curves are those of the producer (``ProducerCurves/<producer>/``), laid
out as any other set of curves given to DyCoV: a ``CurvesFiles.ini`` and, for
every test, a curve file named after the test
(``PCS_RTE-I18z1.S_VolAngStep1.OC2.csv``, or a COMTRADE or EUROSTAG file) with
its ``.dict``. The fiche asks for the RMS active and reactive currents and the
voltage at the PGU terminals, sampled every 1 ms at most and covering at least
from the event to the steady state. They are the Node 1 of the Zone 1 of the
DTR, so the dictionary may name them after that bus, or after the connection
point as the other performance curves do:

.. code-block:: ini
   :caption: CurvesFiles.ini

   [Curves-Dictionary]
   time = time

   [Curves-Dictionary-Zone1]
   InternalNode1_BUS_ActiveCurrent = Ip
   InternalNode1_BUS_ReactiveCurrent = Iq
   InternalNode1_BUS_Voltage = U

   [Curves-Dictionary-Zone3]

The ``.dict`` of each test declares in its ``[Curves-Metadata]`` section the
time of the event in the curves, ``sim_t_event_start``, which DyCoV aligns
with the event of the envelopes. The currents are in pu of the rating of the
converter.

The curves are low-pass filtered at the 30 Hz the DTR asks for, given the
response dynamics of Grid Forming units (``cutoff`` of the ``[GFM]`` section;
the other verifications keep the 15 Hz of ``[GridCode]``), each side of the
event apart. A test is **compliant** when:

* the current the envelope bounds (:math:`I_p` or :math:`I_q`) stays inside
  it, over the time both cover, within ``envelope_tolerance`` (0.005 pu, which
  also absorbs the narrowing of the envelopes in their first 20 ms);
* no oscillation of the active or reactive current, nor of the voltage when it
  is given, between ``damping_f_min`` and ``damping_f_max`` (0.1 Hz and
  10 Hz) is damped less than ``thr_damping_ratio`` (40 %). The damping is
  estimated with the Matrix Pencil method, on each window between the event
  discontinuities (during the frequency ramp and after it, for the RoCoF
  tests). Oscillations smaller than ``damping_min_amplitude`` (0.001 pu) are
  the numerical noise of a nearly flat curve, and are not considered.

Within the envelopes and well damped, the converter has also stayed connected
and stable, the last criterion of the fiche. A test whose curves miss one of
the currents is reported as missing producer curves; one whose curves cannot
be read is an invalid test.

Every test is in the summary of the report, and the tests whose curves were
judged have a page in the section of the PCS: the parameters of the test, the
figure of the envelopes with the filtered curve, and the envelope and damping
checks with their verdict. The results of each test are under
``Results/<producer>/PCS_RTE-I18z1/S_<Scenario>/OC<k>/``, as for the envelope
generation, and its ``results.json`` adds the compliance, how far the curve
leaves the envelope and over which time they are compared, and every
oscillating mode found (curve, window, frequency, damping ratio and
amplitude).

.. note::
   The Matrix Pencil method fits the response with a sum of damped
   exponentials. A response with corners, as when a current enters or leaves
   its limit, is not such a sum, and the fit may then show lightly damped
   modes of small amplitude that are not oscillations of the unit. Every mode
   found is listed, with its amplitude, in the ``results.json`` of the test.