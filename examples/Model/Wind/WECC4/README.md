# WECC4 — not usable

This plant has two generating units (topology `M`), and DyCoV does not support multi-generator
topologies yet. The example keeps only its Dynawo inputs: it carries no reference curves, and
it is left out of `tools/scripts/models.sh`, so neither `test_tool.sh` nor
`regenerate_curves.sh` runs it.
