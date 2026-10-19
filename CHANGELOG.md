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
  in the script that adds the protection's parameters (ticket 4202), before the rest of the chain
  has run;
- none of them writes the capability-curve file, which has to be supplied by hand whichever route
  is taken.

### Fixed

- Islanding simulations run again: the `DYNModelOmegaRef` connectors are written with the names
  Dynawo 2.0.0 expects (#606).
