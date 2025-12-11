================================================================
Welcome to Dynamic grid Compliance Verification's documentation!
================================================================

The **Dynamic grid Compliance Verification** tool (dycov for short) is designed to automate
most tasks related to the validation of RMS models, in the context of compliance
requirements for new generation facilities. It contemplates **model validation**
properly speaking (i.e., *"does the model and its parameterization match the
actual behavior?"*), as well as **electric performance** requirements testing
(i.e., *"does the behavior, either measured or simulated, pass the grid code
requirements for connection?"*).

The tool is built with **Python**. Internally it is structured as a series of independent
tests, each producing its own report in PDF. These tests correspond to the
*PCSs I** in RTE's Connection Network code - `DTR document`__. To be specific, they contain the following
tests:

* **Electric Performance tests (Synchronous Machines)**: PCSs I2 (except
  stability margin calculations), I3, I4, I6, I7, I8, and I10.
* **Electric Performance tests (Power Park Modules)**: PCSs I2 (except
  stability margin calculations), I5, I6, I7, and I10.
* **RMS Model Validation tests (Power Park Modules)**: PCS I16, structured into:
    - **Zone 1** (WT-level): Fault Ride-Through, Setpoint steps, Grid Frequency ramps, and Grid Voltage step.
    - **Zone 3** (plant-level): Voltage Regulation behavior (like I2), Fault
      Ride-Through (like I5), Voltage-dip Ride-Through (like I6), Voltage-swell Ride-Through
      (like I7), and Islanding (like I10).

Correspondingly, the results directory is structured along these lines.

__ https://www.services-rte.com/files/live//sites/services-rte/files/documentsLibrary/20240729_DTR_5867_fr

Usually, the inputs are simply three files: the **DYD** and **PAR** files
corresponding to the Dynawo model on the producer's side (i.e., everything
"left" of the connection point, the PDR bus), and an **INI** file containing the parameters and metadata that cannot be provided in the DYD/PAR
files. It is also possible to provide a set of curves as input to the tool, these
should be provided as a file in one of the accepted formats plus a
special DICT file that describes the format (see :ref:`Producer Curves <producerCurves>` below).
See the available examples in the `examples` directory, at the top level of the git repository.

Additionally, in the case of *Model Validation*, the user must also provide the
**reference curves** for each test, against which the simulated curves will be
compared. They should be provided as a file in one of the accepted formats plus a
special DICT file that describes the format (see :ref:`Reference Curves <referenceCurves>`
below).

In the case of *Electric Performance* testing, the user has also the option of
providing test curves to be used along Dynawo simulations (just for plotting both
and comparing them).


.. _get-started:

Get Started
===========

These sections cover the basics of getting started with Dynamic grid Compliance Verification.

.. toctree::
   :maxdepth: 3
   :caption: Get started

   usage/installation
   usage/quickstart

.. _user-guides:

Using Dynamic grid Compliance Verification
==========================================

These sections cover various topics in using Dynamic grid Compliance Verification for various
use-case. They are comprehensive guide to using Dynamic grid Compliance Verification in many contexts and assume
more knowledge of Dynamic grid Compliance Verification. If you are new to Dynamic grid Compliance Verification, we recommend
starting with :ref:`get-started`.

.. toctree::
   :maxdepth: 3
   :caption: Using Dynamic grid Compliance Verification

   usage/validations
   usage/inputs
   usage/results
   usage/configuration
   usage/gfm_envelopes

Reference
=========

Reference documentation is more complete and programmatic in nature, it is a collection of
information that can be quickly referenced. If you would like usecase-driven documentation, see
:ref:`get-started` or :ref:`user-guides`.

.. toctree::
   :maxdepth: 3
   :caption: Reference

   usage/configuration
   examples
