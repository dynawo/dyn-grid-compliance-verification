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

The **base** is the first revision the tool implemented, the DTR of `20240215`, and it holds
the whole catalogue: every PCS, with its values and its reports. The base does not move: a
revision that arrives is added, and nothing that already works is rewritten.

A **delta** is one other revision. It holds the options and the lists that revision writes
differently **from the base**, and nothing else. It is not written against the revision before
it, so a reader of one delta sees the whole distance from the base to that revision.

A run names one revision. The tool reads the base, applies the delta of that revision, and runs.
It reads one delta and never a chain. Nothing else in the tool knows which revision it works on.

Two things follow. A delta stands on its own, so the deltas may be written in any order, and by
different people. And a value that two revisions change carries its own value in each delta,
which is a repetition the tool accepts in exchange for a delta that can be read alone.

## The name of a revision

A revision is named after the edition of the DTR that carries it, as `YYYYMMDD`: the date
RTE prints on the document it publishes. The articles inside carry their own version numbers,
and several editions may carry the same version of an article.

That name is not the day the article takes force, and the two may be months apart. RTE publishes
an article on its own first, and consolidates it into a full edition later. Article 8.3.3 v3.6
takes force on 04/05/2026, and the first full edition that carries it is `20260723`: RTE
published no full DTR between 13/01/2026 and 23/07/2026. The three older revisions the tool
carries do coincide, because their edition came out the same day as their article.

So a user who holds a PTF reads the table of *Which revisions the tool needs*: it gives, for each
revision, the dates of the PTF it answers for.

`Summary_data_from_the_DTR.md` holds, for each revision, the version of each article the values
come from.

## How a run selects one

The issue #551 holds this part.

* The `[DTR]` section declares `current`, the revision a run uses, and `available`, the
  revisions the tool implements. The configuration the tool ships gives `current` the newest
  revision, so a run that says nothing validates against the norm in force.
* `--dtr <YYYYMMDD>` overrides `current` for one execution, so the same producer runs against two
  revisions one after the other. The curves of a test both revisions share do not change, only
  its criteria do; a test one of them adds or changes, such as those of the Fiche I16.2 of a
  storage installation of type C or D under the revision `20260723`, needs reference curves of
  its own.
* A run that asks for a revision that is not in `available` stops with an error. The tool never
  falls back to another norm in silence.

## Where a delta lives

A revision keeps its whole delta in one directory of its own, which **mirrors**
`src/dycov/templates/`. A reader of that directory sees everything the revision changed, and
nothing else. The issue #550 holds this part.

```
src/dycov/templates/PCS/<kind>/<PCS>/...                 the base, the whole catalogue
src/dycov/templates/reports/<kind>/<PCS>/...             the base, the whole report

src/dycov/templates/revisions/<YYYYMMDD>/
    PCS/<kind>/<PCS>/PCSDescription.ini                  what that revision writes differently
    PCS/<kind>/<PCS>/Type<categories>.ini                its version of the fiche for some
                                                         categories of unit, if it splits it
    PCS/<kind>/*aliases*.ini                             the aliases its versions inherit
    PCS/<kind>/<PCS>/<benchmark>/Table*.txt              the voltage tables it changes
    reports/<kind>/<PCS>/report.*.tex                    the templates it changes or adds
    revision_art_5_1_1.ini                               what belongs to no PCS,
    revision_art_8_3_3.ini                               one file per article
```

The mirror is the whole rule: the tool takes any path under `templates/` and inserts
`revisions/<YYYYMMDD>` after it, so a subtree added later needs no new code. A file the base does
not have is one the revision adds: a version of a fiche by category, the aliases it inherits, a
template of a test it adds. The files that belong to no directory of the base are the
`revision_art_*.ini`, which hold the sections of a revision that belong to no PCS, such as the
thresholds of `[GridCode]`. There is one per article of the DTR the revision changes, so that a
reader sees which article moved: the categories of a unit come from the article 5.1.1, and the
criteria of a fiche from the article 8.3.3.

A file holds what changes, and not the whole description, because the base answers for the rest.
The PCS configuration splits into two parsers, the base and the revision, so that the precedence
is structural and not a consequence of the order the files were read in. A file the revision does
write replaces the shipped one of the same name, because the delta is copied after it.

**A fiche a revision adds** has no shipped description at all: its directory exists only under
the revision, and the delta layer then holds its whole description. The tool looks for the PCS
of a run in both trees, so such a fiche is found, loaded and simulated like any other.

**A fiche a revision withdraws** keeps its shipped description, and the delta writes `none` in
place of its list of benchmarks. A PCS that declares no benchmark is skipped, which is the path
a declared-tests fiche already takes. The word is needed because an empty value says nothing: a
layer that writes one leaves the layer below to answer. The same word withdraws one test of a
fiche, in the list of its operating conditions.

**A fiche a revision splits by category** keeps, for the categories the revision does not single
out, the description the revision gives the PCS (its delta, or the shipped one when the revision
writes no delta of it), and puts a version for the others in the directory of the delta, named
after them: `Type<categories>.ini`. The revision `20260723` splits the Fiche I16 of a storage
installation this way, into the Fiche I16.1 for type B and the Fiche I16.2, `TypeCD.ini`, for
types C and D; zone 1 has no delta, so its version stands alone in that directory. The category
is the one the DTR gives the whole installation, from its Zone 3, and the version is part of what
the revision writes for the PCS: it shares the layer of the delta and is read after it, so it only
carries what the categories it names do differently. A revision that does not split the fiche has
no version, so a run that follows it gives every category the same fiche.

## What the tool already gives a delta

Three mechanisms are in the tool so that a delta carries data alone:

* **A key may name the category of the unit.** `find_option` reads `<key>_<category>` first,
  `<key>_<level>` next, and `<key>` last. `get_generator_category` gives the category from the
  connection voltage and the maximum power at injection, with the powers that separate A from B,
  B from C and C from D as options of `[GridCode]`. The gabarits of the base are written this
  way: the plain key holds what the DTR gives to the types B and C, and the `_D` key what it
  gives to the type D. The level suffix is left for the one value the DTR does give by level,
  the clearing time of the fault of the fiches I4, I5 and I16 zone 3.
* **A limit may be withdrawn.** `get_threshold` reads `none` as "no limit", and the check then
  reports its value and gives no verdict. The report drops the comparison from the row of that
  check. A revision that keeps an indicator and withdraws its criterion writes one word.
* **A value of the DTR is an option.** The gabarits, the operating points, the events, the lists
  of benchmarks and of operating conditions, the time limits and the error thresholds are all
  read from the configuration.

## How a revision reaches a run

The run fixes its revision before anything else reads a value, and every layer then follows.

1. The run reads `[DTR]` and `--dtr`, and stops when the revision is not among the available
   ones (#551).
2. It reads the `revision_art_*.ini` of that revision into a layer of its own, below the
   shipped PCS description and above the default configuration. A PCS says more than a
   revision, and a revision says more than a default.
3. Each PCS in preparation loads, beside its shipped description, the one the revision writes
   for it, into a layer of its own.
4. The files of a PCS are copied into the working directory from the shipped tree first and
   from the delta after it, so a voltage table or a report template the revision rewrites
   replaces the shipped one, and one it adds arrives with no counterpart.

The order of the layers, from the highest precedence to the lowest, is then:

1. the PCS description of the user,
2. the configuration of the user,
3. the delta of the PCS for the selected revision,
4. the PCS description shipped with the tool,
5. the `revision_art_*.ini` of the selected revision,
6. the default configuration.

The configuration of the user wins over a revision. A user who changes a value takes the
responsibility for it, as with every other option.

## What a run says about its revision

A verdict without its revision cannot be read, so the run states it: the header of the report
and of the summary of the log give `DTR revision: <YYYYMMDD>`, and every `results.json` carries
it as `dtr_revision`.

The configuration of the user outranks a revision, so a run may be measured with values the
norm does not give. The tool keeps validating and keeps the verdict those values produce, and
the summary marks the PCS it happened to: a note names every option that was changed and says
the result is not a conformity check. The mark is per PCS, because an override may reach only
one of them.

Which options belong to the norm is not a judgement. They are the ones the shipped description
of the PCS and the delta of the revision define, plus the sections of the default configuration
that hold what the DTR fixes and not how the tool runs: `[GridCode]`, the lists of benchmarks
and of operating conditions, and the lists of validations. A log level or a setting of the
solver marks nothing.

## How a revision redefines the categories

The DTR redefines the categories about as often as it moves a gabarit, and the gabarit follows
the category, so a redefinition changes which profile a unit is tested against. Every revision so
far writes the same table: three powers that separate A from B, B from C and C from D, one set
below a connection voltage and another above it, and a set of its own for a storage unit. That is
the shape of the options, so a redefinition writes values:

| Revision | What it says | What it writes |
|---|---|---|
| `20240215` | every unit above 110 kV is type D, whatever its power | `category_thresholds_high_voltage = 0,0,0` |
| `20250801` | a unit above 110 kV is type D from 30 MW | `category_thresholds_high_voltage = 1,18,30` |
| `20251013` | the category of a storage unit stops reading the installed power | nothing: see below |

One criterion of the base is outside that shape. The table of a storage unit makes a unit of 18 to
50 MW above 110 kV type D when the **installed power of the installation** is above 50 MW, and
type C when it is below. DyCoV reads no installed power, so it gives that unit the type C. The
revision of 13/10/2025 drops the clause and writes type C for every one of them, so the tool
already answers as that revision does, and the base is an approximation in that one band.

A revision that adds a criterion of this kind — one the tool has no input for — is not a delta.
It is work on the tool, and the producer has to declare the new input first.

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

A figure asks for nothing of a revision either. A test that did not run draws no figure, and the
template then takes a placeholder in its place, decided as the report is built. So a revision that
adds a test adds no figure to declare anywhere.

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

Two choices of the tool answer to no revision. They hold whatever revision applies, so no delta
takes them away.

**The residual voltage of a gabarit of a type D** is 0.00 in the DTR, and 1e-3 in the tool. It is
a guard: not every model converges with a voltage of exactly zero. The description of each PCS
that writes it says so.

**The frequency ramp runs in zone 3.** Table 1 of the fiche I16 puts it in zone 1, as the case of
a ramp of +500 mHz at 2 Hz/s on the AC source, and a zone 1 model cannot run it. The tool runs it
as `GridFreqRamp` of `PCS_RTE-I16z3`, with the same magnitude and the same slope, so the curves it
compares are those of the PDR and not those of the node 1. Every revision of the DTR so far
places the test in zone 1, and the tool will keep it in zone 3. The Fiche I16.2 of the revision
`20260723`, for a storage installation of type C or D, has no such ramp, so its version runs it in
neither zone.

## What stays in the code

A value that names a check stays in the code: the 5 % and the 10 % of `time_5P` and `time_10P`,
and the 1 Hz of `freq_1`. A revision that changes one of them gives another check, with another
name, and the lists of `[Performance-Validations]` say which checks a PCS runs.

The four voltage tables of `PCS_RTE-F16z3` also write their levels. A declared test states the
instants of its record, and the levels come from the profile of the DTR. To give them a delta,
the shipped `F16Description.ini` has to declare them, and every producer has to add them to the
file it already has. That migration belongs to the day the deltas arrive.

## Which revisions the tool needs

RTE asks for every revision from the first one the tool implemented, which is article 8.3.3
v3.3, of 15/02/2024. The reason is the PTF: a client signs it months or years before it sends
the fiches, so in the coming months most projects carry a PTF dated before 04/05/2026, the day
article 8.3.3 v3.6 took force.

So the tool ships the base of `20240215` and carries three deltas:

| Revision | Article 8.3.3 | Article 5.1.1 | For a PTF signed |
|---|---|---|---|
| `20240215`, the base | 3.3 | 1.3, from 15/02/2024 | from 15/02/2024 to 31/07/2025 |
| `20250801` | 3.4 | 1.4, from 01/08/2025 | from 01/08/2025 to 12/10/2025 |
| `20251013` | 3.5 | from 13/10/2025, with no version number | from 13/10/2025 to 03/05/2026 |
| `20260723` | 3.6 | the same text as `20251013` | from 04/05/2026 |

The edition of the DTR of `20261008`, the newest one, still carries article 8.3.3 v3.6, so the
delta of `20260723` covers every PTF from 04/05/2026.

The tool needs no revision before `20240215`. The fiche I16 does not exist before that date, and
no PTF in hand carries an earlier one. So the base does not move backwards: every revision that
arrives is added in front of it, and nothing that already works is measured again.

## The tests of a revision

A delta carries data, so what proves it is a test that reads the catalogue and states
what the DTR says. These tests live in `tests/dtr`, apart from the unit tests, and the
CI runs them with the rest.

Every revision brings a file of its own, `test_revision_<YYYYMMDD>.py`. It reads the base
and the revision one after the other, so the table of each test shows the difference
itself: the category a unit takes, the tests a fiche is made of, the value an option
holds. A test selects its revision with the fixture `revision`, and the fixture
`description` then reads the delta of the PCS the test names.

## The deltas to write

The second phase writes the loader and then the three deltas, one branch each. Every delta
describes what its revision changed over the base, so their order does not matter and two of
them may be written at the same time. The issue #616 holds what the revisions of 2025 changed,
fiche by fiche. The tables below hold what is measured so far, which covers the fiches the tool
implements and not the fiches those revisions add.

The delta of `20250801` writes:

| What | Where |
|---|---|
| A unit above 110 kV is type D from 30 MW, not from any power | `category_thresholds_high_voltage = 1,18,30` in its `revision_art_5_1_1.ini` |

The delta of `20251013` writes:

| What | Where |
|---|---|
| The fiches I6 and I7 start at Un | `pdr_U` of the dip and of the swell |
| The fiche I7 gives one operating point, at Q = 0 | the list of operating conditions, one description, one report |
| The fiche I5 adds the impedant fault | the list of operating conditions, one description, one report |
| The reaction time carries no verdict | `thr_reaction_time = none` in `revision_art_8_3_3.ini` |

The delta of `20260723` is not compared yet. It carries the five points above, because its
revision keeps them, and it writes them itself: a delta is measured against the base.

Two fiches of those revisions are not in the tool at all: I17 and F17, on the damping of
oscillations, which 3.5 adds. A fiche that appears is not a delta of a value; it is a PCS of its
own, and #616 names it.

`~/dycov_632_dtr34`, `~/dycov_632_dtr35` and `~/dycov_632_dtr36` hold the measurements of those
values, test by test.
