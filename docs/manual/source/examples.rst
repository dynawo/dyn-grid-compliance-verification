========
Examples
========

In the examples folder of the root, we can find several valid files to simulate the producer. The
examples are organized by the types of validations that Dynamic grid Compliance Verification can perform.

* Electric Performance Verification
    * for synchronous production units examples are in the examples/SM directory
    * for non-synchronous park of generators examples are in the examples/PPM directory
* RMS Model Validation examples are in the examples/Model directory

And within these directories you can find examples of the topologies (see :ref:`available
topologies <topologies>`):

* Synchronous production units
    * Single synchronous machine + auxiliary load.
    * Single synchronous machine + auxiliary load + internal line.
* Non-synchronous park of generators
    * Single wind park + auxiliary load.
    * Multiple wind park + auxiliary load.
* RMS Model Validation
    * Zone 1 and Zone 3 models for WECC models
    * Zone 1 and Zone 3 models for IEC models

An example of the RMS Model Validation run could be:

.. code-block:: console

    dycov validate $PWD/dycov/examples/Model/Wind/IEC2015/ReferenceCurves -m $PWD/dycov/examples/Model/Wind/IEC2015/Dynawo

The result of the execution should be similar to the following and it should create a results
folder where we have executed the package with the pcs and their respective reports.

.. code-block:: console

    2024-10-11 11:27:51,765 |           DyCoV.ModelValidation |       INFO |       model_validation.py:   92 | DyCoV Model Validation
    2024-10-11 11:27:51,798 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3
    2024-10-11 11:27:56,324 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR10
    2024-10-11 11:27:59,540 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3Qmin
    2024-10-11 11:28:02,960 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientHiZTc800
    2024-10-11 11:28:17,388 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientHiZTc500
    2024-10-11 11:28:33,459 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentBolted
    2024-10-11 11:28:37,575 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentHiZ
    2024-10-11 11:28:50,476 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Active
    2024-10-11 11:28:54,294 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Reactive
    2024-10-11 11:28:57,550 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Voltage
    2024-10-11 11:28:57,601 |                    DyCoV.Dynawo |    WARNING |       model_parameters.py:  351 | IECWT4BCurrentSource2015 control mode will be changed
    2024-10-11 11:29:01,219 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridFreqRamp, OPER. COND.: W500mHz250ms
    2024-10-11 11:29:04,795 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Rise
    2024-10-11 11:29:08,083 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Drop
    2024-10-11 11:29:11,629 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.USetPointStep, OPER. COND.: AReactance
    2024-10-11 11:29:11,694 |                    DyCoV.Dynawo |    WARNING |       model_parameters.py:  351 | IECWPP4BCurrentSource2015 control mode will be changed
    2024-10-11 11:29:15,820 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.USetPointStep, OPER. COND.: BReactance
    2024-10-11 11:29:15,871 |                    DyCoV.Dynawo |    WARNING |       model_parameters.py:  351 | IECWPP4BCurrentSource2015 control mode will be changed
    2024-10-11 11:29:19,563 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.PSetPointStep, OPER. COND.: Dec40
    2024-10-11 11:29:23,539 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.PSetPointStep, OPER. COND.: Inc40
    2024-10-11 11:29:27,268 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.QSetPointStep, OPER. COND.: Inc10
    2024-10-11 11:29:30,366 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.QSetPointStep, OPER. COND.: Dec20
    2024-10-11 11:29:33,440 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.ThreePhaseFault, OPER. COND.: TransientBolted
    2024-10-11 11:29:40,400 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.GridVoltageDip, OPER. COND.: Qzero
    2024-10-11 11:29:46,410 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.GridVoltageSwell, OPER. COND.: QMax
    2024-10-11 11:29:51,451 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.GridVoltageSwell, OPER. COND.: QMin
    2024-10-11 11:29:56,347 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I16z3.Islanding, OPER. COND.: DeltaP10DeltaQ4
    2024-10-11 11:29:58,116 |                    DyCoV.Dynawo |    WARNING |              simulator.py:  892 | Simulation Fails, logs in Results/Model/PCS_RTE-I16z3/Islanding/DeltaP10DeltaQ4/outputs/logs/dynawo.log
    2024-10-11 11:30:47,926 |                  DyCoV.PDFLatex |    WARNING |                 figure.py:  507 | All curves appear to be flat in PCS_RTE-I16z1.GridFreqRamp.W500mHz250ms; something must be wrong with the simulation
    2024-10-11 11:31:46,592 |                    DyCoV.Report |       INFO |                 report.py:  273 |
    Summary Report
    ==============

    ***Run on 2024-10-11 11:31 CEST***
    ***Dynawo version: 1.7.0 (rev:master-4ee311a)***
    ***Model: examples/Model/Wind/IEC2015/Dynawo***
    ***Reference: examples/Model/Wind/IEC2015/ReferenceCurves***


    Pcs          Benchmark                Operating Condition      Overall Result
    -----------------------------------------------------------------------------
    PCS_RTE-I16z1ThreePhaseFault          TransientBoltedSCR3      Compliant
    PCS_RTE-I16z1ThreePhaseFault          TransientBoltedSCR10     Compliant
    PCS_RTE-I16z1ThreePhaseFault          TransientBoltedSCR3Qmin  Compliant
    PCS_RTE-I16z1ThreePhaseFault          TransientHiZTc800        Compliant
    PCS_RTE-I16z1ThreePhaseFault          TransientHiZTc500        Compliant
    PCS_RTE-I16z1ThreePhaseFault          PermanentBolted          Compliant
    PCS_RTE-I16z1ThreePhaseFault          PermanentHiZ             Compliant
    PCS_RTE-I16z1SetPointStep             Active                   Non-compliant
    PCS_RTE-I16z1SetPointStep             Reactive                 Compliant
    PCS_RTE-I16z1SetPointStep             Voltage                  Non-compliant
    PCS_RTE-I16z1GridFreqRamp             W500mHz250ms             Non-compliant
    PCS_RTE-I16z1GridVoltageStep          Rise                     Non-compliant
    PCS_RTE-I16z1GridVoltageStep          Drop                     Non-compliant
    PCS_RTE-I16z3USetPointStep            AReactance               Non-compliant
    PCS_RTE-I16z3USetPointStep            BReactance               Non-compliant
    PCS_RTE-I16z3PSetPointStep            Dec40                    Compliant
    PCS_RTE-I16z3PSetPointStep            Inc40                    Compliant
    PCS_RTE-I16z3QSetPointStep            Inc10                    Compliant
    PCS_RTE-I16z3QSetPointStep            Dec20                    Non-compliant
    PCS_RTE-I16z3ThreePhaseFault          TransientBolted          Compliant
    PCS_RTE-I16z3GridVoltageDip           Qzero                    Compliant
    PCS_RTE-I16z3GridVoltageSwell         QMax                     Compliant
    PCS_RTE-I16z3GridVoltageSwell         QMin                     Compliant
    PCS_RTE-I16z3Islanding                DeltaP10DeltaQ4          Failed simulation


    2024-10-11 11:32:17,921 |                  DyCoV.PDFLatex |       INFO |                 report.py:  414 | PDF done: /tmp/DyCoV_Results_debian/0b738550-9d10-4ead-bfc5-e03cc2bcaee5/Reports/report.tex
    2024-10-11 11:32:36,547 |           DyCoV.ModelValidation |       INFO |       model_validation.py:   40 | Opening the report: Results/Model/Reports/report.pdf
    Opening in existing browser session.

An example of the Electric Performance Verification run could be:

.. code-block:: console

    dycov performance -m $PWD/dycov/examples/SM/Dynawo/SingleAux
    
The result of the execution should be similar to the following and it should create a results 
folder where we have executed the package with the pcs and their respective reports.
    
.. code-block:: console

    2024-10-11 11:34:29,199 |           DyCoV.ModelValidation |       INFO |       model_validation.py:   76 | Electric Performance Verification for Synchronous Machines
    2024-10-11 11:34:29,232 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: AReactance
    2024-10-11 11:34:29,766 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: BReactance
    2024-10-11 11:34:30,215 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I3.LineTrip, OPER. COND.: 2BReactance
    2024-10-11 11:34:30,828 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I4.ThreePhaseFault, OPER. COND.: TransientBolted
    2024-10-11 11:34:41,351 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I6.GridVoltageDip, OPER. COND.: Qzero
    2024-10-11 11:34:42,511 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I7.GridVoltageSwell, OPER. COND.: QMax
    2024-10-11 11:34:43,523 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I7.GridVoltageSwell, OPER. COND.: QMin
    2024-10-11 11:34:44,482 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I8.LoadShedDisturbance, OPER. COND.: PmaxQzero
    2024-10-11 11:34:44,925 |       DyCoV.Operating Condition |       INFO |    operating_condition.py:  237 | RUNNING BENCHMARK: PCS_RTE-I10.Islanding, OPER. COND.: DeltaP10DeltaQ4
    2024-10-11 11:34:57,351 |                    DyCoV.Report |       INFO |                 report.py:  273 |
    Summary Report
    ==============

    ***Run on 2024-10-11 11:34 CEST***
    ***Dynawo version: 1.7.0 (rev:master-4ee311a)***
    ***Model: examples/SM/Dynawo/SingleAux***


    Pcs          Benchmark                Operating Condition      Overall Result
    -----------------------------------------------------------------------------
    PCS_RTE-I2   USetPointStep            AReactance               Non-compliant
    PCS_RTE-I2   USetPointStep            BReactance               Non-compliant
    PCS_RTE-I3   LineTrip                 2BReactance              Compliant
    PCS_RTE-I4   ThreePhaseFault          TransientBolted          Compliant
    PCS_RTE-I6   GridVoltageDip           Qzero                    Compliant
    PCS_RTE-I7   GridVoltageSwell         QMax                     Compliant
    PCS_RTE-I7   GridVoltageSwell         QMin                     Compliant
    PCS_RTE-I8   LoadShedDisturbance      PmaxQzero                Compliant
    PCS_RTE-I10  Islanding                DeltaP10DeltaQ4          Compliant


    2024-10-11 11:35:08,635 |                  DyCoV.PDFLatex |       INFO |                 report.py:  414 | PDF done: /tmp/DyCoV_Results_debian/e66c17ee-caff-4ef1-ae1f-eba5592092bb/Reports/report.tex
    2024-10-11 11:35:08,797 |           DyCoV.ModelValidation |       INFO |       model_validation.py:   40 | Opening the report: Results/Performance/Reports/report.pdf
    Opening in existing browser session.

Additionally, a new example called IEC2020WithProtections has been added, which aims to provide 
a more realistic representation of how the simulations and the tool work in practice. Unlike the 
“standard” examples, which have minimal (or almost non-existent) protection mechanisms, this 
example incorporates realistic protections, resulting in several tests failing and representing 
a much more real scenario.
