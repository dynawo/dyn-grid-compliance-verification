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

Runs RMS model validation against a set of reference curves. Requires a Dynawo
model (``-m``), producer curves (``-c``), or the workbook that describes the
installation (``-e``). With a workbook, the model and its reference curves are
generated from it into a temporary directory that is removed when the run ends,
so the reference directory is not given either and the report names the
workbook as its input.

.. include:: helps/validate.rst

----

dycov performance
-----------------

Runs electric performance verification against the applicable DTR PCSs.
Requires a Dynawo model (``-m``), producer curves (``-c``), or both — when
both are given, compliance is evaluated on the simulated curves only and the
producer curves are drawn in the figures as an overlay.

.. include:: helps/performance.rst

----

dycov generateEnvelopes
-----------------------

Analytically computes GFM admissible response envelopes. No Dynawo model
required — only a ``Producer.ini`` file.

.. include:: helps/generateEnvelopes.rst

----

dycov generate
--------------

Interactive wizard that generates the input files (DYD, PAR, INI, DICT)
needed to run a validation.

.. include:: helps/generate.rst

----

dycov excel2inputs
------------------

Writes the input files of a model — ``Producer.{dyd,par,ini}`` for both zones
and the reference-curve tree — from the workbook that describes it. The
workbook is the single source of truth; nothing else is asked for.

.. include:: helps/excel2inputs.rst

----

dycov anonymize
---------------

Produces an anonymized version of a set of curves, replacing signal names
with generic identifiers and adding a noise signal.

.. include:: helps/anonymize.rst