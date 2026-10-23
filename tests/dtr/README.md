# Acceptance tests of the DTR

These are not unit tests. They read the catalogue the tool ships and assert what the DTR
says, so that a reader sees the norm and not the implementation: the category a unit takes,
the gabarit a fiche applies to it, and the tests a fiche is made of.

They all state the revision they answer for. Today the tool implements one, the base
`20240215`, so every test here reads the base. A revision that arrives brings two kinds of
test of its own: what its delta writes, and what it writes differently from another
revision.

Run them alone with `pytest tests/dtr`. The CI runs them with the rest, because
`pytest.ini` points at `tests`.
