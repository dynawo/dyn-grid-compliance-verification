==========================
Adding a new dynamic model
==========================

Dynamic grid Compliance Verification is a tool  designed to carry out several tests related to
RTE's grid code requirements on new generating plants that want to connect to the grid. It
implements the tests defined in RTE's DTR document, the so called "PCSs" of type "I" (I2, I3,
etc.).  These PCSs include compliance tests for both electric performance requirements as well as
RMS model fidelity requirements.

This tool is based on Dynawo, RTE's dynamic network simulator. Dynawo has a large library of models
covering most of the modeling needs of new power generation projects. However, the tool does not
automatically support all of Dynawo's models: if a new model is added to Dynawo's library, or if an
existing one modifies its parameters or variable names, some additions or modifications will be
needed in this Tool in order to support those changes.

The two subsections below describe these additions, and how they should be prepared:
   * Dynawo Models "Master Dictionary": describes the internal dictionary that maps
     variable/parameter names used by each specific model to the tool's generic names.
   * Dynawo Model Description: describes the ``ini`` file that should be
     prepared for each new Dynawo model that the tool may need to support.




Dynawo Models "Master Dictionary"
---------------------------------

Anytime the DyCoV tool needs to read/modify a variable or a parameter in the PAR or CRV Dynawo files,
it needs to know the precise name of that variable/parameter *for the particular Dynawo model in
question*.  Therefore, the tool needs to maintain an internal dictionary that maps the
variable/parameter names used by each specific model to the tool's generic names. This dictionary
is located in the ``src/dycov/dynawo/dictionary`` of the tool.

To add support for a new Dynawo model in the Dynamic grid Compliance Verification Tool, it is necessary
to modify the ``ini`` file corresponding to the type of equipment to which it belongs (``Bus.ini,
Control_Modes.ini, Line.ini, Load.ini, Power_Park.ini, Storage.ini, Synch_Gen.ini, Transformer.ini``) 
and link the keywords used in the Tool with the corresponding Dynawo parameter of the model.


Bus
^^^
The Tool uses the following keywords to define the dynamic model:

* ``'VoltageRe'``
    Real part of complex AC voltage in per unit. It is required for the PDR.

* ``'VoltageIm'``
    Imaginary part of complex AC voltage in per unit. It is required for the PDR.

* ``'Voltage'``
    Modulus of complex AC voltage in per unit. If the dynamic model does not have this information,
    the tool calculates it from 'VoltageRe' and 'VoltageIm'. It is required for the PDR.

* ``'NetworkFrequencyPu'``
    Bus frequency in per unit. It is required in Model Validation.


Synchronous Generator
^^^^^^^^^^^^^^^^^^^^^
The Tool uses the following keywords to define the dynamic model:

* ``'ActivePower0Pu'``
    Start value of active power at terminal in per unit. It is required for initialization.

* ``'ReactivePower0Pu'``
    Start value of reactive power at terminal in per unit. It is required for initialization.

* ``'Voltage0Pu'``
    Start value of voltage amplitude at terminal in per unit. It is required for initialization.

* ``'Phase0'``
    Start value of voltage angle at terminal in per unit. It is required for initialization.

* ``'Running'``
    Indicates if the generator is running or not. It is required when OmegaRef model is
    *DYNModelOmegaRef*.

* ``'RotorSpeedPu'``
    Angular frequency in per unit. It is required when OmegaRef model is
    *DYNModelOmegaRef* and/or for Electrical Performance Verification.

* ``'NetworkFrequencyPu'``
    Reference frequency in per unit. It is required when OmegaRef model is
    *DYNModelOmegaRef* and/or for Electrical Performance Verification and Model Validation.

* ``'NetworkFrequencyValue'``
    Reference frequency value. It is required when OmegaRef model is a *SetPoint* or an
    *InfiniteBus*.

* ``'InternalAngle'``
    Internal angle in rad. It is required for Electrical Performance Verification.

* ``'AVRSetpointPu'``
    Control voltage in per unit. It is required.

* ``'MagnitudeControlledByAVRPu'``
    Magnitude voltage amplitude in per unit. It is required.

* ``'InjectedActiveCurrent'``
    Injected active current in per unit. It is required for Electrical Performance Verification and
    Model Validation.

* ``'InjectedReactiveCurrent'``
    Injected reactive current in per unit. It is required for Electrical Performance Verification and
    Model Validation.

* ``'InjectedCurrentMax'``
    Maximum current amplitude in per unit. It is required for Electrical Performance Verification.

* ``'ActivePowerSetpointPu'``
    Active power set-point in per unit. It is required Model Validation.

* ``'ReactivePowerSetpointPu'``
    Reactive power set-point in per unit. It is required Model Validation.


Power Park
^^^^^^^^^^
The Tool uses the following keywords to define the dynamic model:

* ``'ActivePower0Pu'``
    Start value of active power at terminal in per unit. It is required for initialization.

* ``'ReactivePower0Pu'``
    Start value of reactive power at terminal in per unit. It is required for initialization.

* ``'Voltage0Pu'``
    Start value of voltage amplitude at terminal in per unit. It is required for initialization.

* ``'Phase0'``
    Start value of voltage angle at terminal in per unit. It is required for initialization.

* ``'Running'``
    Indicates if the generator is running or not. It is required when OmegaRef model is
    *DYNModelOmegaRef*.

* ``'RotorSpeedPu'``
    Angular frequency in per unit. It is required when OmegaRef model is
    *DYNModelOmegaRef* and/or for Electrical Performance Verification.

* ``'NetworkFrequencyPu'``
    Reference frequency in per unit. It is required when OmegaRef model is
    *DYNModelOmegaRef* and/or for Electrical Performance Verification and Model Validation.

* ``'NetworkFrequencyValue'``
    Reference frequency value. It is required when OmegaRef model is a *SetPoint* or an
    *InfiniteBus*.

* ``'InternalAngle'``
    Internal angle in rad. It is required for Electrical Performance Verification.

* ``'AVRSetpointPu'``
    Control voltage in per unit. It is required.

* ``'MagnitudeControlledByAVRPu'``
    Magnitude voltage amplitude in per unit. It is required.

* ``'InjectedActiveCurrent'``
    Injected active current in per unit. It is required for Electrical Performance Verification and
    Model Validation.

* ``'InjectedReactiveCurrent'``
    Injected reactive current in per unit. It is required for Electrical Performance Verification and
    Model Validation.

* ``'InjectedCurrentMax'``
    Maximum current amplitude in per unit. It is required for Electrical Performance Verification.

* ``'ActivePowerSetpointPu'``
    Active power set-point in per unit. It is required Model Validation.

* ``'ReactivePowerSetpointPu'``
    Reactive power set-point in per unit. It is required Model Validation.

WECC Family
"""""""""""

* ``'RefFlag'``
    RefFlag Plant level: reactive power (False) or voltage control (True). Only in Plant models.

* ``'VCompFlag'``
    VCompFlag Plant level (if RefFlag is True): Reactive droop (False) or line drop compensation
    (True). Only in Plant models.

* ``'VFlag'``
    VFlag Voltage control flag: voltage control (False) or Q control (True).

* ``'QFlag'``
    Q control flag: const. pf or Q ctrl (False) or voltage/Q (True).

* ``'PFlag'``
    Power reference flag: const. Pref (False) or consider generator speed (True).

* ``'PfFlag'``
    Power factor flag: Q control (False) or pf control(True).

IEC Family
""""""""""

* ``'MwpqMode'``
    Control mode: reactive power reference (0), power factor reference (1), UQ static (2),
    voltage control (3). Only in Plant models.

* ``'MqG'``
    MqG QControl: Voltage control (0), reactive power control (1), open loop recative power (2),
    power factor control (3), open loop power factor control (4).


Storage
^^^^^^^
The Tool uses the following keywords to define the dynamic model:

* ``'ActivePower0Pu'``
    Start value of active power at terminal in per unit. It is required for initialization.

* ``'ReactivePower0Pu'``
    Start value of reactive power at terminal in per unit. It is required for initialization.

* ``'Voltage0Pu'``
    Start value of voltage amplitude at terminal in per unit. It is required for initialization.

* ``'Phase0'``
    Start value of voltage angle at terminal in per unit. It is required for initialization.

* ``'NetworkFrequencyPu'``
    Reference frequency in per unit. It is required when OmegaRef model is
    *DYNModelOmegaRef* and/or for Electrical Performance Verification and Model Validation.

* ``'NetworkFrequencyValue'``
    Reference frequency value. It is required when OmegaRef model is a *SetPoint* or an
    *InfiniteBus*.

* ``'AVRSetpointPu'``
    Control voltage in per unit. It is required.

* ``'MagnitudeControlledByAVRPu'``
    Magnitude voltage amplitude in per unit. It is required.

* ``'InjectedActiveCurrent'``
    Injected active current in per unit. It is required for Electrical Performance Verification and
    Model Validation.

* ``'InjectedReactiveCurrent'``
    Injected reactive current in per unit. It is required for Electrical Performance Verification and
    Model Validation.

* ``'InjectedCurrentMax'``
    Maximum current amplitude in per unit. It is required for Electrical Performance Verification.

* ``'ActivePowerSetpointPu'``
    Active power set-point in per unit. It is required Model Validation.

* ``'ReactivePowerSetpointPu'``
    Reactive power set-point in per unit. It is required Model Validation.

WECC Family
"""""""""""

* ``'RefFlag'``
    RefFlag Plant level: reactive power (False) or voltage control (True). Only in Plant models.

* ``'VCompFlag'``
    VCompFlag Plant level (if RefFlag is True): Reactive droop (False) or line drop compensation
    (True). Only in Plant models.

* ``'VFlag'``
    VFlag Voltage control flag: voltage control (False) or Q control (True).

* ``'QFlag'``
    Q control flag: const. pf or Q ctrl (False) or voltage/Q (True).

* ``'PFlag'``
    Power reference flag: const. Pref (False) or consider generator speed (True).

* ``'PfFlag'``
    Power factor flag: Q control (False) or pf control(True).

Line
^^^^
The Tool uses the following keywords to define the dynamic model:

* ``'ResistancePu'``
    Resistance in per unit. It is required for initialization.

* ``'ReactancePu'``
    Reactance in per unit. It is required for initialization.

* ``'SusceptancePu'``
    Half-susceptance in per unit. It is required for initialization.

* ``'ConductancePu'``
    Half-conductance in per unit. It is required for initialization.

* ``'ActivePower'``
    Active power on side 2 in per unit. It is required.

* ``'ReactivePower'``
    Reactive power on side 2  in per unit. It is required.

* ``'ActiveCurrent'``
    Active current on side 2 in per unit. It is required in Model Validation.

* ``'ReactiveCurrent'``
    Reactive current on side 2 in per unit. It is required in Model Validation.


Load
^^^^
The Tool uses the following keywords to define the dynamic model:

* ``'ActivePower0'``
    Start value of active power in per unit. It is required for initialization.

* ``'ReactivePower0'``
    Start value of reactive power in per unit. It is required for initialization.

* ``'Voltage0'``
    Start value of voltage amplitude at load terminal in per unit. It is required for
    initialization.

* ``'Phase0'``
    Start value of voltage angle at load terminal in rad. It is required for initialization.

* ``'ActivePower'``
    Active power at load terminal in per unit. It is required.

* ``'ReactivePower'``
    Reactive power at load terminal  in per unit. It is required.

* ``'ActiveCurrent'``
    Active current at load terminal in per unit. It is required in Model Validation.

* ``'ReactiveCurrent'``
    Reactive current at load terminal in per unit. It is required in Model Validation.


Transformer
^^^^^^^^^^^
The Tool uses the following keywords to define the dynamic model:

* ``'Resistance'``
    Resistance. It is required for initialization.

* ``'Reactance'``
    Reactance. It is required for initialization.

* ``'Susceptance'``
    Susceptance. It is required for initialization.

* ``'Conductance'``
    Conductance. It is required for initialization.

* ``'Rho'``
    Start value of transformer ratio in per unit. It is required for initialization.

* ``'SNom'``
    Nominal apparent power in MVA. It is required if 'Resistance', 'Resistance', 'Resistance' and
    'Resistance' are expressed in %.

* ``'ActivePower0'``
    Start value of active power at terminal 1 in per unit. It is required for initialization.

* ``'ReactivePower0'``
    Start value of reactive power at terminal 1 in per unit. It is required for initialization.

* ``'Voltage0'``
    Start value of voltage amplitude at terminal 1 in per unit. It is required for initialization.

* ``'Phase0'``
    Start value of voltage angle at terminal 1 in rad. It is required for initialization.

* ``'VoltageSetpoint'``
    Voltage set-point on side 2 in per unit. It is required for initialization.

* ``'Tap'``
    Current tap.

Control Modes
^^^^^^^^^^^^^
The Tool uses this dictionary to define the valid options of control modes by:

* test type (USetpoint or QSetpoint)
* family (WECC or IEC)
* level (Plant or Turbine

Under the ``ControlModes`` section the list of valid options for configuring the control mode
is defined by dividing the models according to the mentioned characteristics. The parameter name
must be created using the following rule:

    ``testType_family_level``

An example of the ``ControlModes`` section:

.. code-block:: console

    [ControlModes]
    USetpoint_WECC_Plant = WTG_UControl_Local_Coordinated,WTG_Only_UControl
    QSetpoint_WECC_Plant = WTG_QControl_Local_Coordinated,WTG_Only_QControl

    USetpoint_WECC_Turbine = WT_Local_Coordinated,WT_UControl
    QSetpoint_WECC_Turbine = WT_Local_Coordinated,WT_QControl

    USetpoint_IEC_Plant = IECWPP_UQStatic,IECWPP_Openloop_UQStatic,IECWPP_UControl
    QSetpoint_IEC_Plant = IECWPP_QControl,IECWPP_Openloop_QControl

    USetpoint_IEC_Turbine = IECWT_UControl
    QSetpoint_IEC_Turbine = IECWT_QControl,IECWT_Openloop_QControl


A section is defined below for each of the previously configured options. These sections consist
of the dynamic model parameters that need to be configured and the value to be applied.

An example of a valid option section for a WECC dynamic model:

.. code-block:: console

    [WTG_UControl_Local_Coordinated]
    PfFlag = False
    VFlag = True
    QFlag = True
    RefFlag = True


An example of a valid option section for a IEC dynamic model:

.. code-block:: console

    [IECWPP_UQStatic]
    MqG = 1
    MwpqMode = 2
