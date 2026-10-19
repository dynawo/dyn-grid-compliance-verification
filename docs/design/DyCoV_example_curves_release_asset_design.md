## DyCoV Example Curves as a Release Asset — Design

### 1. Purpose

The curves of the examples stop being versioned and become an asset of the GitHub release, built
and published the same way the Dynawo build already is. The repository stops growing with every
regeneration; nothing an end user installs or runs changes, and the curves keep the paths they
have today.

The pattern is the one `installers/prepare_release.sh` already applies to `Dynawo_omc_v1.8.0.zip`:
the release script zips it, writes its SHA-256 into `installers/linux_install.sh`, and the
installer downloads it, checks the sum and unzips it. This design reuses that mechanism; it does
not introduce another one.

---

### 2. Scope

**In scope:** the `*.csv` curves under the example trees, the release and installation machinery
that has to carry them, the regeneration command that produces them, and the development surface
that consumes them.

**Out of scope:** the layout of the examples, which does not move; the content of the curves,
which is what `tools/scripts/regenerate_curves.sh` already decides; the 6.17 GB the history
already holds, which only leaves the pack with a rewrite that RTE performs; and
`docs/GFM_envelopes_curves/` (263 files, 42 MB), which has the same problem on a smaller scale and
is a separate decision.

---

### 3. What leaves the index

**The directories, whole.** All 1,042 tracked files under them leave, not only the curves. The
weight is of course in the curves:

| | files | bytes |
| :--- | ---: | ---: |
| `*.csv` | 474 | 453,606,509 |
| `*.dict` | 538 | 698,309 |
| `*.ini` | 30 | 96,485 |

But the rest goes too, because a repository that holds half of a delivery holds something
incomplete, and because every one of those files can be written from what stays:

* **The 21 indexes** (`CurvesFiles.ini`) are written by `dycov anonymize`, like the curves.
* **The 538 dictionaries** come from the same run. The 64 that have no curve
  (`PCS_RTE-I16z1.SetPointStep.Voltage`, `PCS_RTE-I16z3.QSetPointStep.Inc10/Dec20` and the BESS
  `Consumption`/`Injection` variants) stop existing, and nothing changes for it: a test whose
  curve is not delivered reports the same verdict with or without its dictionary — except under
  Fiche F16, where the dictionary is what makes the test run at all (§12).
* **The 7 producer declarations** — the `Producer.ini` of each curve directory — are written from
  the model whose curves the directory ships (§12).
* **The 2 F16 declarations** are written too, and for every Model example rather than the two
  that happened to have one (§12).

**The rule**, then, is the directories themselves:

```
# The curve directories of the examples ship as an asset of the release, not as repository
# content: tools/scripts/regenerate_curves.sh writes them whole — curves, dictionaries and the
# declarations that go with them — and they are fetched or regenerated, never committed.
examples/**/ReferenceCurves/
examples/**/ProducerCurves/
examples/.curves-release
```

Ignoring does not untrack: `git rm -r --cached` over those 1,042 files goes **in the same commit**
as the rules, or they stay versioned. The directories leave the working tree as well, so the ones
that were there are worth keeping aside first: the regeneration is what proves the rule, and what
it produces is compared against them.

---

### 4. The asset

**`dycov_examples.zip`** — the whole `examples/` tree with its curves. 453.6 MB of CSV compress to
53 MB, so each release publishes about the same volume a regeneration used to add to the pack,
once and outside git.

It is built in two stages, because neither alone is right:

```
git archive HEAD examples | tar -x -C "$STAGING"     # the tracked tree, nothing ignored
cp the working-tree *.csv over "$STAGING/examples"   # the curves, which git no longer carries
zip -qr "$OUTPUT_DIR/dycov_examples.zip" examples    # from "$STAGING"
```

`git archive` is what keeps a local `Results*/` out of the asset — the reason `build.sh` already
uses it — and the overlay is what puts the curves back in. Neither step can be dropped.

---

### 5. `installers/prepare_release.sh`

**Step 0 — the `STALE_EXAMPLES` guard is rewritten.** As it stands it aborts the release when
*any* git-ignored file exists under `examples/`, which the curves now always are. It becomes two
checks:

* no ignored path under `examples/` other than the curve `*.csv` and `.curves-release` (§9) — a
  stale `Results*/` still stops the release;
* every one of the 21 curve directories holds at least one `.csv` — a release never ships an
  `examples/` whose curves were never fetched or regenerated.

**Step 1b — new, between the Dynawo zip and the `linux_install.sh` patch.** Builds
`dycov_examples.zip` as in §4 and computes its SHA-256. It has to precede Step 2, which writes
that sum into the installer, and Step 4, which builds the image from the same working tree.

**Step 2 — one more substitution.** Beside `TARGET_BRANCH` and `DYNAWO_SHA256SUM`, the generated
`linux_install.sh` gets `EXAMPLES_SHA256SUM`.

**Step 6 and the summary.** `dycov_examples.zip` is one more file to upload; the release goes from
eight artifacts to nine.

`installers/RELEASING.md` follows: the artifact table, the post-release checklist, and §1, where
the regeneration is already described as the step before the tag — which is also what guarantees
the curves are on disk when Step 1b runs.

---

### 6. The image

`installers/docker/build.sh` stages the examples with `git archive HEAD examples`, which would now
produce an `examples/` without curves. It gains the same overlay as §4, right after the archive:
the curves come from the working tree, which at release time is the tagged tree with the
regenerated curves.

`Dockerfile` does not change. It copies `./examples` from the build context and the context is
assembled by `build.sh`.

---

### 7. `installers/linux_install.sh`

Today Step 5 does `cp -a "$TMP_LOCAL_REPO"/examples "$INSTALL_DIR"/`. From a clone of the tag that
copies the tree without curves, so it is replaced by the asset, following `Dynawo_omc_v1.8.0.zip`
line for line:

```bash
EXAMPLES_ZIP_FILE="dycov_examples.zip"
EXAMPLES_SHA256SUM="<written by prepare_release.sh>"
EXAMPLES_ZIP_URL="https://github.com/.../releases/download/$TARGET_BRANCH/$EXAMPLES_ZIP_FILE"
```

`curl -O -L --fail`, `sha256sum` against `EXAMPLES_SHA256SUM`, `unzip` into `$INSTALL_DIR`,
remove the zip — the same four steps as the Dynawo build, from the same release.

Which release that is had to be settled first. The installer took its version from
`TARGET_BRANCH`, defaulting to `master`, and built both asset URLs from it; but a branch has no
release and no assets, and there is no `master` release, so that default answered 404 and had
done so unnoticed — the examples asset would have inherited exactly that. It now resolves a
release: `--release` names one, the default is the latest, and `--branch` survives as what it
can honestly be, the sources of someone testing something unreleased, with the assets still
coming from a release. `--examples-zip`, like `-z` for Dynawo, takes one from disk instead.

A missing or corrupt asset aborts the installation. An `examples/` without curves is worse than no
installation: the user would find out when a validation reports `WithoutReferenceCurves` on every
test.

The three source modes (`--source-zip`, `--url`, clone) are unaffected: the curves come from the
release either way, not from the source the installer was given.

---

### 8. Packaging

Nothing to do. There is no `MANIFEST.in`, and the wheel never carried the examples:
`[tool.setuptools.package-data]` only reaches `src/dycov`. `uv build --wheel`, which is what
`build.sh` installs into the image, is unaffected.

`git archive` is used in two places (`build.sh`, and now the asset) and in both it is the right
tool for what it is asked to do — the tracked tree — with the curves overlaid separately.

---

### 9. The developer's clone

A fresh clone has the example trees with their dictionaries and no curves. Two ways to fill them:

**`tools/scripts/fetch_example_curves.sh`** — new. Downloads `dycov_examples.zip` from the release
this checkout descends from (`--release` names another, `master` when it descends from none),
checks the archive and unpacks only the `*.csv` over `examples/`. Seconds, and no Dynawo — **from
the first release that publishes the asset onwards**. No release has one today, so between the
merge and that release regeneration is the only route, and the script says exactly that when the
release it is pointed at carries no `dycov_examples.zip`, instead of failing on a 404.

**`tools/scripts/regenerate_curves.sh`** — what a release does. Hours, and a Dynawo launcher.

Nothing that needs curves may run without saying which of the two to use:

* `tests_integration/conftest.py` gains a session fixture that checks the curve directories of the
  examples the tests name and fails with the command to run. These tests assert an exact list of
  verdicts per test; without the guard a clone with no curves fails on a verdict list, not on the
  reason.
* `tools/scripts/test_tool.sh` makes the same check before its first run — except when
  `regenerate_curves.sh` calls it, which is the one run that exists to produce the curves and
  reads no verdict. That is what its `--without-curves` says.

**They also stop asserting verdicts.** A verdict is a statement about a particular set of curves.
While the curves are versioned, the data and the expected verdicts travel in the same commit and
cannot disagree; once the curves come from a release, a developer can hold the asset of one
release in a checkout that has moved past it, and a hard-coded verdict list then fails for a
reason that has nothing to do with the change under test. A test over real inputs is worth
keeping, so what it asserts becomes what a run yields whatever curves it was given
(`tests_integration/curves_invariants.py`):

* **which tests ran** — the PCS descriptions and the producer decide it, and both are in the
  commit;
* **that every one reached a verdict** — an invalid test, a simulation that failed or timed out
  is a failure however the curves read;
* **which tests are not applicable** — the control mode of the model decides that and nothing
  else, so the set is fixed until the model changes;
* **that every delivered curve was verified** — each CSV of a producer directory is one test, so
  the tests that reached a verdict are exactly the curves that arrived, less the ones the model
  cannot do.

`Compliant` versus `NonCompliant` is the one thing the curves decide, and the one thing these
tests no longer say. Reading them needs the test identities, which `Validation.validate` reduced
to a verdict column: it now keeps its `Summary` list and `get_summary()` returns it, which is also
what `execute_tool` maps to produce the same list as before.

What this change does owe them is knowing which curves they ran on. The curves on disk carry where
they came from, in an ignored `examples/.curves-release`: `fetch_example_curves.sh` writes the
release it fetched, `regenerate_curves.sh` the commit it regenerated from. The guard above compares
it against `git describe --tags --abbrev=0` and says which two it is holding when they differ;
curves regenerated locally are a legitimate answer, so that case is reported and not refused. It
needs no tracked file, and `prepare_release.sh` writes nothing into a tree that is already tagged.

**Three test files move to `tests_integration/`.** `pytest.ini` has `testpaths = tests`, so what
lives under `tests/` is what the CI runs on every pull request, and a test that needs the curve
directories cannot stay there once they are not in the clone:

| File | Reads |
| :--- | :--- |
| `tests/dycov/validate/test_validate_model.py` | `Model/ProducerCurves/{PPM,BESS}` and two `ReferenceCurves` trees |
| `tests/dycov/validate/test_validate_performance.py` | `Performance/ProducerCurves/{SM,PPM,BESS}` |
| `tests/dycov/sanity_checks/test_model_sanity_checks.py` | the `ReferenceCurves` directory of every Model example |

The last one needs no curve at all — `ModelProducer` checks the directory, not what is in it — but
it does need the directory, which is enough to take it out of the unit suite.

Everything else under `tests/` reads the `Dynawo/` model definitions and one workbook, so the CI
keeps running and stops checking out 437 MB of curves on every job.

Both files that move run **without Dynawo** — they validate curves against curves, which is why
they were unit tests in the first place. `tests_integration/conftest.py` has an autouse fixture
that raises when no Dynawo build is found under `/opt`, so it has to stop being fatal for them, or
they error instead of running on a machine that has the curves and no Dynawo.

This costs the CI its only coverage of the curve-driven validation path, which no longer has data
to run on. Recovering it means fetching the asset in the CI job, and that is a decision for when a
release publishes one.

**What the documentation has to say.** A fresh clone that does not run one of the two commands has
example trees that look complete and are not, so the step belongs wherever a developer is told to
clone or to run an example:

| Document | What changes |
| :--- | :--- |
| `docs/developer/setup.md` | §4 (cloning): the fetch replaces the merge-driver registration. §9, step 4 ("run DyCoV commands against one of the bundled examples"): it needs the curves. |
| `docs/manual_dev/source/development/installation.rst` | The same two places, which mirror `setup.md`. |
| `docs/manual_dev/source/index.rst` | The `examples` entry says the curves are not in the repository; the `scripts` entry goes (§11). |
| `docs/developer/project_structure.md` | The `examples/` section says the same; `scripts/` leaves the tree, the prose and the table at the end. |
| `CONTRIBUTING.md` | §7, "Add or update examples under `examples/`": a new or changed example ships its curves through the release, not through the commit. |
| `tools/scripts/README.md` | `fetch_example_curves.sh` joins the table, and the regeneration section says what the curves become. |

**The user-facing documentation does not change.** `docs/installation/`, `docs/tutorials/` and
`docs/manual/` describe an installation that has the curves — the installer unpacks them and the
image carries them — so the step would be wrong there, not merely unnecessary.

---

### 10. The CLI needs no guard

`dycov validate` and `dycov performance` are not touched. `curves/manager.py` already resolves a
missing reference curve into `CurvesAvailability.NO_REFERENCE` and the test into
`Compliance.WithoutReferenceCurves`, reported per test. That is the correct answer for the case the
code exists to serve — a producer whose recordings do not cover every test — and it does not become
wrong because the curves of the examples now arrive by another route. Making the CLI refuse to run
without curves would break a real use case to report a development accident.

The guard belongs where the accident happens: the development surface of §9.

---

### 11. What this removes

`.gitattributes` holds one line, `examples/**/*.csv merge=csv-ref`, and `scripts/` holds only the
driver it names (`git-merge-csv-ref`, `setup-git-hooks.sh`). Both exist because versioned curves
conflict on merge. Once the curves are not versioned they have nothing to do, so the line, the
directory, the "register it once per clone" step and the two descriptions of `scripts/` as a
top-level directory — `docs/manual_dev/source/index.rst` and `docs/developer/project_structure.md`
— go with this change.

---

### 12. The regeneration writes the directories, whole

Once the curve directories are not in the repository, the command that writes them has to write
everything they hold, and `regenerate_curves.sh` wrote about half: the reference curves of the
Model examples and the producer curves of two families. It becomes four stages, each a script of
its own that can be run alone, with that command as their launcher. The order is not a matter of
taste.

**1 — `regenerate_f16.sh`: the declared tests of Fiche F16.** The fiche fixes no test, so a
producer declares the ones it recorded; the examples declare an invented one, the same for all of
them: a setpoint step of active power and one of voltage, at each power level the producer
records. Two examples had that declaration by hand; now every Model example gets it, written from
`example_inputs.ini`.

It has to be first, and this is the one piece of the design that is not obvious: a declared F16
test is run **only where its record already exists** (`recorded_tests_only`, which `Benchmark`
resolves through the reference `.dict`). So the record is announced before the run — a dictionary
saying when the event happens and nothing else — the run then simulates the test, and the
anonymized result replaces the announcement with the real record. Measured on one example: the six
declared tests run, report `WithoutReferenceCurves`, and leave their six `curves_calculated.csv`.

**2 — `regenerate_producer_inis.sh`: the producer each curve directory declares.** A delivery of
curves has no model, so it states its own magnitudes. Each declaration is written from the model
whose curves the directory ships — the pair is in `models.sh` — carrying the magnitudes of the
DTR and the kind of generator, dropping the parameters of the Dynawo model, and taking from
`example_inputs.ini` the one thing no model states, the apparent power of each zone. Nothing is
deduced: both are data files.

Three of the seven were stale, which is what generating them fixes and what nothing would
otherwise have caught: `Model/ProducerCurves/BESS/Zone3` and `Performance/ProducerCurves/BESS`
declared 75 MW and ±40 MVAr against a model that has moved to 40 and ±13, and the two PPM ones
omitted the `p_min_injection = 7.5` their model declares and the F16 `Pmin` level uses.

**3 — `regenerate_reference_curves.sh`: the reference curves.** What the command did before, with
the coverage guard it already had — the tests the PCS of the tool declare, plus the ones the
example declares for itself, which is now where F16 is counted.

**4 — `regenerate_producer_curves.sh`: the curves delivered instead of a model.** The Model ones
are the curves of a Model example, so they come from the run of stage 3; the Performance ones,
the 30 the command never produced, are a run of their own in performance mode, of the model each
family declares.

**And it has to run unattended.** `confirm_replacement` asked for a terminal before replacing a
previous run, so the command gains `-y/--yes`; and `test_tool.sh` wrote its progress to
`/dev/tty`, which under `errexit` killed any run without a console — found by running it, after
sixteen validations had completed and before a single curve was written.
---

### 13. Order of the change

One pull request, and within it the order matters:

1. `.gitignore` rules and `git rm --cached` of the 474 curves — **the same commit**, or the files
   stay tracked.
2. The release and installation machinery of §§4–7, so that the first release after the change
   publishes and consumes the asset.
3. The development surface of §9 — the fetch script, the guards, the two test files that move —
   and the removals of §11.
4. `regenerate_curves.sh` completed (§12), which the first release after the change depends on.

Until a release carries the asset, a developer's clone has no curves and no asset to fetch: §12
and the fetch script of §9 have to be usable before the branch is useful to anyone, and the first
release after the merge is what makes the installer path real.

**What the merge does to a checkout that has the curves.** `git rm --cached` leaves them on disk
where the commit is made, but it records an ordinary deletion, so every other checkout loses its
474 curves on the first `pull` that brings the commit in. Only the first one: from then on they
are ignored, and a restored curve survives any later checkout with a clean `git status`. Whoever
pulls that merge before a release publishes the asset should copy the curves aside first and put
them back afterwards, because regeneration is the only other way to get them at that point.

---

### 14. What this does not do

The 6.17 GB the pack already holds stay there. They only leave with a history rewrite, which needs
administrator rights on the repository and is RTE's decision; this design is what stops the growth
and is complete without it.

Nor does it touch the integration tests that simulate. `tests_integration/test_validate_model.py`
compares a Dynawo run against the reference curves of an example, so its verdict lists have the
same problem the curve-driven ones had and the same answer applies; `test_performance.py` reads no
reference, so its verdicts depend on the model and the Dynawo build the release pins, not on the
curves. Changing the first means running it, and the Dynawo build its fixture picks is the newest
under `/opt`, which here is a 2.0 that DyCoV does not yet work with.
