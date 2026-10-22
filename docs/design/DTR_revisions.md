# How a revision of the DTR enters the tool

DyCoV ships the whole catalogue of one revision of the DTR, and the differences of every other
one. A validation follows the revision that applies to the installation: the one in force at the
date of its PTF, the *Proposition Technique et Financière*, because the specifications of the
installation were written with that revision. A validation must also give the same verdict years
later.

So the tool needs every revision an installation may carry. This document says how a revision
enters the tool, and what the shipped files already give it.

## The two phases of the work

**The base.** The tool holds the whole catalogue of one revision, the DTR of 15/02/2024, and says
so. Every value that revision fixes is an option, and the mechanisms a delta needs are in the
tool, used by nothing. This is where the tool is now.

**The revisions.** The loader of a delta, and one delta for each later revision. Nothing of it
is in the tool yet. The issues #549, #550, #551 and #552 hold that work, and this document is
their design.

## The base and the deltas

The **base** is the first revision the tool implemented, the DTR of 2024-02-15, and it holds
the whole catalogue: every PCS, with its values and its reports. The base does not move: a
revision that arrives is added, and nothing that already works is rewritten.

A **delta** is one other revision. It holds the options and the lists that revision writes
differently from the one before it, and nothing else. A delta reads as the DTR announces its
own changes, and a reader of one sees what that revision changed.

A run names one revision. The tool reads the base, applies every delta from the base up to that
revision in date order, and runs. Nothing else in the tool knows which revision it works on.

## The name of a revision

A revision is named by the date of the full DTR, as `YYYY-MM-DD`. The articles inside carry
their own version numbers, and several editions may carry the same version of an article. The
date is the name a user reads on the document RTE publishes, and it orders the revisions.

`Summary_data_from_the_DTR.md` holds, for each revision, the version of each article the values
come from.

## How a run selects one

The issue #551 holds this part.

* The `[DTR]` section declares `current`, the revision a run uses, and `available`, the
  revisions the tool implements. The configuration the tool ships gives `current` the newest
  revision, so a run that says nothing validates against the norm in force.
* `--dtr <date>` overrides `current` for one execution, so the same producer runs against two
  revisions one after the other. The curves do not change; only the criteria do.
* A run that asks for a revision that is not in `available` stops with an error. The tool never
  falls back to another norm in silence.

## Where a delta lives

A delta of a PCS sits beside the description of that PCS, named after the date of the full DTR.
A PCS a revision does not touch has no file at all, and its revision layer is then empty rather
than whatever the previous PCS loaded. The issue #550 holds this part.

```
<PCS dir>/PCSDescription.ini                  the base, which holds the whole description
<PCS dir>/PCSDescription.<YYYY-MM-DD>.ini     what that revision writes differently
<PCS dir>/<benchmark>/Table*.<YYYY-MM-DD>.txt the voltage tables that revision changes
src/dycov/configuration/revision.<YYYY-MM-DD>.ini   the sections that belong to no PCS
```

A file holds what changes, and not the whole description, because the base answers for the rest.
The PCS configuration splits into two parsers, the base and the revision, so that the precedence
is structural and not a consequence of the order the files were read in.

## What the tool already gives a delta

Three mechanisms are in the tool, and no shipped PCS uses any of them. They are there so that a
delta carries data alone:

* **A key may name the category of the unit.** `find_option` reads `<key>_<category>` first,
  `<key>_<level>` next, and `<key>` last. `get_generator_category` gives the category from the
  connection voltage and the maximum power at injection, with the powers that separate A from B,
  B from C and C from D as options of `[GridCode]`. The DTR of 15/02/2024 selects every gabarit
  by the voltage level, so it writes no key with a category.
* **A limit may be withdrawn.** `get_threshold` reads `none` as "no limit", and the check then
  reports its value and gives no verdict. The report drops the comparison from the row of that
  check. A revision that keeps an indicator and withdraws its criterion writes one word.
* **A value of the DTR is an option.** The gabarits, the operating points, the events, the lists
  of benchmarks and of operating conditions, the time limits and the error thresholds are all
  read from the configuration.

## What the tool has to do next

`Config` already holds the layer, between the configuration of the user and the shipped PCS
description. `load_pcs_config` takes a `dtr_pcs_path` and nobody passes one yet. The work is:

1. Read `[DTR]` and `--dtr`, and stop when the revision is not among the available ones
   (#551).
2. Give `load_pcs_config` the delta files of the PCS in preparation, when the revision has them.
   `configparser.read` takes several paths and the last one wins, so a chain of deltas needs no
   other mechanism (#550).
3. Read the `revision.<date>.ini` files into a layer of their own, below the shipped PCS
   description and above the default configuration. A PCS says more than a revision, and a
   revision says more than a default (#550).
4. Resolve the path of a voltage table and of a report template through the revision first, and
   through the shipped file when the revision gives none (#550).
5. Write the revision in the report and in `results.json`, because a verdict without its
   revision cannot be read. Mark a PCS whose criteria the user configuration overrode as invalid
   for certification, and name the keys that were changed: a report measured with altered
   criteria must not read as a conformity check (#552).

The order of the layers, from the highest precedence to the lowest, is then:

1. the PCS description of the user,
2. the configuration of the user,
3. the PCS description of the selected revision,
4. the PCS description shipped with the tool,
5. the `revision.ini` of the selected revision,
6. the default configuration.

The configuration of the user wins over a revision. A user who changes a value takes the
responsibility for it, as with every other option.

## What a delta may carry

Every value of the DTR that the tool reads is an option, so a delta reaches all of them:

* the values of a test: the gabarit, the operating point, the event, in the PCS description;
* the lists of benchmarks and of operating conditions of a PCS, in the same file;
* the time limits of the checks and the thresholds of the errors, in `[GridCode]`;
* the levels of the voltage dip and of the swell, which the voltage tables read as placeholders;
* the reports, which state the conditions of the test they report.

## The reports of a revision

A report template states the conditions of the test it reports, so a revision that changes a test
changes its template. The `reports/` subtree of a delta mirrors `src/dycov/templates/reports/`.
The tool reads the template of the selected revision when it exists, and the shipped one when it
does not. These are the cases.

**A test changes its conditions.** The delta carries the template of that test. A revision that
renames a fiche or moves it in the report carries, in the description of the PCS, the `id` and the
`report_name` of the section as well.

**A test appears.** The delta carries three things: the description of the test, its name in the
list of operating conditions, and its template, which no other revision has.

**A test disappears.** The delta takes its name out of the list of operating conditions. Its
template stays in the shipped tree, and nothing reads it. No file is deleted.

**A fiche appears, or a fiche is withdrawn.** The shipped catalogue holds every fiche the tool
implements, each with the revision that introduced it and the one that withdrew it. Outside those
dates the PCS is not loaded and the report has no section for it, and the summary and
`results.json` give it as not defined in that revision.

A description overlays key by key, so a delta of a description holds the keys that change and
nothing else. A template does not: it is text, and a delta that changes one sentence of a report
carries the whole file, with everything the revision did not touch.

The way out is to take the values of the DTR out of the text. A template states the conditions of
its test — the operating point, the stages of the gabarit, the clearing time — with the numbers
written in the prose. Those numbers are already options, and the report is built with a template
engine, so the template can read them as it reads every other value it prints. A revision then
changes the data alone, and it needs a template only when the test says something new. It also
ends a class of defect of its own: a report that states one value while the simulation uses
another.

One file does not follow this rule yet. `figures.json` lists the figures of every PCS, so that the
report finds a file for a figure the run did not produce. It is one shipped file: a revision that
adds a test adds figures the file does not list, and the report of a failed test then misses a
file. Two ways out: give it the treatment of the templates, one file per revision, or build it
from the descriptions and the templates, which already say which tests exist and which figures
they draw. The second one ends the duplication.

## What a delta cannot do

A delta adds a value and replaces a value. It never deletes one, because a layer below always
answers. Two rules follow.

**A delta that changes how a value is selected rewrites the keys of the old selection too.** The
tool reads a key with the suffix of the category first, the suffix of the voltage level next, and
the plain key last. A revision that selects the dip gabarit by the voltage level writes every
`u_fault_HTB<n>`, and one that selects it by the category writes `u_fault_D` and gives the level
keys the value of the types B and C.

**A delta carries data, not code.** A revision that needs a mechanism the tool does not have is
not a delta: it is work on the tool.

## What belongs to no revision

The residual voltage of a gabarit of a type D is 0.00 in the DTR, and 1e-3 in the tool. It is a
guard: not every model converges with a voltage of exactly zero. It holds for every revision, so
no delta takes it away, and the description of each PCS that writes it says so.

## What stays in the code

A value that names a check stays in the code: the 5 % and the 10 % of `time_5P` and `time_10P`,
and the 1 Hz of `freq_1`. A revision that changes one of them gives another check, with another
name, and the lists of `[Performance-Validations]` say which checks a PCS runs.

The four voltage tables of `PCS_RTE-F16z3` also write their levels. A declared test states the
instants of its record, and the levels come from the profile of the DTR. To give them a delta,
the shipped `F16Description.ini` has to declare them, and every producer has to add them to the
file it already has. That migration belongs to the day the deltas arrive.

## Which revisions the tool needs

RTE asks for every revision from the first one the tool implemented, which is article 8.3.3 v3.3,
of 2024-02-15. The reason is the PTF: a client signs it months or years before it sends the
fiches, so in the coming months most projects carry a PTF dated before 2026-05-04, the day
article 8.3.3 v3.6 took force.

So the tool ships the base of 2024-02-15 and carries three deltas:

| Revision | Article 8.3.3 | For a PTF signed |
|---|---|---|
| 2024-02-15, the base | 3.3 | from 15/02/2024 to 31/07/2025 |
| 2025-08-01 | 3.4 | from 01/08/2025 to 12/10/2025 |
| 2025-10-13 | 3.5 | from 13/10/2025 to 03/05/2026 |
| 2026-05-04 | 3.6 | from 04/05/2026 |

The edition of the DTR of 2026-10-08, the newest one, still carries article 8.3.3 v3.6, so the
delta of 2026-05-04 covers every PTF from that day.

The tool needs no revision before 2024-02-15. The fiche I16 does not exist before that date, and
no PTF in hand carries an earlier one. So the base does not move backwards: every revision that
arrives is added in front of it, and nothing that already works is measured again.

## The deltas to write

The second phase writes the loader and then the three deltas, one branch each, oldest first,
because every delta describes what its revision changed over the one before it. The issue #616
holds what the revisions of 2025 changed, fiche by fiche. The tables below hold what is measured
so far, which covers the fiches the tool implements and not the fiches those revisions add.

The delta of 2025-08-01 writes:

| What | Where |
|---|---|
| The category of a unit selects the dip gabarit | the `category_*` keys in `revision.ini`, and the keys of the gabarit of every dip |

The delta of 2025-10-13 writes:

| What | Where |
|---|---|
| The fiches I6 and I7 start at Un | `pdr_U` of the dip and of the swell |
| The fiche I7 gives one operating point, at Q = 0 | the list of operating conditions, one description, one report |
| The fiche I5 adds the impedant fault | the list of operating conditions, one description, one report |
| The reaction time carries no verdict | `thr_reaction_time` in `revision.ini` |
| The category of a storage unit drops the installed power | `category_storage_thresholds_high_voltage` |

The delta of 2026-05-04 is not compared yet, beyond the five points above, which it keeps as
2025-10-13 writes them.

Two fiches of those revisions are not in the tool at all: I17 and F17, on the damping of
oscillations, which 3.5 adds. A fiche that appears is not a delta of a value; it is a PCS of its
own, and #616 names it.

`~/dycov_632_dtr34`, `~/dycov_632_dtr35` and `~/dycov_632_dtr36` hold the measurements of those
values, test by test.
