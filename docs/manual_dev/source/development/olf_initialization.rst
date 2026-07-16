==========================================
Using OpenLoadFlow to initialize the tests
==========================================

The previous chapter concluded that Dynawo cannot currently be driven through
PyPowsybl. That does not, by itself, close the door on the integration: PyPowsybl
bundles more than the Dynawo binding. In particular it ships **OpenLoadFlow (OLF)**,
a static AC load-flow engine native to ``powsybl-core`` that does not involve Dynawo
at all (``import pypowsybl.loadflow as lf; lf.run_ac(network)``). This chapter asks
whether a much narrower use of PyPowsybl — using OLF *only* to initialize the tests —
is worth adopting on its own.

DyCoV computes its own initial conditions with a closed-form, ad-hoc routine
(``src/dycov/electrical/initialization_calcs.py``): the steady-state voltages, angles
and reactive powers that seed every dynamic simulation. The question is whether OLF
should replace that routine. If DyCoV's internal initialization already matches an
independent AC load flow, an OLF dependency buys no accuracy and would have to be
justified on other grounds.


Method
------

The comparison is driven by ``tools/olf_init_check/compare_init.py``. Its ground
truth is the set of *completed* per-test models that DyCoV writes to disk — the
``TSOModel.par`` / ``Producer*.par`` files (and ``TableInfiniteBus.txt`` for table
grids) that already contain DyCoV's own initial conditions. For each case the tool:

#. reconstructs the equivalent IIDM network from those files, using
   ``PypowsyblNetworkBuilder``;
#. runs OLF with the grid source as the slack bus, held at DyCoV's grid voltage, and
   the generators modelled the way these plants behave — **PV regulating the PDR node
   remotely** when a line separates the grid from the PDR (so OLF *solves* each
   generator's reactive power), or **PQ** when the grid sits directly on the PDR and
   its voltage is therefore stiff;
#. compares OLF's bus voltages and angles, each generator's reactive power, and the
   active/reactive flow at the PDR against DyCoV's recorded values.

One numerical point is worth recording, because it is easy to get wrong: on weak
grids (low short-circuit ratio) OLF's default Newton-Raphson tolerance stops
iterating too early and settles on a slightly wrong solution. Those cases only
converge to the true answer with a single, non-distributed slack and a tight
convergence criterion — the tool uses ``newtonRaphsonConvEpsPerEq = 1e-10``,
``maxNewtonRaphsonIterations = 100``, ``distributed_slack = False`` and
``slackBusSelectionMode = NAME`` with the grid as the named slack.


Discrepancies that turned out to be initialization bugs
-------------------------------------------------------

The first runs did **not** agree, and each disagreement traced back to a genuine
bug in DyCoV's initialization rather than to a modelling choice in OLF. Three were
found and fixed:

* **Plant transformer treated as a line.** The plant step-up transformer was being
  processed as if it were a line, so its turns ratio was ignored; on top of that, the
  power dispatched to the individual step-up transformers used the *total* plant power
  instead of each generator's own share. The fix matters because it corrects the
  voltage on the generator side of the transformer and the per-unit reactive
  contribution of each machine in multi-unit plants.

* **Transformer terminal orientation ignored.** The transformer's terminals were not
  read in the correct order, so the turns ratio was applied on the wrong side. The
  fix ensures the ratio steps the voltage in the right direction, which is what makes
  the reconstructed and computed voltages agree.

* **Local load at the PDR in islanding.** In the islanding tests, the load hanging off
  the PDR side was not discounted from the line flow, so the PDR angle came out
  AC-inconsistent. Accounting for that local load restores a physically consistent
  phase at the PDR. This was the one case family that had been diverging, and the
  comparison against OLF is what pinpointed it.

Once these were corrected, DyCoV's initialization and OLF agreed across the board.


Result
------

Over the full DyCoV catalogue, OLF reproduces DyCoV's internal initialization —
node voltage and angle, each generator's reactive power, and the PDR active/reactive
flow — on **every comparable case: 389 of 389 match, with 55 further cases
Not-Applicable** (no PDR reference to compare against). The agreement is to numerical
precision: across the whole set the largest node-voltage deviation is about
``4.6e-05`` pu and the largest angle deviation about ``7.5e-05`` rad, with reactive
and flow residuals one to several orders of magnitude smaller — typically around
``1e-7`` or tighter. The islanding family, formerly divergent, now matches as well.

The tool ships with a short ``README`` and seven frozen reference cases (one per
topology / grid family), so a future divergence on freshly generated results reads
as a regression.


Conclusion
----------

DyCoV's internal initialization is, for every case in the catalogue, numerically
indistinguishable from an independent AC load flow. An OLF (and therefore PyPowsybl)
dependency **cannot be justified by accuracy** — the ad-hoc routine is already as
good. What can be said in its favour is qualitative: robustness and generality
(a load-flow solver would extend naturally to meshed or asymmetric networks that the
closed-form routine is not written for), and maintainability. And the exercise
already paid for itself once, in correctness: comparing against OLF is what surfaced
and fixed the three initialization bugs above, the islanding one in particular.


Scope and outlook
-----------------

The comparison also frames the first motivation from the previous chapter — accepting
arbitrary input topologies. In parallel, DyCoV is gaining a tool that generates Dynawo
PAR fragments from an Excel specification (``tools/dynawo_par/generate_par.py``,
described in ``docs/design/Dynawo_par_generation_from_excel_design.md``). Opening the
set of admissible topologies without bound would make that Excel-driven path
combinatorially unwieldy: it is not realistic to express every topology combination in
a spreadsheet. This is a concrete argument for keeping the set of supported topologies
bounded, rather than pursuing full topological freedom through a programmatic network
builder.
