================================================================
Welcome to Dynamic grid Compliance Verification's documentation!
================================================================

**Dynamic grid Compliance Verification** (DyCoV for short) automates the
verification of dynamic grid compliance requirements for electrical
installations — wind and solar farms, battery energy storage systems, and
synchronous machines.

It implements three main workflows:

* **RMS model validation** — verifies that the dynamic response of a model
  matches a reference behavior within the tolerances defined by RTE (PCS I16,
  Zones 1 and 3).

* **Electric performance verification** — verifies that an installation meets
  the dynamic performance requirements of RTE's grid code, as specified in the
  applicable `DTR <https://www.services-rte.com/files/live//sites/services-rte/files/documentsLibrary/20240729_DTR_5867_fr>`_
  PCSs:

  - *Synchronous Machines*: PCSs I2, I3, I4, I6, I7, I8, and I10.
  - *Power Park Modules*: PCSs I2, I5, I6, I7, and I10.
  - *Battery Energy Storage Systems*: PCSs I2, I5, I6, I7, and I10.

* **Grid-Forming (GFM) envelope generation** — analytically computes
  admissible dynamic response envelopes for Grid-Forming units under specific
  grid disturbances, without running any time-domain simulation.

The tool is built with **Python** and uses **Dynawo** as the underlying RMS
simulator. The producer response can alternatively be provided as a set of
curves (measured or pre-simulated), in which case no Dynawo model is needed.

For RMS model validation, a set of reference curves is always required in
addition to the producer response.


.. _get-started:

Get Started
===========

New to DyCoV? Start here. These sections cover installation and your first
run.

.. toctree::
   :maxdepth: 3
   :caption: Get started

   usage/installation
   usage/quickstart
   examples


.. _user-guides:

User Guide
==========

These sections cover the main topics in depth. If you are new to DyCoV, we
recommend reading :ref:`get-started` first.

.. toctree::
   :maxdepth: 3
   :caption: User Guide

   usage/validations
   usage/inputs
   usage/understanding_reports
   usage/results
   usage/configuration
   usage/gfm_envelopes


.. _reference:

Reference
=========

Quick-access reference for the most frequently consulted information.

.. toctree::
   :maxdepth: 2
   :caption: Reference

   examples
   usage/configuration
   usage/inputs
   usage/cli_reference