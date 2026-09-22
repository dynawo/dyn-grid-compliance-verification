==================================
Running Dynawo through PyPowsybl
==================================

DyCoV currently drives Dynawo through its command-line interface: for each
operating condition it writes a working directory of native input files
(``TSOModel.jobs``, ``.par``, ``.dyd``, ``.crv``, ``solvers.par``) from Jinja
templates and launches ``dynawo jobs`` as a subprocess. This backend has proven
robust, and it already supports the tool's more demanding workflows — the solver
retry strategy and the bisection algorithms (HIZ, bolted fault, CCT).

`PyPowsybl <https://pypowsybl.readthedocs.io>`_ is the Python binding of
`PowSyBl <https://www.powsybl.org>`_, and it exposes a Python-native API on top
of the same Dynawo engine. This raised the question of whether DyCoV should adopt
PyPowsybl, and three motivations were put forward:

* **Arbitrary input topologies.** DyCoV today works from a fixed catalogue of
  producer topologies — ``S``, ``S+i``, ``S+Aux``, ``S+Aux+i`` and their multi-unit
  counterparts ``M``, ``M+i``, ``M+Aux``, ``M+Aux+i``. A network built
  programmatically could accept any topology described in the inputs.
* **Executing Dynawo through PyPowsybl** as an alternative backend, replacing the
  CLI subprocess while keeping exactly the same Dynawo engine underneath.
* **Dynamic generation of each test's network**, building the exact network of a
  given test programmatically instead of copying templates and filling
  placeholders.

As a first building block for these ideas, a small standalone helper was written,
``tools/olf_init_check/network_builder.py`` (``PypowsyblNetworkBuilder``). It
assembles the structural IIDM network of a case through keyword-only wrappers over
``pypowsybl.network.create_*``, restricted to ``BUS_BREAKER`` topology. It carries
no dynamic behaviour — it is purely the electrical skeleton — and it is used only
by the initialization study described in the next chapter.

The three motivations are not independent: dynamic network generation (the third)
and arbitrary topologies (the first) only pay off if Dynawo can actually be run
through PyPowsybl (the second). The first question, therefore, was whether that
second motivation is even feasible. This chapter answers it; the design notes
behind the analysis live in ``docs/design/Dynawo_PyPowsybl_Backend.md`` and
``docs/design/Dynawo_PyPowsybl_feasibility.md``, with reproducible probes under
``tools/pypowsybl-vs-native/``.


How powsybl-dynawo runs a simulation
------------------------------------

PyPowsybl does **not** ingest DyCoV's native input files. Its dynamic-simulation
module (``pypowsybl.dynamic``) is entirely programmatic: a case is described in
memory through a ``ModelMapping`` (dynamic models and their interconnections), an
``EventMapping`` (events) and an ``OutputVariableMapping`` (curves). From that
description, the underlying ``powsybl-dynawo`` layer *generates* the DYD, PAR, JOBS
and CRV files itself and then launches ``dynawo jobs`` — the very files DyCoV writes
by hand are, on this path, produced automatically.

The consequence is that a case can only be expressed with models that
``powsybl-dynawo`` knows how to wire. Each model belongs to a **category**, which is
not a device type but a *wiring contract*: a builder that encodes which terminals
and control variables the model exposes and how they connect to the network and to
helper models such as the frequency reference. The whole WECC wind/PV/BESS family,
for example, shares a single ``Wecc`` category.


Model catalogue and its extensibility
--------------------------------------

The base catalogue of PyPowsybl 1.15 contains **164 models across 28 categories**.
Of these, the ``Wecc`` family — the one most relevant to DyCoV's non grid-forming
models — has **9** entries (the WT4 current-source wind models and the WECC
photovoltaic variants). Several models DyCoV relies on are missing from the base
catalogue: the IEC 61400-27 models, the WECC Type-3 wind and BESS models, the
numbered / ``NoPlantControl`` PV variants, the custom RTE synchronous machine, and
the pseudo/helper models DyCoV uses internally (``Measurements``, and the
``Omega`` / ``SetPoint`` / ``Ramp`` / ``Step`` helpers).

The catalogue can be extended at run time through an *additional models file* — a
JSON document supplied as a provider parameter
(``Parameters(provider_parameters={"additionalModelsFile": ...})``; note that the
``config.yaml`` mechanism was **not** picked up in testing). This registration does
work — a non-catalogue WECC model reaches ``instantiation OK`` once declared — but it
is limited in a decisive way: additional models can only be added **inside existing
categories**. A category cannot be created from PyPowsybl, because a new category
requires a Java service to be contributed upstream. Since there is no ``IEC``
category, an IEC model can at best be registered under some other category, whose
builder then wires it against the wrong connector contract: the model "instantiates"
but fails when the connections are generated. Extensibility therefore rescues models
that already fit an existing category's contract, not those that need a new one.


The blocking issue: Dynawo version drift
-----------------------------------------

Even setting the catalogue aside, a harder problem appears when a complete run is
attempted. ``powsybl-dynawo`` pins to **official Dynawo releases** — the latest being
Dynawo 1.7.0 — so PyPowsybl 1.15 generates connections for the 1.7.0 model interface.
DyCoV, however, runs against a Dynawo **1.8.0 development (master)** build, whose
model interfaces have been renamed past 1.7.0. The two no longer agree on the names
of the variables that the generated connections reference.

The mismatch is not subtle, nor confined to exotic models: PyPowsybl's *own* canonical
integration example — an IEEE-14 network with a catalogue synchronous generator, which
upstream asserts must succeed — fails against the installed Dynawo, because a
connection variable that ``powsybl-dynawo`` emits does not exist under this Dynawo
build. For instance, the active-power-step event model emits ``step_step_value`` while
Dynawo 1.8.0 exposes ``step_step``; equivalent renames affect the load switch-off and
the frequency-reference coupling to synchronous machines. These were confirmed against
Dynawo's model description files (``dynawo/ddb/*.desc.xml`` and ``*.extvar``). The
builder-internal wiring is generated with fixed names and cannot be overridden from
PyPowsybl, so per-model workarounds cannot rescue a realistic case. The net effect is
that **no dynamic simulation completes** in this environment.


Conclusion
----------

Running Dynawo through PyPowsybl is **not feasible today**, and the obstacle is a
release-cycle mismatch rather than an architectural one. It would become viable only
if both sides tracked the same official Dynawo release: once Dynawo 1.8.0 ships
officially and a matching ``powsybl-dynawo`` / PyPowsybl is published, or if DyCoV
pinned itself to the release that ``powsybl-dynawo`` already targets. Neither holds
while DyCoV depends on the Dynawo development branch, and the branch is where DyCoV's
custom models live — so the block persists for as long as that dependency does.

This rules out the second and third motivations (running Dynawo through PyPowsybl,
and generating each test's network dynamically). It leaves open a narrower question:
if Dynawo cannot be driven through PyPowsybl, is it still worth pursuing the
integration for the *static* part alone — using PyPowsybl only to initialize the
tests? That is the subject of the next chapter.
