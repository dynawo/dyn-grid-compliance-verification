# Acceptance tests of the DTR

These are not unit tests. They read the catalogue the tool ships and assert what the DTR
says, so that a reader sees the norm and not the implementation: the category a unit takes,
the gabarit a fiche applies to it, and the tests a fiche is made of.

They all state the revision they answer for. A test reads the base `20240215` unless it
selects another one with the fixture `revision`: the configuration names the newest
revision, so a test that said nothing would answer for a different DTR at every release.
Every revision after the base has a file of its own, `test_revision_<YYYYMMDD>.py`, which
reads the base and the revision one after the other and shows the difference itself.

`test_delta_is_complete.py` answers for every delta the tool ships, whichever revision wrote
it. It reads the files and asserts what a delta must hold: that the tool implements the
revision, that the delta describes a PCS that exists, and that every test the delta changes
carries its report template, because a template states the conditions of its test in its prose.

Run them alone with `pytest tests/dtr`. The CI runs them with the rest, because
`pytest.ini` points at `tests`.
