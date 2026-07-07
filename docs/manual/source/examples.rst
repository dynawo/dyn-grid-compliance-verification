========
Examples
========

The best way to get a feel for DyCoV is to run one of the bundled examples.
They cover all three workflows and use real model files, so you can see exactly
what DyCoV produces before working with your own data.

All examples live under the ``examples/`` directory at the root of the
repository. If you installed DyCoV natively on Linux, a copy was placed in
``~/dycov/examples/`` during installation. If you are using the Docker or WSL
image, the examples are copied to your home directory the first time you start
a session.


How the examples are organized
-------------------------------

.. code-block:: text

   examples/
   ├── Model/
   │   ├── Wind/
   │   │   └── WECC4B/
   │   │       ├── Dynawo/
   │   │       │   ├── Zone1/
   │   │       │   └── Zone3/
   │   │       └── ReferenceCurves/
   │   └── ProducerCurves/
   │       ├── BESS/
   │       └── PPM/
   ├── Performance/
   │   ├── Single/
   │   │   └── WECC4B/
   │   │       └── Dynawo/
   │   └── ProducerCurves/
   │       ├── BESS/
   │       ├── PPM/
   │       └── SM/
   └── GFM/
       ├── Overdamped/
       ├── Underdamped/
       └── Fusion/

A few things worth noting about this layout:

* **Dynawo model examples** live alongside their reference curves
  (``ReferenceCurves/``) in the same case directory. For RMS model validation,
  the model is split into ``Zone1/`` and ``Zone3/`` subfolders, each with its
  own ``Producer.dyd``, ``Producer.par``, and ``Producer.ini``. The topology
  used on the producer side must match one of the
  :ref:`available topologies <topologies>`.

* **Producer curve examples** (``ProducerCurves/``) are a separate entity.
  A single set of curve files is shared across zones; the zone is identified
  through the PCS identifier in the filename and through a per-zone
  ``Producer.ini``.

* **Performance examples** use the ``Single/`` topology name, which refers to
  the producer-side electrical configuration (a single generating unit), not
  to a DyCoV-specific concept.

* **GFM examples** require only a ``Producer.ini`` — no network model and no
  simulation involved.


RMS Model Validation
--------------------

This workflow validates that a dynamic model matches a reference behavior.
It always runs Zone 1 (unit-level) and Zone 3 (plant-level) independently.

Using a Dynawo model:

.. code-block:: console

   cd examples/Model/Wind/WECC4B
   dycov validate ReferenceCurves/ -m Dynawo/

Using producer curves instead of a Dynawo model:

.. code-block:: console

   cd examples/Model/ProducerCurves/PPM
   dycov validate ReferenceCurves/ -c ProducerCurves/

In both cases, DyCoV compares the curves against the reference, evaluates
compliance, and writes a PDF report and interactive HTML plots under
``Results/``.


Electric Performance Verification
-----------------------------------

This workflow checks compliance with grid-code dynamic performance
requirements. No reference curves are needed — only a producer response.

Using a Dynawo model:

.. code-block:: console

   cd examples/Performance/Single/WECC4B
   dycov performance -m Dynawo/

Using producer curves:

.. code-block:: console

   cd examples/Performance/ProducerCurves/PPM
   dycov performance -c ProducerCurves/

Results go to ``Results/`` as well, with the same PDF and HTML structure.


Grid-Forming (GFM) Envelope Generation
-----------------------------------------

Unlike the other two workflows, GFM analysis is purely analytical — it
computes admissible dynamic response envelopes without running any simulation.
All you need is a ``Producer.ini`` describing the GFM unit parameters.

.. code-block:: console

   cd examples/GFM/Overdamped
   dycov generateEnvelopes -i Producer.ini

The three example configurations represent different dynamic regimes:

* ``Overdamped/`` — the unit's response is overdamped
* ``Underdamped/`` — the unit's response is underdamped
* ``Fusion/`` — hybrid mode, combining overdamped and underdamped envelopes
  into a single merged envelope

Outputs are CSV files with the envelope data, static PNG figures, and
interactive HTML plots, all written under ``Results/``.