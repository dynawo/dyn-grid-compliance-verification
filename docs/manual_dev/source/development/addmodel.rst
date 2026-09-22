==========================
Adding a new dynamic model
==========================

DyCoV is built on top of Dynawo, which has a large library of dynamic models
covering most power generation and storage technologies. However, DyCoV does
not automatically support every model in Dynawo's library — when a new model
is added to Dynawo, or when an existing one changes its parameter or variable
names, DyCoV needs to be updated to recognize it.

This section explains what that update involves and how to do it.


How DyCoV maps model variables
--------------------------------

Whenever DyCoV needs to read or write a variable or parameter in a Dynawo
PAR or CRV file, it needs to know the precise name of that variable *for
the specific Dynawo model in use*. For example, the voltage regulation
setpoint of a generating unit is called ``voltageRegulator_UsRefPu`` for
synchronous generators, ``WTG4B_wecc_repc_URefPu`` for WECC wind models,
and ``WPP_xWPRefPu`` for IEC models — but DyCoV refers to all of them
generically as ``VoltageSetpointPu``.

This mapping is maintained in a set of INI files located under
``src/dycov/dynawo/dictionary/``:

* ``Bus.ini``
* ``Control_Modes.ini``
* ``Line.ini``
* ``Load.ini``
* ``Power_Park.ini``
* ``Storage.ini``
* ``Synch_Gen.ini``
* ``Transformer.ini``

To add support for a new Dynawo model, find the INI file corresponding to
the equipment type and add the mapping from the model's Dynawo variable names
to the DyCoV generic keywords described below.


Generic keywords by equipment type
------------------------------------

The following sections list all the generic keywords that DyCoV uses for each
equipment type, together with their meaning and when they are required.

Bus
^^^

* ``'VoltageRe'``
    Real part of complex AC voltage in per unit. Required for the PDR bus.

* ``'VoltageIm'``
    Imaginary part of complex AC voltage in per unit. Required for the PDR bus.

* ``'Voltage'``
    Modulus of complex AC voltage in per unit. If the model does not expose
    this directly, the tool computes it from ``VoltageRe`` and ``VoltageIm``.
    Required for the PDR bus.

* ``'NetworkFrequencyPu'``
    Bus frequency in per unit. Required for Model Validation.


Synchronous Generator
^^^^^^^^^^^^^^^^^^^^^

Initialization:

* ``'ActivePower0Pu'`` — start value of active power at terminal (pu).
* ``'ReactivePower0Pu'`` — start value of reactive power at terminal (pu).
* ``'Voltage0Pu'`` — start value of voltage amplitude at terminal (pu).
* ``'Phase0'`` — start value of voltage angle at terminal (pu).

Control and frequency:

* ``'Running'``
    Indicates whether the generator is running. Required when the OmegaRef
    model is *DYNModelOmegaRef*.

* ``'RotorSpeedPu'``
    Angular frequency in per unit. Required when OmegaRef is
    *DYNModelOmegaRef* and/or for Electrical Performance Verification.

* ``'NetworkFrequencyPu'``
    Reference frequency in per unit. Required when OmegaRef is
    *DYNModelOmegaRef* and/or for Electrical Performance Verification and
    Model Validation.

* ``'NetworkFrequencyValue'``
    Reference frequency value. Required when OmegaRef is a *SetPoint* or an
    *InfiniteBus*.

* ``'InternalAngle'``
    Internal angle in radians. Required for Electrical Performance
    Verification.

* ``'VoltageSetpointPu'``
    Control voltage in per unit. Always required.

* ``'MagnitudeControlledByAVRPu'``
    Voltage amplitude controlled by the AVR in per unit. Always required.

Currents (required for Electrical Performance Verification and Model Validation):

* ``'IpInjTerminal'`` — active current at the injector's LV terminal (pu).
* ``'IqInjTerminal'`` — reactive current at the injector's LV terminal (pu).
* ``'UPuInjTerminal'`` — voltage amplitude at the injector terminal (pu).
* ``'MaxCurrentAtConverter'`` — maximum current amplitude (pu). Required for
  Electrical Performance Verification.

Setpoints (required for Model Validation):

* ``'ActivePowerSetpointPu'`` — active power setpoint (pu).
* ``'ReactivePowerSetpointPu'`` — reactive power setpoint (pu).


Power Park
^^^^^^^^^^

The generic keywords for Power Park models are the same as for Synchronous
Generators, with the same applicability conditions, plus the following
model-family-specific control flags.

WECC family:

* ``'RefFlag'``
    Plant-level reactive control: reactive power (False) or voltage control
    (True). Plant models only.

* ``'VCompFlag'``
    Plant-level voltage compensation (when RefFlag is True): reactive droop
    (False) or line drop compensation (True). Plant models only.

* ``'VFlag'``
    Voltage control flag: voltage control (False) or Q control (True).

* ``'QFlag'``
    Q control flag: constant PF or Q control (False) or voltage/Q (True).

* ``'PFlag'``
    Power reference flag: constant Pref (False) or speed-dependent (True).

* ``'PfFlag'``
    Power factor flag: Q control (False) or PF control (True).

IEC family:

* ``'MwpqMode'``
    Control mode: reactive power reference (0), power factor reference (1),
    UQ static (2), voltage control (3). Plant models only.

* ``'MqG'``
    Q control mode: voltage control (0), reactive power control (1), open loop
    reactive power (2), power factor control (3), open loop PF control (4).


Storage
^^^^^^^

The generic keywords for Storage models are a subset of the Power Park
keywords (initialization, frequency, voltage setpoint, currents, setpoints),
with the same applicability conditions and the same WECC family control flags.


Line
^^^^

Initialization:

* ``'ResistancePu'``, ``'ReactancePu'``, ``'SusceptancePu'``,
  ``'ConductancePu'``
  — R, X, half-B, half-G in per unit. Required for initialization.

Measurements (always required):

* ``'ActivePower'`` — active power on side 2 (pu).
* ``'ReactivePower'`` — reactive power on side 2 (pu).

Measurements (required for Model Validation):

* ``'ActiveCurrent'`` — active current on side 2 (pu).
* ``'ReactiveCurrent'`` — reactive current on side 2 (pu).


Load
^^^^

Initialization:

* ``'ActivePower0'``, ``'ReactivePower0'`` — start values of P and Q (pu).
* ``'Voltage0'`` — start voltage amplitude at load terminal (pu).
* ``'Phase0'`` — start voltage angle at load terminal (rad).

Measurements (always required):

* ``'ActivePower'``, ``'ReactivePower'`` — P and Q at load terminal (pu).

Measurements (required for Model Validation):

* ``'ActiveCurrent'``, ``'ReactiveCurrent'`` — currents at load terminal (pu).


Transformer
^^^^^^^^^^^

Initialization:

* ``'Resistance'``, ``'Reactance'``, ``'Susceptance'``, ``'Conductance'``
  — transformer impedance values. Required for initialization.

* ``'Rho'``
    Start value of the transformer ratio in per unit. Required for
    initialization.

* ``'SNom'``
    Nominal apparent power in MVA. Required if the impedance values above are
    expressed in percent rather than per unit.

* ``'ActivePower0'``, ``'ReactivePower0'``, ``'Voltage0'``, ``'Phase0'``
  — start values at terminal 1. Required for initialization.

* ``'VoltageSetpoint'``
    Voltage setpoint on side 2 in per unit. Required for initialization.

* ``'Tap'``
    Current tap position.


Control Modes
--------------

The ``Control_Modes.ini`` file (located at
``src/dycov/configuration/Control_Modes.ini``) defines all available control
mode configurations. It is organized in three sections.

The ``[Parameters]`` section defines which flags are relevant for each
family/zone combination:

.. code-block:: ini

   [Parameters]
   ControlMode_WECC_Zone3 = PfFlag,VFlag,QFlag,PFlag,FreqFlag,RefFlag
   ControlMode_WECC_Zone1 = PfFlag,VFlag,QFlag
   ControlMode_IEC_Zone3  = MqG,MwpqMode
   ControlMode_IEC_Zone1  = MqG
   VoltageDroop_WECC_Zone3 = RefFlag,VCompFlag
   VoltageDroop_IEC_Zone3  = MqG,MwpqMode

The ``[ControlModes]`` section maps each test-type/family/zone combination to
the list of available named configurations, following the naming convention
``<TestType>_<Family>_<Zone>``:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Key
     - Available options
   * - ``USetpoint_WECC_Zone3``
     - ``WTG_UControl_Local_Coordinated``, ``WTG_Only_UControl``
   * - ``QSetpoint_WECC_Zone3``
     - ``WTG_QControl_Local_Coordinated``, ``WTG_Only_QControl``
   * - ``PSetpoint_WECC_Zone3``
     - ``WTG_PControl_Oscillation``, ``WTG_PControl``
   * - ``VoltageDroop_WECC_Zone3``
     - ``WTG_Voltage_Droop``
   * - ``USetpoint_WECC_Zone1``
     - ``WT_UControl``
   * - ``QSetpoint_WECC_Zone1``
     - ``WT_Local_Coordinated``, ``WT_QControl``
   * - ``PSetpoint_WECC_Zone1``
     - ``WT_PControl_Oscillation``, ``WT_PControl``
   * - ``USetpoint_IEC_Zone3``
     - ``IECWPP_ReactivePowerControl_UQStatic``,
       ``IECWPP_ReactivePowerControl_UControl``,
       ``IECWPP_Openloop_UQStatic``, ``IECWPP_Openloop_UControl``,
       ``IECWPP_VoltageControl_UQStatic``, ``IECWPP_VoltageControl_UControl``
   * - ``QSetpoint_IEC_Zone3``
     - ``IECWPP_ReactivePowerControl_QReference``,
       ``IECWPP_Openloop_ReactivePowerControl_QReference``
   * - ``VoltageDroop_IEC_Zone3``
     - ``IECWPP_Voltage_Droop``
   * - ``USetpoint_IEC_Zone1``
     - ``IECWT_VoltageControl``
   * - ``QSetpoint_IEC_Zone1``
     - ``IECWT_ReactivePowerControl``, ``IECWT_Openloop_ReactivePowerControl``

Each named configuration has its own section specifying the flag values to
apply. The naming pattern for plant-level configurations is
``ModelFamily_InverterLevelMode_PlantLevelMode``, and for turbine-level
``ModelFamily_InverterLevelMode``.

WECC plant configurations:

.. list-table::
   :header-rows: 1

   * - Name
     - PfFlag
     - VFlag
     - QFlag
     - RefFlag
     - VCompFlag
   * - ``WTG_Voltage_Droop``
     - —
     - —
     - —
     - True
     - False
   * - ``WTG_UControl_Local_Coordinated``
     - False
     - True
     - True
     - True
     - —
   * - ``WTG_QControl_Local_Coordinated``
     - False
     - True
     - True
     - False
     - —
   * - ``WTG_Only_UControl``
     - False
     - —
     - False
     - True
     - —
   * - ``WTG_Only_QControl``
     - False
     - —
     - False
     - False
     - —
   * - ``WTG_PControl``
     - —
     - —
     - —
     - —
     - —
   * - ``WTG_PControl_Oscillation``
     - —
     - —
     - —
     - —
     - —

WECC turbine configurations:

.. list-table::
   :header-rows: 1

   * - Name
     - PfFlag
     - VFlag
     - QFlag
     - PFlag
   * - ``WT_Local_Coordinated``
     - False
     - True
     - True
     - —
   * - ``WT_UControl``
     - False
     - False
     - True
     - —
   * - ``WT_QControl``
     - False
     - —
     - False
     - —
   * - ``WT_PControl``
     - —
     - —
     - —
     - False
   * - ``WT_PControl_Oscillation``
     - —
     - —
     - —
     - True

IEC plant configurations:

.. list-table::
   :header-rows: 1

   * - Name
     - MqG
     - MwpqMode
   * - ``IECWPP_Voltage_Droop``
     - 0
     - 3
   * - ``IECWPP_ReactivePowerControl_UQStatic``
     - 1
     - 2
   * - ``IECWPP_ReactivePowerControl_UControl``
     - 1
     - 3
   * - ``IECWPP_Openloop_UQStatic``
     - 2
     - 2
   * - ``IECWPP_Openloop_UControl``
     - 2
     - 3
   * - ``IECWPP_VoltageControl_UQStatic``
     - 0
     - 2
   * - ``IECWPP_VoltageControl_UControl``
     - 0
     - 3
   * - ``IECWPP_ReactivePowerControl_QReference``
     - 1
     - 0
   * - ``IECWPP_Openloop_ReactivePowerControl_QReference``
     - 2
     - 0
   * - ``IECWPP_PowerFactorControl_PfReference``
     - 3
     - 1
   * - ``IECWPP_Openloop_PowerFactorControl_PfReference``
     - 4
     - 1

IEC turbine configurations:

.. list-table::
   :header-rows: 1

   * - Name
     - MqG
   * - ``IECWT_VoltageControl``
     - 0
   * - ``IECWT_ReactivePowerControl``
     - 1
   * - ``IECWT_Openloop_ReactivePowerControl``
     - 2
   * - ``IECWT_PowerFactorControl``
     - 3
   * - ``IECWT_Openloop_PowerFactorControl``
     - 4

To add a new control mode, add its name to the appropriate ``[ControlModes]``
entry and define the corresponding section with the flag values. The
``defaultConfig.ini`` defines which of these options is applied by default
for each test type — update it if the new mode should become the default.