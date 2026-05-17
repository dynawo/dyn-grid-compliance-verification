=============
CLI Reference
=============

This page documents all DyCoV command-line commands. The output shown for
each command is generated automatically from the tool itself, so it always
reflects the current version.

For usage examples and workflow context, see :ref:`get-started`.

----

dycov
-----

The main entry point. Run without arguments to see the available subcommands.

.. include:: helps/dycov.rst

----

dycov validate
--------------

Runs RMS model validation against a set of reference curves. Requires either
a Dynawo model (``-m``) or producer curves (``-c``).

.. include:: helps/validate.rst

----

dycov performance
-----------------

Runs electric performance verification against the applicable DTR PCSs.
Requires either a Dynawo model (``-m``) or producer curves (``-c``).

.. include:: helps/performance.rst

----

dycov generateEnvelopes
-----------------------

Analytically computes GFM admissible response envelopes. No Dynawo model
required — only a ``Producer.ini`` file.

.. include:: helps/generate.rst

----

dycov generate
--------------

Interactive wizard that generates the input files (DYD, PAR, INI, DICT)
needed to run a validation.

.. include:: helps/generate.rst

----

dycov anonymize
---------------

Produces an anonymized version of a set of curves, replacing signal names
with generic identifiers and adding a noise signal.

.. include:: helps/anonymize.rst