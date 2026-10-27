# Changelog

What changes between releases for someone who uses DyCoV: the version of Dynawo the release is
built on, and anything a user has to do to their own producer model, workbook or configuration
before the new release will run it. Fixes that need nothing from the user are listed in one line;
the issue each one points at holds the explanation.

## Unreleased

### Built on Dynawo 2.0.0

This release ships and requires Dynawo 2.0.0. The previous one shipped a Dynawo 1.8.0 nightly in
which the voltage ride-through protection described below did not exist. The Dynawo models
themselves changed, so a producer model prepared for the previous release does not load unchanged.

The simplest way through is to update the workbook and regenerate the model with `dycov generate`.
Editing the DYD and the PAR by hand works too, and the three points below are what has to end up in
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

- asked to migrate from 1.8.0 to 2.0.0 the updater reports no patch files at all, because every
  migration that matters here is numbered `1.8.0.x` and so belongs to 1.8.0;
- the chain that does contain them — `--origin 1.7.0 --version 1.8.0` — stops with a `NameError`
  in the script that adds the protection's parameters (Dynawo issue 4278), before the rest of the
  chain has run;
- none of them writes the capability-curve file, which has to be supplied by hand whichever route
  is taken.

### The values of the DTR of 15/02/2024

DyCoV says which revision of the DTR it implements: the one of 15/02/2024, which carries revision
3.3 of article 8.3.3. A later revision enters the tool as a delta over that one, and
`docs/design/DTR_revisions.md` says how. Nothing of that mechanism is in this release.

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

### Fixed

- Islanding simulations run again: the `DYNModelOmegaRef` connectors are written with the names
  Dynawo 2.0.0 expects (#606).
- The WECC examples simulate every test again when several run at once: their plant controller no
  longer has a voltage deadband, on whose edge the WECCVoltageSource4 swell kept the solver (#626).
