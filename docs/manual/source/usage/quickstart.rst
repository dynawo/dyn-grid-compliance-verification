===============
Getting Started
===============

DyCoV has three main workflows, each with its own entry point:

* For :ref:`RMS Model Validation <model_validation>`: ``dycov validate``
* For :ref:`Electric Performance Verification <perf_verification>`: ``dycov performance``
* For :ref:`Grid-Forming envelope generation <gfm_envelopes_cmd>`: ``dycov generateEnvelopes``

There are also two utility commands: ``dycov generate`` to create input files
through a guided process, and ``dycov anonymize`` to produce anonymized curve
files. All commands are described below.

Run ``dycov --help`` (or ``-h``) at any time to get a quick overview:

.. include:: helps/dycov.rst


.. _model_validation:

RMS Model Validation
--------------------

RMS model validation checks whether a dynamic model behaves as expected by
comparing its response against a set of reference curves. The tests follow the
*PCS* defined in the ION stage of the RTE DTR, but the objective here is to
validate the model — not the electrical performance of the installation. This
means reference curves are always required, in addition to either a Dynawo
model or producer curves.

You would use the command ``dycov validate``:

.. include:: helps/validate.rst

.. note::
   If you installed DyCoV natively on Linux, make sure the virtual
   environment is active before running any command:

   .. code-block:: console

      source ~/dycov/activate_dycov

   You can tell the environment is active because the shell prompt will show
   its name. The Docker and WSL installations handle this automatically.


.. _perf_verification:

Electric Performance Verification
----------------------------------

Electric performance verification checks whether an installation meets the
dynamic performance requirements defined in the RTE DTR PCS. Unlike model
validation, no reference curves are needed — the tool evaluates the producer
response directly against the PCS criteria.

This workflow applies to Power Park Modules (PPM), Battery Energy Storage
Systems (BESS), and Synchronous Machines (SM).

The producer response can come from a Dynawo model (the tool runs the
simulations) or from producer-provided curves. You would use the command
``dycov performance``:

.. include:: helps/performance.rst

.. note::
   If you installed DyCoV natively on Linux, make sure the virtual
   environment is active before running any command:

   .. code-block:: console

      source ~/dycov/activate_dycov

For the format of DYD and PAR files (the Dynawo model of the producer's
facilities), refer to the Dynawo documentation. The format of INI and curve
files is documented in this manual.


.. _gfm_envelopes_cmd:

GFM Envelope Generation
------------------------

Grid-Forming (GFM) analysis is a purely analytical workflow — no dynamic
simulation is involved. Given the key parameters of a GFM unit (inertia,
damping, effective reactance), the tool computes the admissible upper and
lower response envelopes for specific grid disturbances.

You would use the command ``dycov generateEnvelopes``:

.. include:: helps/generateEnvelopes.rst

The output consists of CSV files with the envelope data, static PNG figures,
and interactive HTML plots.

.. seealso::
   For a detailed description of the supported disturbance cases, input
   parameters, and output format, see :doc:`GFM Envelope Generation <gfm_envelopes>`.


Generate Producer Input Files
------------------------------

If you are starting from scratch and need to create the input files required
by DyCoV, the ``dycov generate`` command walks you through the process
interactively:

.. include:: helps/generate.rst


Curve Anonymizer
----------------

The anonymizer produces a version of your curves with generic signal names
and an added noise signal, useful for sharing data without exposing
proprietary information. You would use the command ``dycov anonymize``:

.. include:: helps/anonymize.rst