==========================
Adding a new dynamic model
==========================

DyCoV is built on top of Dynawo, which has a large library of dynamic models
covering most power generation and storage technologies. Custom models are
compiled with Dynawo directly. However, DyCoV does not automatically support
every model in Dynawo's library — when a new model is added to Dynawo, or
when an existing one changes its parameter or variable names, DyCoV needs
to be updated to recognize it.

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
``src/dycov/curves/dynawo/dictionary/``:

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

An entry never names a read-only parameter of the model: Dynawo computes those
itself and ignores, without a word, the value a PAR gives them. When Dynawo is
installed, ``tests/dycov/curves/dynawo/dictionary`` checks every entry against
the model descriptors.


Generic keywords by equipment type
------------------------------------

The following sections list the main generic keywords that DyCoV uses for each
equipment type, together with their meaning and when they are required. The
dictionary INI files are the authoritative, complete list; when in doubt, copy
the section of an existing model of the same family.

Every model section must also declare its ``family`` key (``WECC``, ``IEC`` or
``GFM``): it selects which set of control flags applies to the model.

A flag of the tool that the Dynawo model has no parameter for, because the model
always behaves one way, is written as its value, ``true`` or ``false``, in place
of the name of a parameter.

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

* ``'NetworkFrequencyReference'``
    Reference frequency value. Required when OmegaRef is a *SetPoint* or an
    *InfiniteBus*.

* ``'InternalAngle'``
    Internal angle in radians. Required for Electrical Performance
    Verification.

* ``'VoltageSetpointPu'``
    Control voltage in per unit. Always required.

* ``'MagnitudeControlledByAVRPu'``
    Voltage amplitude controlled by the AVR in per unit. Always required.


Power Park
^^^^^^^^^^

The generic keywords for Power Park models are the same as for Synchronous
Generators, with the same applicability conditions, plus the following
converter-specific keys and model-family-specific control flags.

Node2, the converter terminal between the unit and its transformer, as the DTR names it
(required for Electrical Performance Verification and Model Validation). The dictionary
declares what the Dynawo model provides; the tool divides the powers by the voltage and emits
the currents as ``'ActiveCurrentNode2'`` and ``'ReactiveCurrentNode2'``:

* ``'ActivePowerNode2'`` — active power at Node2 (pu).
* ``'ReactivePowerNode2'`` — reactive power at Node2 (pu).
* ``'VoltageNode2'`` — the amplitude of the voltage at Node2 (pu), when the model
  provides it; otherwise ``'VoltageNode2Re'`` / ``'VoltageNode2Im'``, its
  components, whose amplitude the tool emits under that same name.
* ``'CurrentNode2Re'`` / ``'CurrentNode2Im'`` — the components of the current the
  unit injects at Node2 (pu, generator convention), in place of the two powers when
  the model gives none there: the tool computes them from that current and the
  voltage components.
* ``'MaxCurrentAtConverter'`` — maximum current amplitude (pu). Required for
  Electrical Performance Verification.

A unit model, with no plant controller, is the Zone 1 model, and its control measures at
Node1 or at Node2 — the controlled node:

* ``'ActivePowerControlledNode'``, ``'ReactivePowerControlledNode'`` — the powers the
  converter injects at the controlled node (pu). Required for Model Validation.
* ``'VoltageControlledNode'`` — the voltage at the controlled node (pu). It takes the
  place of ``'MagnitudeControlledByAVRPu'``, which is the magnitude a plant controller
  regulates. No test asks for it yet.

The initial values at the PCC (``'ActivePowerPcc0Pu'``, ``'ReactivePowerPcc0Pu'``,
``'VoltagePcc0Pu'``, ``'PhasePcc0'``) and ``'PPCLocal'`` belong to the plant controller: only
plant models declare them.

Setpoints (required for Model Validation):

* ``'ActivePowerSetpointPu'`` — active power setpoint (pu).
* ``'ReactivePowerSetpointPu'`` — reactive power setpoint (pu).

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

* ``'FreqFlag'``
    Plant-level frequency control: governor response disabled (False) or
    enabled (True). Plant models only.

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

The Grid Forming converters of Dynawo the tool supports
(``GridFormingConverterDroopControl`` and ``GridFormingEpri``, family ``GFM``)
have no control flags: the family lists ``FrequencyDroop``, the active power
droop, as the parameter every model of the family has, and no control mode, so
they take every test. Both reach their terminal through an impedance of their
own, which no parameter switches off (``ConverterLVControl = false``). The
droop converter takes its references at its filter capacitor, behind that
impedance (``SetpointsBehindTransformer = true``): the initial value of a
stepped setpoint is then computed there, through ``TransformerResistance`` and
``TransformerReactance``, and not at the terminal. The EPRI converter takes
them at its terminal, and has no input for the frequency reference of the
network (``NetworkFrequencyReference``): it sees the frequency of the grid only
through the phase of its voltage. The tests of the Fiche I16.2 drive the
frequency from the table of the infinite bus, which then turns its phase with
it, so they reach such a unit; those that drive it through an Omega model, the
frequency ramp and the islanding of Zone 3, do not.


Line
^^^^

Initialization:

* ``'ResistancePu'``, ``'ReactancePu'``, ``'SusceptancePu'``,
  ``'ConductancePu'``
  — R, X, half-B, half-G in per unit. Required for initialization.

* ``'SwitchOffSignal10'``, ``'SwitchOffSignal20'``
    Initial switch-off signals of the line; a line one of them holds open from
    the start is left out of the initialization.


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
    Transformer ratio in per unit, for a fixed-ratio transformer. Required for
    initialization.

* ``'Tap0'``, ``'NbTap'``, ``'RhoMin'``, ``'RhoMax'``
    Starting tap, number of taps and ratio range of a tap changer, whose starting
    ratio the tool derives from them as Dynawo does. They take the place of
    ``'Rho'``: Dynawo computes a tap changer's starting ratio itself and ignores
    one a PAR states.

* ``'SNom'``
    Nominal apparent power in MVA. Required if the impedance values above are
    expressed in percent rather than per unit.

* ``'ActivePower10'``, ``'ReactivePower10'``, ``'Voltage10'``, ``'Phase10'``
  — start values at terminal 1. Required for initialization.

* ``'Tap'``
    Current tap position.


Control Modes
--------------

The ``Control_Modes.ini`` file (located at
``src/dycov/curves/dynawo/dictionary/Control_Modes.ini``) defines all available control
mode configurations. It is organized in three sections.

The ``[Parameters]`` section defines which flags are relevant for each
family/zone combination:

.. code-block:: ini

   [Parameters]
   ControlMode_WECC_Zone3 = PfFlag,VFlag,QFlag,PFlag,FreqFlag,RefFlag
   ControlMode_WECC_Zone1 = PfFlag,VFlag,QFlag,PFlag
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
     - the six ``USetpoint_IEC_Zone3`` options
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
     - PFlag
     - FreqFlag
   * - ``WTG_Voltage_Droop``
     - —
     - —
     - —
     - True
     - False
     - —
     - —
   * - ``WTG_UControl_Local_Coordinated``
     - False
     - True
     - True
     - True
     - —
     - —
     - —
   * - ``WTG_QControl_Local_Coordinated``
     - False
     - True
     - True
     - False
     - —
     - —
     - —
   * - ``WTG_Only_UControl``
     - False
     - —
     - False
     - True
     - —
     - —
     - —
   * - ``WTG_Only_QControl``
     - False
     - —
     - False
     - False
     - —
     - —
     - —
   * - ``WTG_PControl``
     - —
     - —
     - —
     - —
     - —
     - False
     - True
   * - ``WTG_PControl_Oscillation``
     - —
     - —
     - —
     - —
     - —
     - True
     - True

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
