# Changelog

What changes between releases for someone who uses DyCoV: the version of Dynawo the release is
built on, and anything a user has to do to their own producer model, workbook or configuration
before the new release will run it. Fixes that need nothing from the user are listed in one line;
the issue each one points at holds the explanation.

## Unreleased

### Storage installations of types C and D are validated against the Fiche I16.2

The revision of the DTR of 20260723 gives a storage installation of type C or D its own version of
the Fiche I16, the Fiche I16.2. Its Zone 1 runs the setpoint steps on a grid of short-circuit
ratio 2 and simulates the tests of the Fiche I18 (Grid Forming); its Zone 3 has neither the fault
of the Fiche I5 nor the ramp of the grid frequency; both filter the curves at 30 Hz, on a common
sampling interval of 1 ms.

DyCoV applies it to the installations the DTR puts in category C or D, which the tool computes
from the connection voltage and the maximum power at injection of the INI file of `Zone3/`, so
nothing has to be declared for it. A run that follows an earlier revision gives them the Fiche I16
of that revision, which has no Fiche I18 to repeat.

Zone 1 compares the curves the Fiche I16.1 compares, in every test: the active and reactive
power at the point the converter controls and the currents Ip and Iq at InternalNode2, with the
voltages at InternalNode1 and InternalNode2. The reference curves of the tests of the Fiche I18
declare them too, besides the curves that fiche asks for at the output of the unit.

The fiche asks for every test of the Fiche I18 at its operating conditions OC2 and OC3, and at the
others only when they drive the unit into current limitation, which the tool does not check on a
model: it runs them at OC1, OC4 and OC5, and at OC6 and OC7 of the grid voltage steps, only when
`run_OC1`, `run_OC4`, `run_OC5`, `run_OC6` or `run_OC7` is set to true in the `[PCS_RTE-I16z1]`
section of `config.ini` or of a description of your own of the PCS. As RTE reads the fiches, the
unbalanced faults of the Fiche I18 are left out, and so is its `S_Fault7`, which no profile
defines; `S_VolAngStep12` jumps the other way from `S_VolAngStep11`; the phase jumps and the
voltage steps are sized with the effective reactance of the ideal converter of the fiche, 0.27 pu,
whatever the unit's, so its events are those its tables print; and the active power of the
operating points is in pu of Pn, the maximum active power of Zone 1. The tests of the Fiche I18
that are not faults are tracking tests of the active current at InternalNode2, or of the reactive
one for a step of the grid voltage: besides their tracking errors, relative to the change of the
reference or to the peak of a transient, and their final error, a step of the grid voltage checks
the rise and settling times and the overshoot of the reactive current and reports its reaction time
without a verdict, and the other tests, transients the active current returns from, its settling
time and overshoot against the peak of the reference. The unit runs as delivered, as RTE asked,
and a ramp of the frequency starts from the power the unit settles at after the frequency reaches
its starting value. The jumps of the short-circuit ratio leave OC1 out, since at no power they
move no current and leave nothing to validate, and the recovery of the active power after a fault
is not timed at OC1, where there is no power to recover. The reference curves of the GFM examples
cover OC2 and OC3 only.

Two of the Grid Forming converters of Dynawo, the droop one and the EPRI one, can be the Zone 1
unit: the examples `BESS/GridFormingDroop` and `BESS/GridFormingEpri` are such installations, of
type C, with a WECC plant of 40 MW at 225 kV in Zone 3. The droop one keeps its transformer
inside, so its InternalNode2 is its filter capacitor, where it takes its references. The
`BESS/WECC` example, whose plant had that same size and so was of type C too, is now of 15 MW, a
type B: under this revision a storage installation of type C has to be Grid Forming, and its unit
is not.

### Fiche I5 applies to storage installations of type B alone from the DTR revision 20260723

The revision of the DTR of 20260723 asks the Fiche I5 of a storage installation of type B alone,
where the earlier revisions asked it of types B, C and D. Under that revision, the performance
verification of a storage installation of type C or D leaves PCS I5 out and says why in the log.
The tool computes the category as the DTR does, from the connection voltage and the maximum power
at injection of the producer's INI file, so nothing has to be declared for it.

### The report shows the values each test ran with

Every simulated test now lists, next to the solver of its simulation, the conditions it ran with
once its definitions are resolved: the operating point, the short-circuit ratio or impedance and
the impedances of the grid, the impedance of the fault, including the one the high-impedance or
bolted fault search settled on, and the event and its step or the voltages of its dip or swell.
The same values are recorded in the `[Conditions]` section of the `simulation_inputs.ini` of each
test.

### The revision of the DTR is set in the configuration

The configuration the tool ships no longer names a revision of the DTR, and `--dtr` is gone from
the command line. Set `current` in the `[DTR]` section of `config.ini`, or of the file given with
`--user-config`, to the revision in force when the PTF of the installation was signed. A run that
finds none, or one the tool does not implement, stops and lists the revisions it implements.

### Workbooks name the version of their template

`dycov excel2inputs`, and `validate` and `performance` with `--excel`, warn when a workbook names
a template other than the one the release reads, in the `format_version` cell of its
`Infos générales ->` sheet: rows that differ between the two would be dropped or missing. The
templates of 1.2.1 said 1.2.1 and those of 1.3.0 said 1.0.0, so every workbook made on them is
warned about: copy its data into `workbooks/Producer_IEC.xlsx` or `workbooks/Producer_WECC.xlsx`,
whose rows the next sections describe (#701).

### The fault searches run on the simplified solver

The searches for the impedance of the high-impedance and bolted faults run each of their
simulations on the SIM solver and stop it 2 s after the fault is cleared, or 2 s after a permanent
fault starts. A simulation that fails is retried as any other and, if SIM still cannot simulate it,
simulated again on the solver of the test; a high-impedance search that ends without its dip on
SIM, whose dip may jump past the target, is run again on the solver of the test. The test is then
simulated as before. The impedance they settle on may differ slightly from the one they found on
IDA. `fault_search_solver_lib` and `fault_search_time_after_clearing`, in `[Dynawo]`, change both
(#644, #830).

### The IEC workbook carries the tables of the models

The IEC template, now version 1.4.0, lays out the tables its models read point by point: the
current and reactive power limits of the turbine, the tables of the plant controller and the
decoupling protection curves, which the previous template listed one parameter per row. Copy the
data of a workbook made on the template of 1.3.0 into `workbooks/Producer_IEC.xlsx`: it is still
read, with a warning, and its protection curves written as before (#394).

The IEC examples fill in the two current-limit tables of their turbines, `TableIpMaxUwt` and
`TableIqMaxUwt`, in their workbooks and PAR files, with the values Dynawo gives them by default,
so their results do not change. Those tables bound the currents along with `IMaxPu` and
`IMaxDipPu`, the reactive one to 0.33 pu around the nominal voltage: a model built from an example
now shows them, to be adapted with the current limits (#789).

### The workbooks carry the tests of every revision of the DTR

The rows of the signal sheets are read as the tests of the revision of the DTR being validated,
so the records a workbook gives reach the tests that revision runs. Both templates, the WECC one
now version 1.4.0 as well, carry a row for every test of every revision: a second I5 row, the
impedant fault, after the bolted one, and a third I7 row, the swell at Q = 0, which the revisions
from 3.5 on run instead of the two of the base. Copy the data of a workbook made on an earlier
template into `workbooks/Producer_IEC.xlsx` or `workbooks/Producer_WECC.xlsx` and fill the new
rows: a workbook without them is still read, and the conversion names the tests it has no row
for (#679).

### Your report templates replace the packaged ones

A report template in `templates/reports` of the configuration directory replaces the packaged one
of the same name, and the one of the revision of the DTR, as the manual says; until now they
overwrote it. A copy of a packaged template left there now hides the packaged one, and the
corrections later releases bring to it, so remove the copies you do not mean to change (#686).

### A copy of `commonz1.tex` names the schematic of its unit

The report of each Zone 1 unit draws its own schematic, which `commonz1.tex` names through
`\ProducerFiles`. A copy of `commonz1.tex` among your report templates made on an earlier release
still names the shared template, and its report draws both circuits one over the other: copy it
again from the package, or write `\ProducerFiles.circuit_z1_fault.tikz` and
`\ProducerFiles.circuit_z1_setpoint.tikz` where it names the schematics (#793). Such a copy also
lacks the figure of the frequency of the converter that the RoCoF tests of the Fiche I16.2 draw
(#813).

### Fixed

- The summary table of the PDF report lists every test, page after page: it was cut at the end of
  its first page, so a run of more than about 56 tests, as every one of the Fiche I16.2 is, lost
  the rows after it, those of Zone 3 and of the failed tests among them.
- The report of a PCS of many tests no longer holds the curves of all of them in memory, which
  made the full report of the Zone 1 of a storage installation of type C or D exceed 6 GB: the
  curves of each test wait on disk until the report draws them.
- The IEC wind power plants of zone 3 are measured at Node2 itself, as the turbines of zone 1
  are since 1.3.0. With the low-voltage transformer inside the converter model
  (`WPP_ConverterLVControl = false`), their voltage and powers there were read on its grid side,
  at Node1, and so were the currents at Node2 the tool derives from them (#634).
- Every test an F16 declaration names is run, recorded or not, and one without its record ends as
  missing its reference curves, where the notes of 1.3.0 said only the recorded ones run: declare
  only the tests recorded (#684).
- The page of a model-validation test without reference curves gives the dynamic behaviour of
  the simulated curves, where it always said "unstable"; when it cannot be told, it says N/A
  (#685).
- `generate_gfm_envelopes` keeps the envelopes of every PCS when one it lists generates none,
  because it is not a valid PCS, its description cannot be read or its generation stopped before
  its first envelope: it reports that PCS and leaves it out, where it stopped there and lost the
  envelopes of the PCS listed after it (#688).
- The reports of fiche I16 zone 1 give the 500 ms high-impedance fault as a dip of 0.7 Un, where
  they said V = 0.7 Un: the voltage falls to 0.3 Un (#697).
- The Zone 1 schematic of the report follows the Zone 1 model in a parallel validation too, where
  it drew the group transformer or left it out depending on which PCS prepared its report first
  (#740).
- A power park module of 250 MW or more connected at HTB1 takes the reactance b the DTR gives it,
  0.54 up to 800 MW and 0.6 above, where it took 0.3: its line reactances in the fiches I2, I5,
  I10 and I16 zone 3, and the reactance of the impedant fault, change with it. Such a unit reads
  its steps of b from `HTB1_reactance_b_PPM` and the powers between them from `HTB1_p_max_PPM`,
  so a configuration that changed them through `HTB1_reactance_b_low`, `_b_high` or
  `HTB1_p_max` now changes those two keys instead (#744).
- The SCR jump no longer marks its envelopes as inconsistent when the variations of D and H fall
  on both sides of critical damping: each takes the response of its own regime, as in the RoCoF
  (#761).
- `generate_gfm_envelopes` reads the producer file `-i` names and no other INI of its folder, and
  stops when that file does not exist (#766).
- The native installation lists `tex-gyre`, the fonts of the PDF manual the installer compiles,
  and the installer checks for them before it starts (#768).
- The figures of the GFM RoCoF tests give their initial frequency and RoCoF in Hz with the
  nominal frequency of the configuration, where they took 50 Hz (#770).
- The continuous integration runs on pushes to master as well, builds the wheel and runs the tests
  once, against the installed package, on current versions of its actions (#844).
- The Epsilon of the GFM SCR jump figures is that of the producer's D and H, not that of one of
  their variations, and a hybrid run leaves it out as it does D and H (#771).
- A run whose process group is told to end, as a closed terminal does, ends within 15 s of the
  signal even when its pool waits for a worker it can no longer start, the signal having also ended
  the process that starts them. Such a run says on its error output that its shutdown did not end
  (#850).
- The GFM envelopes scale the base angular frequency `Wb` of the PCS, given for 50 Hz, to the
  nominal frequency of the configuration (#779).
- The native installer, the image and `build_and_install.sh` install the dependencies at the
  versions `uv.lock` pins, which the release is tested with, where each installation took the
  latest ones of the day (#841).
- The SCR jump envelopes keep their shape outside the 30 ms hold after the event when the
  producer's minimum power is above zero or its maximum below zero (#780).
- The minimum versions of numpy, pandas, SciPy, matplotlib and lxml are the oldest ones that
  install on each Python version the tool supports, 3.13 and 3.14, and pass the tests, where they
  named versions that do not install there. On pandas 2 the filter of the curves no longer
  changes the curves it is given (#840).
- In a model with several Zone 1 units, the report draws for each unit its own Zone 1
  schematic, where every unit got that of the unit rendered last (#793).
- `tools/dynawo_par`, which the conversion of workbooks of the package replaced, is retired, and so
  are the `dynawo-pypowsybl` extra, the `-p` option of `build_and_install.sh` and the tools of the
  PyPowSyBl study, whose conclusions stay in the design documents. The package says it runs on
  Linux and points its bug tracker at the issues of the repository, and no longer lists a data
  file it does not ship (#847).
- `generate_gfm_envelopes` stops, naming each value, when the producer's D, H or Xeff cannot give
  envelopes (#782).
- `dycov anonymize` asks for its output directory, `-o`, without which it ended with a TypeError,
  and for the curves to anonymize, `--curves` or `--results`. It refuses an output directory that is
  or holds the `--curves` one, which it emptied, deleting the curves it was given (#836).
- A list of the configuration may have spaces around its commas, or a comma at its end: a PCS
  listed after a space was looked for with that space in its name, and the run stopped with an
  error that said nothing about the cause. The voltage figure of the swell of fiche I16 zone 3
  for storage units, left out by such a space in the shipped description, is back (#792).
- The index DyCoV generates in an empty directory of reference curves lists the tests of the
  Fiche I16 the installation runs, as the description of its PCS gives them for the selected
  revision of the DTR and its category: a storage of type C or D gets those of the Fiche I16.2,
  where every model got the tests of the base revision of I16 (#835).
- A producer model without its `Producer.ini`, its DYD or its PAR file ends the run with a single
  error that names the file and the directory it was looked for in, where it ended in a
  `TypeError` and a stack trace, or named no directory. A model directory of the other
  verification, such as the one of a model validation given to `performance`, is told this way;
  a Zone 1 unit without its DYD is not a unit of the model, and the count of units tells it
  (#637).
- The voltage setpoint step of a Zone 1 unit that controls the voltage at InternalNode2 is checked
  on the voltage there, which its figure draws the setpoint over, where its tracking errors and
  step-response indicators were measured on the voltage at InternalNode1 (#834).
- The dip a permanent bolted fault or a voltage table makes is measured to its real depth: the
  first measured none, and the second was measured from inside the smoothed step of the table, at
  about half its depth. The report draws the target of reactive current from it in the tests that
  check `imax_reac` (#814).
- A Zone 1 test of a power park module that ends without curves, a fault whose dip is out of
  reach for instance, no longer leaves the run without its PDF: its page says the test produced
  no curve, as the pages of storage already did, and a fault whose dip is out of reach says it
  was not simulated for that reason. A copy of the `commonz1.tex` of the power park modules in
  your report templates still stops the PDF on such a page: copy it again (#831).
- Every test of a parallel run gets its interactive HTML page: when the reports of several PCS
  were prepared at the same time, one could fail to create the HTML folder another had just
  created, and the page of its test was left out (#815).
- An optional number of the producer INI left empty, `Xeff` of `[GFM Parameters]`,
  `p_min_injection`, `p_min_consumption`, `p_max_consumption` or `s_nom`, reads as not given, where
  it stopped the run before its first test (#832).
- The ramp of the grid frequency of the Fiche I16 in Zone 3 is the one its PCS description declares:
  the simulation applied the start, the duration and the height written in the grid model, so a
  description of your own, a revision or a declaration of the Fiche F16 that changed them moved
  only the checks and the report, and so did reference curves that put the event at another
  instant (#816).
- The page of a test without reference curves no longer lists the curves missing from the record
  of the test before it in the same benchmark, which could also turn a test whose fault dip was
  out of reach into an invalid one (#823).
- `dycov excel2inputs` keeps the curves already in the folder it writes to when the workbook names
  that same folder for them, where it stopped with a SameFileError (#838).
- The lines the log writes once a test is over, while the report of its PCS is prepared, the
  next PCS is loaded or the summary of the run is written, no longer carry the label of that
  test (#825).
- The shared page of the Fiche I16.2 gives the value of the step of the high-impedance faults,
  the dip their search aims at, which its column left empty (#833).
- A `reference_step_size` the tool rejects no longer ends the run without summary or report: the
  log names the file and line that define it, and the figures of its test show their default
  time range. A PCS whose report cannot be prepared leaves the PDF without its pages, where it
  ended the whole run, summary included, with `Error during verification: 'producer'` (#824).

## 1.3.0 — 2026-10-29

### Built on Dynawo 2.0.0

This release ships and requires Dynawo 2.0.0. The previous one shipped a Dynawo 1.8.0 nightly in
which the voltage ride-through protection described below did not exist. The Dynawo models
themselves changed, so a producer model prepared for the previous release does not load unchanged.

The simplest way through is to update the workbook and regenerate the model with
`dycov excel2inputs`.
Editing the DYD and the PAR by hand works too, and the four points below are what has to end up in
them either way.

#### WECC models: the voltage ride-through protection is now mandatory

Every WECC model — photovoltaic, wind and storage — now embeds a protection that watches the
unit's voltage and opens its breaker. It brings eight parameters with it, none of which has a
default value, so each generating unit's parameter set has to declare them:

    lhvrt_UUnderPu            the voltage below which the low-voltage side arms
    lhvrt_UOverPu             the voltage above which the high-voltage side arms
    lhvrt_tLagAction          the delay between the decision and the breaker opening
    lhvrt_tUFilt              the time constant of the voltage measurement filter
    lhvrt_TablesFile          the file holding the two capability curves
    lhvrt_TabletUunderUfilt   the name of the low-voltage curve in that file
    lhvrt_TabletUoverUfilt    the name of the high-voltage curve in that file
    lhvrt_TablesOnFile        true

The file `lhvrt_TablesFile` names has to sit beside the producer model's DYD and PAR, and holds the
two capability curves — the time the unit may stay connected against the voltage the protection
watches. Without the parameters the run stops at once with a missing-parameter error; without the
file it does not start at all.

The curves the examples carry are those of the French grid code, and they allow 100 s anywhere
inside the normal voltage band. That is deliberate: the counter the protection compares against the
curve does not reset when the voltage comes back into that band, so the time allowed there has to
outlast the simulation — otherwise a unit that rode the fault through is disconnected once the
counter reaches the allowance. The behaviour has been reported to the Dynawo team; see issue #606.

#### IEC wind turbines, zone 1: the low-voltage transformer moved

`WT_ResPu`, `WT_XesPu`, `WT_GesPu` and `WT_BesPu` are computed by the model now and can no longer
be set: remove them. The low-voltage transformer is declared instead as `WT_RLvTrPu`, `WT_XLvTrPu`,
`WT_GLvTrPu` and `WT_BLvTrPu`. `WT_ConverterLVControl` has lost its default value and has to be
given one.

#### IEC wind power plants of 2020: a lead-lag per communication

The plant controller of `IECWPP4ACurrentSource2020` and `IECWPP4BCurrentSource2020` delays each of
its three communications — the measurements, the setpoints it sends to the turbines and the
external references — through a lead-lag of its own. `WPP_tLead` and `WPP_tLag` are gone, replaced
by `WPP_tLeadM`/`WPP_tLagM`, `WPP_tLeadPD`/`WPP_tLagPD` and `WPP_tLeadRef`/`WPP_tLagRef`, none of
which has a default value. Giving the three pairs the values the old one had leaves the model as it
was, and that is what Dynawo's own migration does: ticket 4237 of `sbin/updateXML`, which has to be
run on its own, with `--tickets 4237` (see below).

In the IEC workbook the six parameters take the place of the two of the `LinearCommunication_2020`
table, in the `Mesures de parc` sheet. A workbook made with the previous template generates a model
Dynawo refuses: copy the table from `workbooks/Producer_IEC.xlsx`, or start again from that
template.

#### WECC workbooks: a new sheet

The WECC template gained a `Protection de tension` sheet, holding the parameters the producer
chooses and the points of its two capability curves, and a row for it in `Général`. The name of the
table file and the flag that says the curves are read from one are not among them: the generator
writes both. What the sheet says about the curves, beside its Commentaire label, heads the table
file as a comment. A workbook made with the previous template has no such sheet, and `excel2inputs`
will generate a model Dynawo refuses: copy the sheet from `workbooks/Producer_WECC.xlsx`, or start
again from that template.

#### What Dynawo's own migration scripts can and cannot do

`<dynawo>/sbin/updateXML` carries the migrations Dynawo applies to input files, and they do not
cover this upgrade on their own:

- asked to migrate from 1.8.0 to 2.0.0, the updater runs only the three migrations numbered
  `2.0.0.x`, the last of which is the ticket 4237 above. The first of them, ticket 4244, stops with
  an `AttributeError` on any WECC or IEC model, so on those the chain never gets that far. Every
  other migration that matters here is numbered `1.8.0.x` and so belongs to 1.8.0;
- the chain that does contain them — `--origin 1.7.0 --version 1.8.0` — stops with a `NameError`
  in the script that adds the protection's parameters (Dynawo issue 4278), before the rest of the
  chain has run;
- none of them writes the capability-curve file, which has to be supplied by hand whichever route
  is taken.

### The magnitudes of `Producer.ini` lose their `_at_PDR` suffix

The magnitudes a producer declares — `p_max_injection`, `p_max_consumption`, `p_min_injection`,
`p_min_consumption`, `u_nom`, `q_max` and `q_min` — no longer carry the `_at_PDR` suffix: each one
holds at the point of the zone it describes, the internal node in zone 1 and the PDR in zone 3. A
`Producer.ini` that still uses the previous names stops the run with an error naming the key.

`dycov migrate_inputs <inputs>` renames them, in a single file or in every INI under a directory.
Only the names change, so values, comments and layout stay as they are, and `--dry-run` reports
what it would rename without writing. Inputs generated from a workbook with `dycov excel2inputs`
already use the new names.

### The revision of the DTR a run validates against

A run validates against a revision of the DTR, named after the date of the edition that carries
it. The `[DTR]` section of the configuration chooses it with `current`, and
`dycov --dtr <YYYYMMDD> <command>` overrides it for one execution; a revision the tool does not
implement stops the run. The report, the summary of the log and every `results.json` state the
revision used. A PCS measured with criteria the user changed in the configuration is marked in the
summary, with the options changed, because its verdict is then not a conformity check.

Two revisions are implemented: `20240215`, the base the catalogue of the tool holds, and
`20260723`, which carries revision 3.6 of article 8.3.3, in force since 04/05/2026. A run that
names none follows `20260723`, so some verdicts differ from those of the previous release:

- the fiche I5 adds a transient impedant three-phase fault, and so does the fiche I16 zone 3;
- the voltage dips of the fiches I6 and I16 zone 3 start at Un;
- the voltage swell of the fiches I7 and I16 zone 3 is run at Q = 0 and from Un, in place of its
  operating points at Qmax and Qmin (in injection and in consumption for a storage unit);
- the reaction time is reported without a verdict;
- at 110 kV and above, a unit that does not store energy is of type D from 30 MW instead of from
  any power.

`dycov --dtr 20240215` measures against the revision of 15/02/2024, with the corrections of the
next section.

### The values of the DTR of 15/02/2024

The revision of 15/02/2024, which carries revision 3.3 of article 8.3.3, is the base of the
catalogue the tool ships: every later revision enters as a delta over it, and
`docs/design/DTR_revisions.md` says how.

Several values did not match that revision, or any other one. They are corrected, so a test that
reads one of them may now give another verdict:

- The voltage profiles of the fiches I6, I7 and I16 zone 3 recover at the instants of the DTR.
  The profile of a dip at HTB2 held 1.15 s where the DTR gives 1.50 s, the dip of a storage unit
  in consumption held 2.15 s, and the dip at HTB3 of a synchronous unit held 1.30 s.
- The two voltage tables of the fiche I16 zone 3 take their levels from the description of the
  test, so the profile a report draws is the profile the simulation applies. They held the levels
  of another technology.
- The reports of the fiche I16 zone 1 state the voltage of the test as Un. Zone 1 has no Udim:
  the DTR fixes the dimensioning voltage at the connection point, which is the point of zone 3.
- The reports of the fiche I16 zone 1 of a storage unit state a negative power for the four tests
  in which Table 1 gives one, so the report and the simulation agree.

The voltage gabarit of a test now follows the category A, B, C or D of the unit, which is what
the DTR says. The tool read it from the connection voltage alone, which gave the right profile
only while the level decided the category. A unit above 75 MW at 63 or 90 kV is type D and used
to take the profile of the types B and C; it now takes the one of its own category. The tool
reads the category from the connection voltage and the maximum power at injection, and the
powers that separate the categories are options of `[GridCode]`, so a revision of the DTR that
moves them changes a value and not the code. One value stays with the voltage level, because
the DTR gives it that way: the clearing time of the fault of the fiches I4, I5 and I16 zone 3.

The time limits of the checks of the fiches are options of `[GridCode]`, as the error
thresholds already were. A limit of `none` makes a check report its value and give no verdict.
A user who has to validate against another revision changes a value in the configuration
instead of waiting for a release.

One value belongs to no revision: the residual voltage of a gabarit of a type D is 1e-3 and not
the 0.00 of the DTR, because not every model converges with a voltage of exactly zero.

### The curves of a unit are named after the nodes of the DTR

Node2 is the converter terminal, between the unit and its transformer, and the controlled node
is the one the control of the converter measures, Node1 or Node2. The curves of a generating
unit take those names:

| Previous name                           | Name now                                 |
| --------------------------------------- | ---------------------------------------- |
| `<unit>_GEN_VoltageInjTerminal`         | `<unit>_GEN_VoltageNode2`                |
| `<unit>_GEN_ActiveCurrentInjTerminal`   | `<unit>_GEN_ActiveCurrentNode2`          |
| `<unit>_GEN_ReactiveCurrentInjTerminal` | `<unit>_GEN_ReactiveCurrentNode2`        |
| `<unit>_GEN_ActivePowerControlledPu`    | `<unit>_GEN_ActivePowerControlledNode`   |
| `<unit>_GEN_ReactivePowerControlledPu`  | `<unit>_GEN_ReactivePowerControlledNode` |

The results, the reports, the dictionaries the tool scaffolds and the example workbooks use the
new names. A dictionary of curves written with the previous ones is still read as it is, and so
is a curve file whose columns carry them.

The keys of the Dynawo dictionaries change the same way. A configuration that lists its own
`[CurvesVariables]` has to list them by their new names — `ActivePowerNode2`,
`ReactivePowerNode2`, `VoltageNode2`, `VoltageNode2Re`, `VoltageNode2Im`, `CurrentNode2Re`,
`CurrentNode2Im`, `ActivePowerControlledNode`, `ReactivePowerControlledNode` — because a name the
dictionaries do not know asks Dynawo for nothing. In the dictionary of a unit model,
`MagnitudeControlledByAVRPu` becomes `VoltageControlledNode`, and the operating point at the PCC
and `PPCLocal` are gone: they belong to the plant controller. The tool wrote that operating point
into the PAR of a unit, where Dynawo ignored it. The storage unit's `VoltageControlledNode` names
`BESS_reecC_UPu`: it named a variable the model does not have.

The IEC wind turbines of zone 1 are now measured at Node2 itself. Their voltage and powers were
read on the grid side of their low-voltage transformer, which is Node1 when that transformer is
inside the unit model (`WT_ConverterLVControl = false`). Their models give no powers at Node2, so
the tool computes them from the voltage and the current there. In the IEC plant models of zone 3
the Node2 curves are still read on the grid side of that transformer.

### The on-site tests of the Fiche F16

`PCS_RTE-F16z3` validates the model of zone 3 against the records of the commissioning tests at
the PDR, the second phase of the validation after the fiche I16. The fiche fixes no test of its
own, so the PCS ships without any, and the producer declares the tests it recorded in an
`F16Description.ini` delivered with the reference curves. The tool leaves a template of that file
among the templates of the user. Only the operating conditions whose records are delivered are
run, with the error thresholds of the fiche (`thr_FT_reftrack_*` in `[GridCode]`), and the
workbook gives the minimum powers of the tests. `docs/tutorials/f16_declaring_recorded_tests.md`
walks through a declaration.

A producer validated against F16 alone delivers its `Zone3/` model: `Zone1/` is required only
when a PCS of zone 1 is validated.

### Running the tool

- `--curves-only`, on `validate` and `performance` with a model, runs the simulations and keeps
  their curves without the checks, the figures or the report.
- Each execution writes its own log, `dycov_run.log`, at the root of its results.
- The working directory of a run is created next to its output directory instead of in the
  current one, so the directory that holds the output has to be writable.
- Dynawo logs at the level of `[Dynawo] log_level`, `WARN` by default and `DEBUG` when DyCoV runs
  in debug, instead of one line per time step.
- The log says how long each test took and how it ended, and each retry of the solver says what
  it changed and why the previous attempt failed.

### The curves of the examples ship with the release

The reference and producer curves of the examples are no longer in the repository: each release
publishes them as its `dycov_examples.zip` asset, which the installer and the image already carry.
A clone of the sources has the examples without their curves, and
`tools/scripts/fetch_example_curves.sh` brings in those of the release the clone descends from.

### Fixed

- The maximum power declared for an IEC plant is checked against its model's, as for WECC, and a
  declaration above it now stops the run: the check read a parameter IEC models lack (#649).
- IEC plants whose controller measures at the PCC start in steady state, and no longer from a
  phase of 0 there whatever the operating point (#649).
- The tool computes the starting point of a tap changer with the ratio its starting tap gives,
  the one Dynawo simulates, and no longer with the one the PAR states, which Dynawo ignores (#649).
- Islanding simulations run again: the `DYNModelOmegaRef` connectors are written with the names
  Dynawo 2.0.0 expects (#606).
- The WECC examples simulate every test again when several run at once: their plant controller no
  longer has a voltage deadband, on whose edge the WECCVoltageSource4 swell kept the solver (#626).
- The IEC 2020 examples simulate again: their plant controller declares the three lead-lag pairs
  Dynawo 2.0.0 asks for (#633).
- The report of a setpoint tracking test whose event lasts gives the thresholds of the event
  window under its own column, and those of the window after it under theirs (#657).
