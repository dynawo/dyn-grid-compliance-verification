===========================

TUTORIAL

HOW TO CONFIGURE DyCoV

(c) 2023&mdash;25 RTE  
Developed by Grupo AIA

===========================

--------------------------------------------------------------------------------

#### Table of Contents

1. [Overview](#overview)
2. [Global Information](#global-information)
3. [Enabling/Disabling which tests are run](#enablingdisabling-which-tests-are-run)
    1. [Enabling/disabling whole PCS](#enablingdisabling-whole-pcs)
    2. [Enabling/disabling specific tests of a given PCS](#enablingdisabling-specific-tests-of-a-given-pcs)
5. [Modifying KPIs](#modifying-kpis)
    1. [Definition](#definition)
    2. [Changing the defaults values](#changing-the-defaults-values)
6. [Changing the Log Level](#changing-the-log-level)

## Overview

Dynamic grid Compliance Verification is configured via a **config.ini** file, written in the well-known INI
format (of the [Python flavor](https://docs.python.org/3/library/configparser.html)). The location of 
this file follows the customary standard of each platform for application data:

* Under Linux: ``$HOME/.config/dycov/``
* Under Windows: ``%APPDATA%\Local\dycov\``

The supplied INI file contains basic configuration options. They appear all commented out,
and with the default values. This way it is much easier for the user to configure anything,
and also to find out what the default value is. We also recommend the user that, whenever he wants
to set a configuration, he duplicates the line in order to preserve the information of what was the
default value, as a reminder. For the case of specific definitions of particular PCSs/Benchmarks/OCs,
the config.ini file also includes one generic example at the bottom.

Besides the **config.ini** file, there are two files named **config.ini_BASIC** and **config.ini_ADVANCED**.
These files contain configuration parameters distinguishing between basic and advanced users. If the
user wishes, he can switch between basic and advanced user by overwriting the config.ini file with
the corresponding configuration file.

The tool has another configuration file usually called *Producer.ini*, this file is used to define the 
particular configuration of a case used as input for the tool. For a more detailed description, 
please review the tutorial called **preparing_inputs.md**.

This document describes the configuration options relevant to an user. The configuration file is
organized into sections, where each section has its own configuration options.


## Global Information

In this section the global options are configured, global options are understood as those options
that do not depend on the execution mode of the tool.
The available options are:

* **electric_performance_verification_pcs**

    Comma separated list of *PCSs* that will be used in the **Performance Validation for
    synchronous production units**. Leave the parameter empty to use all *PCSs*.

* **electric_performance_ppm_verification_pcs**

    Comma separated list  of *PCSs* that will be used in the **Performance Validation for
    non-synchronous park of generators**. Leave the parameter empty to use all *PCSs*.

* **electric_performance_bess_verification_pcs**

    Comma separated list  of *PCSs* that will be used in the **Performance Validation for
    non-synchronous park of storages**. Leave the parameter empty to use all *PCSs*.

* **model_ppm_validation_pcs**

    Comma separated list  of *PCSs* that will be used in the **RMS Model Validation for
    non-synchronous park of generators**. Leave the parameter empty to use all *PCSs*.

* **model_bess_validation_pcs**

    Comma separated list  of *PCSs* that will be used in the **RMS Model Validation for
    non-synchronous park of storages**. Leave the parameter empty to use all *PCSs*.

* **file_log_level**

    File Log level (CRITICAL,FATAL,ERROR,WARNING,INFO,DEBUG).

* **console_log_level**

    Console Log level (CRITICAL,FATAL,ERROR,WARNING,INFO,DEBUG).


```ini
[Global]
#  # File Log level (CRITICAL,FATAL,ERROR,WARNING,INFO,DEBUG)
#  file_log_level = INFO
#  # Console Log level (CRITICAL,FATAL,ERROR,WARNING,INFO,DEBUG)
#  console_log_level = INFO
#  # List of SM pcs to be validated (If it's empty, all the SM pcs are validated)
#  electric_performance_verification_pcs =
#  # List of PPM pcs to be validated (If it's empty, all the PPM pcs are validated)
#  electric_performance_ppm_verification_pcs =
#  # List of BESS pcs to be validated (If it's empty, all the PPM pcs are validated)
#  electric_performance_bess_verification_pcs =
#  # List of PPM model pcs to be validated (If it's empty, all the model pcs are validated)
#  model_ppm_validation_pcs =
#  # List of BESS model pcs to be validated (If it's empty, all the model pcs are validated)
#  model_bess_validation_pcs =
```

## Enabling/Disabling which tests are run

### Enabling/disabling whole PCS

By default all PCS's are validated when the tool is executed:

Model validation example:
```
(dycov_venv) user@dynawo:~/work/MyTests$ dycov validate IEC2015ReferenceCurves -m IEC2015Dynawo -o IEC2015
2025-01-21 11:01:28,689 |                DyCoV.Validation |       INFO |             validation.py:  102 | DyCoV Model Validation for Power Park Modules
2025-01-21 11:01:28,780 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3
2025-01-21 11:01:31,522 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR10
2025-01-21 11:01:33,908 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3Qmin
2025-01-21 11:01:36,426 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientHiZTc800
2025-01-21 11:01:46,092 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientHiZTc500
2025-01-21 11:01:55,916 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentBolted
2025-01-21 11:01:58,520 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentHiZ
2025-01-21 11:02:07,251 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Active
2025-01-21 11:02:09,523 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Reactive
2025-01-21 11:02:11,498 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Voltage
2025-01-21 11:02:11,532 |                    DyCoV.Dynawo |    WARNING |       model_parameters.py:  352 | IECWT4BCurrentSource2015 control mode will be changed
2025-01-21 11:02:13,699 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridFreqRamp, OPER. COND.: W500mHz250ms
2025-01-21 11:02:15,869 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Rise
2025-01-21 11:02:18,224 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Drop
2025-01-21 11:02:20,849 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.USetPointStep, OPER. COND.: AReactance
2025-01-21 11:02:20,894 |                    DyCoV.Dynawo |    WARNING |       model_parameters.py:  352 | IECWPP4BCurrentSource2015 control mode will be changed
2025-01-21 11:02:23,405 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.USetPointStep, OPER. COND.: BReactance
2025-01-21 11:02:23,450 |                    DyCoV.Dynawo |    WARNING |       model_parameters.py:  352 | IECWPP4BCurrentSource2015 control mode will be changed
2025-01-21 11:02:25,869 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.PSetPointStep, OPER. COND.: Dec40
2025-01-21 11:02:28,580 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.PSetPointStep, OPER. COND.: Inc40
2025-01-21 11:02:31,331 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.QSetPointStep, OPER. COND.: Inc10
2025-01-21 11:02:33,765 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.QSetPointStep, OPER. COND.: Dec20
2025-01-21 11:02:36,221 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.ThreePhaseFault, OPER. COND.: TransientBolted
2025-01-21 11:02:40,185 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.GridVoltageDip, OPER. COND.: Qzero
2025-01-21 11:02:43,611 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.GridVoltageSwell, OPER. COND.: QMax
2025-01-21 11:02:46,746 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.GridVoltageSwell, OPER. COND.: QMin
2025-01-21 11:02:50,264 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.Islanding, OPER. COND.: DeltaP10DeltaQ4
2025-01-21 11:02:51,340 |                    DyCoV.Dynawo |    WARNING |                 curves.py:  899 | Simulation Fails, logs in ../Results/Model/WindIEC2015/PCS_RTE-I16z3/Islanding/DeltaP10DeltaQ4/outputs/logs/dynawo.log
2025-01-21 11:03:22,537 |                  DyCoV.PDFLatex |    WARNING |                 figure.py:  590 | All curves appear to be flat in PCS_RTE-I16z1.GridFreqRamp.W500mHz250ms; something must be wrong with the simulation
2025-01-21 11:04:02,456 |                    DyCoV.Report |       INFO |                 report.py:  353 | 
Summary Report
==============

***Run on 2025-01-21 11:04 CET***
***Dynawo version: 1.7.0 (rev:master-d2a92c7)***
***Model: IEC2015Dynawo***
***Reference: IEC2015ReferenceCurves***


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


2025-01-21 11:04:08,770 |                  DyCoV.PDFLatex |       INFO |                 report.py:  482 | PDF done.
2025-01-21 11:04:29,676 |                DyCoV.Validation |       INFO |             validation.py:   42 | Opening the report: IEC2015/Reports/report.pdf
```

Performance verification example:
```
(dycov_venv) user@dynawo:~/work/MyTests$ dycov performance -m SingleAuxI -o SingleAuxI
2025-01-21 10:34:31,341 |                DyCoV.Validation |       INFO |             validation.py:   78 | Electric Performance Verification for Synchronous Machines
2025-01-21 10:34:31,387 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: AReactance
2025-01-21 10:34:31,751 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: BReactance
2025-01-21 10:34:32,059 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I3.LineTrip, OPER. COND.: 2BReactance
2025-01-21 10:34:32,344 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I4.ThreePhaseFault, OPER. COND.: TransientBolted
2025-01-21 10:34:37,033 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I6.GridVoltageDip, OPER. COND.: Qzero
2025-01-21 10:34:37,720 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I7.GridVoltageSwell, OPER. COND.: QMax
2025-01-21 10:34:47,406 |                DyCoV.Validation |    WARNING |            performance.py:  142 | P has not reached steady state
2025-01-21 10:34:47,476 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I7.GridVoltageSwell, OPER. COND.: QMin
2025-01-21 10:34:48,064 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I8.LoadShedDisturbance, OPER. COND.: PmaxQzero
2025-01-21 10:34:48,335 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I10.Islanding, OPER. COND.: DeltaP10DeltaQ4
2025-01-21 10:35:03,191 |                    DyCoV.Report |       INFO |                 report.py:  353 | 
Summary Report
==============

***Run on 2025-01-21 10:35 CET***
***Dynawo version: 1.7.0 (rev:master-d2a92c7)***
***Model: SingleAuxI***


Pcs          Benchmark                Operating Condition      Overall Result
-----------------------------------------------------------------------------
PCS_RTE-I2   USetPointStep            AReactance               Non-compliant
PCS_RTE-I2   USetPointStep            BReactance               Non-compliant
PCS_RTE-I3   LineTrip                 2BReactance              Compliant
PCS_RTE-I4   ThreePhaseFault          TransientBolted          Compliant
PCS_RTE-I6   GridVoltageDip           Qzero                    Compliant
PCS_RTE-I7   GridVoltageSwell         QMax                     Non-compliant
PCS_RTE-I7   GridVoltageSwell         QMin                     Compliant
PCS_RTE-I8   LoadShedDisturbance      PmaxQzero                Compliant
PCS_RTE-I10  Islanding                DeltaP10DeltaQ4          Compliant


2025-01-21 10:35:12,217 |                  DyCoV.PDFLatex |       INFO |                 report.py:  482 | PDF done.
2025-01-21 10:35:12,378 |                DyCoV.Validation |       INFO |             validation.py:   42 | Opening the report: SingleAuxI/Reports/report.pdf
```

The user can define which PCS's he wants to validate when running the tool by modifying the configuration 
file. Below is the previous example after modifying the parameter **model_ppm_validation_pcs** for Model
Validation:

```ini
#  # List of PPM model pcs to be validated (If it's empty, all the model pcs are validated)
#  model_ppm_validation_pcs =
model_ppm_validation_pcs = PCS_RTE-I16z1
```

It can be observed in the output of the tool that only the selected PCS's have been validated.

```
(dycov_venv) user@dynawo:~/work/MyTests$ dycov validate IEC2015ReferenceCurves -m IEC2015Dynawo -o IEC2015
2025-01-21 11:20:13,429 |                DyCoV.Validation |       INFO |             validation.py:  102 | DyCoV Model Validation for Power Park Modules
2025-01-21 11:20:13,440 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3
2025-01-21 11:20:15,918 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR10
2025-01-21 11:20:18,734 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3Qmin
2025-01-21 11:20:21,327 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientHiZTc800
2025-01-21 11:20:30,859 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientHiZTc500
2025-01-21 11:20:41,049 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentBolted
2025-01-21 11:20:43,603 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentHiZ
2025-01-21 11:20:51,859 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Active
2025-01-21 11:20:54,021 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Reactive
2025-01-21 11:20:56,105 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Voltage
2025-01-21 11:20:56,117 |                    DyCoV.Dynawo |    WARNING |       model_parameters.py:  352 | IECWT4BCurrentSource2015 control mode will be changed
2025-01-21 11:20:58,279 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridFreqRamp, OPER. COND.: W500mHz250ms
2025-01-21 11:21:00,421 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Rise
2025-01-21 11:21:03,066 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Drop
2025-01-21 11:21:31,562 |                  DyCoV.PDFLatex |    WARNING |                 figure.py:  590 | All curves appear to be flat in PCS_RTE-I16z1.GridFreqRamp.W500mHz250ms; something must be wrong with the simulation
2025-01-21 11:21:39,383 |                    DyCoV.Report |       INFO |                 report.py:  353 | 
Summary Report
==============

***Run on 2025-01-21 11:21 CET***
***Dynawo version: 1.7.0 (rev:master-d2a92c7)***
***Model: IEC2015Dynawo***
***Reference: IEC2015ReferenceCurves***


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


2025-01-21 11:21:41,698 |                  DyCoV.PDFLatex |       INFO |                 report.py:  482 | PDF done.
2025-01-21 11:21:57,007 |                DyCoV.Validation |       INFO |             validation.py:   42 | Opening the report: IEC2015/Reports/report.pdf
```

And the following example shows the result of modifying the 
**electric_performance_verification_pcs** parameter for performance verification.

```ini
#  # List of SM pcs to be validated (If it's empty, all the SM pcs are validated)
#  electric_performance_verification_pcs =
electric_performance_verification_pcs = PCS_RTE-I2,PCS_RTE-I4,PCS_RTE-I8
```

```
(dycov_venv) user@dynawo:~/work/MyTests$ dycov performance -m SingleAuxI -o SingleAuxI
2025-01-21 10:52:30,704 |                DyCoV.Validation |       INFO |             validation.py:   78 | Electric Performance Verification for Synchronous Machines
2025-01-21 10:52:30,717 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: AReactance
2025-01-21 10:52:30,940 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: BReactance
2025-01-21 10:52:31,157 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I4.ThreePhaseFault, OPER. COND.: TransientBolted
2025-01-21 10:52:35,279 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I8.LoadShedDisturbance, OPER. COND.: PmaxQzero
2025-01-21 10:52:39,255 |                    DyCoV.Report |       INFO |                 report.py:  353 | 
Summary Report
==============

***Run on 2025-01-21 10:52 CET***
***Dynawo version: 1.7.0 (rev:master-d2a92c7)***
***Model: SingleAuxI***


Pcs          Benchmark                Operating Condition      Overall Result
-----------------------------------------------------------------------------
PCS_RTE-I2   USetPointStep            AReactance               Non-compliant
PCS_RTE-I2   USetPointStep            BReactance               Non-compliant
PCS_RTE-I4   ThreePhaseFault          TransientBolted          Compliant
PCS_RTE-I8   LoadShedDisturbance      PmaxQzero                Compliant


2025-01-21 10:52:42,402 |                  DyCoV.PDFLatex |       INFO |                 report.py:  482 | PDF done.
2025-01-21 10:52:42,426 |                DyCoV.Validation |       INFO |             validation.py:   42 | Opening the report: SingleAuxI/Reports/report.pdf
```

### Enabling/disabling specific tests of a given PCS

Each DTR document *PCS* has been implemented using the following terminology:

* PCS
    * Benchmarks
        * Operating Conditions

A *PCS* is understood to be the set of tests and/or complaince criteria necessary to validate the
producer's model.

A *Benchmark* contains the invariant description of the RTE model that will be used in the
simulation of its *PCS*. A *PCS* has one or more *Benchmarks*.

Finally, an *Operating Condition* describes the initialization conditions and/or the event conditions
of a *Benchmark*. A *Benchmark* has one or more *Operating Conditions*.

This section shows how to modify the configuration to enable/disable the benchmarks and/or OC of a PCS.

The **config.ini** file contains the list of *Benchmarks* and *Operating Conditions* validated 
by default in the tool:

```ini
## # List of Benchmarks contained in each Performance Checking Sheet (PCS)
## # For PCS's having multiple benchmarks, you can enable/disable them by listing them explicitly.
## [PCS-Benchmarks]
## PCS_RTE-I16z1 = ThreePhaseFault,SetPointStep,GridFreqRamp,GridVoltageStep
## PCS_RTE-I16z3 = USetPointStep,PSetPointStep,QSetPointStep,ThreePhaseFault,GridVoltageDip,GridVoltageSwell,Islanding

## # List of Operating conditions contained in each PCS-Benchmark
## # For Benchmark's having multiple operating conditions, you can enable/disable them by listing them explicitly.
## [PCS-OperatingConditions]
## PCS_RTE-I2.USetPointStep = AReactance,BReactance
## PCS_RTE-I3.LineTrip = 2BReactance
## PCS_RTE-I4.ThreePhaseFault = TransientBolted
## PCS_RTE-I5.ThreePhaseFault = TransientBolted
## PCS_RTE-I6.GridVoltageDip = Qzero
## PCS_RTE-I7.GridVoltageSwell = QMax,QMin
## PCS_RTE-I10.Islanding = DeltaP10DeltaQ4
## PCS_RTE-I16z1.ThreePhaseFault = TransientBoltedSCR3,TransientBoltedSCR10,TransientBoltedSCR3Qmin,TransientHiZTc800,TransientHiZTc500,PermanentBolted,PermanentHiZ
## PCS_RTE-I16z1.SetPointStep = Active,Reactive,Voltage
## PCS_RTE-I16z1.GridFreqRamp = W500mHz250ms
## PCS_RTE-I16z1.GridVoltageStep = Rise,Drop
## PCS_RTE-I16z3.USetPointStep = AReactance,BReactance
## PCS_RTE-I16z3.PSetPointStep = Dec40,Inc40
## PCS_RTE-I16z3.QSetPointStep = Dec20,Inc10
## PCS_RTE-I16z3.ThreePhaseFault = TransientBolted
## PCS_RTE-I16z3.GridVoltageDip = Qzero
## PCS_RTE-I16z3.GridVoltageSwell = QMax,QMin
## PCS_RTE-I16z3.Islanding = DeltaP10DeltaQ4
```

Taking as a starting point the last example of model validation, where only the PCS **PCS_RTE-I16z1** 
was validated, the benchmarks to be validated will be modified, as well as some operating conditions.
Next, the configuration is modified to validate only the benchmarks called *ThreePhaseFault* and *GridVoltageStep*:

```ini
## # List of Benchmarks contained in each Performance Checking Sheet (PCS)
## # For PCS's having multiple benchmarks, you can enable/disable them by listing them explicitly.
## [PCS-Benchmarks]
## PCS_RTE-I16z1 = ThreePhaseFault,SetPointStep,GridFreqRamp,GridVoltageStep
PCS_RTE-I16z1 = ThreePhaseFault,GridVoltageStep
```

And finally, the *ThreePhaseFault* benchmark is modified to not validate *HiZ* type operating conditions:

```ini
## # List of Operating conditions contained in each PCS-Benchmark
## # For Benchmark's having multiple operating conditions, you can enable/disable them by listing them explicitly.
## [PCS-OperatingConditions]
## PCS_RTE-I16z1.ThreePhaseFault = TransientBoltedSCR3,TransientBoltedSCR10,TransientBoltedSCR3Qmin,TransientHiZTc800,TransientHiZTc500,PermanentBolted,PermanentHiZ
PCS_RTE-I16z1.ThreePhaseFault = TransientBoltedSCR3,TransientBoltedSCR10,TransientBoltedSCR3Qmin,PermanentBolted
```

The result of running the tool only has the PCS, benchmarks and operating conditions configured.

```
(dycov_venv) user@dynawo:~/work/MyTests$ dycov validate IEC2015ReferenceCurves -m IEC2015Dynawo -o IEC2015
2025-01-21 12:00:08,479 |                DyCoV.Validation |       INFO |             validation.py:  102 | DyCoV Model Validation for Power Park Modules
2025-01-21 12:00:08,513 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3
2025-01-21 12:00:13,667 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR10
2025-01-21 12:00:16,338 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3Qmin
2025-01-21 12:00:19,777 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentBolted
2025-01-21 12:00:22,939 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Rise
2025-01-21 12:00:25,543 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Drop
2025-01-21 12:00:51,997 |                    DyCoV.Report |       INFO |                 report.py:  353 | 
Summary Report
==============

***Run on 2025-01-21 12:00 CET***
***Dynawo version: 1.7.0 (rev:master-d2a92c7)***
***Model: IEC2015Dynawo***
***Reference: IEC2015ReferenceCurves***


Pcs          Benchmark                Operating Condition      Overall Result
-----------------------------------------------------------------------------
PCS_RTE-I16z1ThreePhaseFault          TransientBoltedSCR3      Compliant
PCS_RTE-I16z1ThreePhaseFault          TransientBoltedSCR10     Compliant
PCS_RTE-I16z1ThreePhaseFault          TransientBoltedSCR3Qmin  Compliant
PCS_RTE-I16z1ThreePhaseFault          PermanentBolted          Compliant
PCS_RTE-I16z1GridVoltageStep          Rise                     Non-compliant
PCS_RTE-I16z1GridVoltageStep          Drop                     Non-compliant


2025-01-21 12:00:55,848 |                  DyCoV.PDFLatex |       INFO |                 report.py:  482 | PDF done.
2025-01-21 12:00:57,018 |                DyCoV.Validation |       INFO |             validation.py:   42 | Opening the report: IEC2015/Reports/report.pdf
```

<span style="background-color: #4976ba;">INFO:</span> The **modify_pcs.md** tutorial explains how to modify the parameters that define a PCS, 
Benchmark and/or Operating condition.


## Modifying KPIs

### Definition

The tool contemplates two types of verifications:

- **Performance verifications**: defines the state that a curve must have after a given period of 
    time with respect to the event produced in the PCS. Each compliance check of the performance
    verification is defined in the tool as a complete test, so modifying any test requires modifying
    the source code of the tool. Some examples of defined performance verifications in the tool are:
  - **T<sub>10p</sub> - T<sub>event</sub> < 5s**
      - **T<sub>10p</sub>** is time at which the supplied power P stays inside the +/-10% "tube" centered on the final value of P.
      - **T<sub>event</sub>** is time at which the event is triggered.
  - **T<sub>5p</sub> - T<sub>event</sub> < 10s**
      - **T<sub>5p</sub>** is time at which the supplied powerP stays inside the +/-5% "tube" centered on the final value of P.
      - **T<sub>event</sub>** is time at which the event is triggered.
  - **T<sub>10p</sub> - T<sub>85u</sub> < 5 sec**
      - **T<sub>10p</sub>** is time at which the supplied power P stays inside the +/-10% "tube" centered on the final value of P.
      - **T<sub>85u</sub>** is time at which the voltage at the PDR bus returns back above 0.85pu, regardless of any possible.
  - **T<sub>10p</sub> - T<sub>clear</sub> < 5 sec**
      - **T<sub>10p</sub>** is time at which the supplied power P stays inside the +/-10% "tube" centered on the final value of P.
      - **T<sub>clear</sub>** is time at which the event is cleared.
  
  
- **Model validation**: defines the maximum deviation allowed between the curves calculated by
    Dynawo and the reference curves provided by the user. The maximum allowed thresholds are 
    defined in the tool configuration file.
    ```ini
    [GridCode]
    thr_P_mxe_before = 0.05
    thr_P_mxe_during = 0.08
    thr_P_mxe_after = 0.05
    thr_P_me_before = 0.02
    thr_P_me_during = 0.05
    thr_P_me_after = 0.02
    thr_P_mae_before = 0.03
    thr_P_mae_during = 0.07
    ...
    ```

### Changing the defaults values

By having the model validation thresholds defined in the tool configuration file, the user
can modify them if desired by editing the user configuration file (`config.ini`) located in the 
`~/.config/dycov` dir. In this file the user has all the configuration options available for the 
tool, as well as their default values.

```ini
[GridCode]
# thr_P_mxe_before = 0.05
# thr_P_mxe_during = 0.08
# thr_P_mxe_after = 0.05
# thr_P_me_before = 0.02
# thr_P_me_during = 0.05
# thr_P_me_after = 0.02
# thr_P_mae_before = 0.03
# thr_P_mae_during = 0.07
...
```

**Before modify the `thr_P_mxe_during` threshold:** 

PCS_RTE-I16z1 - Transient fault:High-impedance fault ( V = 0.5U n, 800ms )

Compliance checks on the curves, every 3 columns shown in the table show the errors for a 
specific time range nof the curve, where the first 3 columns (called MXE, ME, and MAE) 
correspond to the pre-event range, the next 3 columns to the range in which the event is happening,
and the last 3 columns correspond to the post-event range:

|      | MXE      | ME  | MAE      | MXE     | ME      | MAE      | MXE      | ME       | MAE      | Compl. |
|------|----------|-----|----------|---------|---------|----------|----------|----------|----------|--------|
| P    | 2.93e-05 | 0.0 | 1.53e-05 | 0.00246 | 0.0     | 0.000917 | 0.000178 | 0.000165 | 0.000165 | True   |
| Q    | 4.89e-05 | 0.0 | 2.95e-05 | 0.00164 | 0.0     | 0.000108 | 0.000633 | 0.0      | 8.12e-05 | True   |
| I re | 2.92e-05 | 0.0 | 1.74e-05 | 0.00219 | 0.0     | 0.00106  | 0.000155 | 0.000143 | 0.000143 | True   |
| I im | 6.38e-05 | 0.0 | 3.65e-05 | 0.0111  | 0.00188 | 0.00191  | 0.000753 | 0.000135 | 0.000135 | True   |  

In steady state after the event, the absolute average error must not exceed 1%:

| Variable | MAE      | Final Error | Compliance |
|----------|----------|-------------|------------|
| V        | 7.05e-05 | 7.05e-05    | True       |
| P        | 0.000172 | 0.000172    | True       |
| Q        | 6.87e-05 | 6.87e-05    | True       |
| I re     | 0.000142 | 0.000142    | True       |
| I im     | 0.000134 | 0.000134    | True       |


**After modify the `thr_P_mxe_during` threshold:** 

```ini
[GridCode]
# thr_P_mxe_before = 0.05
# thr_P_mxe_during = 0.08
thr_P_mxe_during = 0.002
# thr_P_mxe_after = 0.05
# thr_P_me_before = 0.02
# thr_P_me_during = 0.05
# thr_P_me_after = 0.02
# thr_P_mae_before = 0.03
# thr_P_mae_during = 0.07
...
```

PCS_RTE-I16z1 - Transient fault:High-impedance fault ( V = 0.5U n, 800ms )

Compliance checks on the curves, every 3 columns shown in the table show the errors for a 
specific time range nof the curve, where the first 3 columns (called MXE, ME, and MAE) 
correspond to the pre-event range, the next 3 columns to the range in which the event is happening,
and the last 3 columns correspond to the post-event range:

|      | MXE      | ME  | MAE      | MXE                                     | ME      | MAE      | MXE      | ME       | MAE      | Compl.                                |
|------|----------|-----|----------|-----------------------------------------|---------|----------|----------|----------|----------|---------------------------------------|
| P    | 2.93e-05 | 0.0 | 1.53e-05 | <span style="color: red">0.00246</span> | 0.0     | 0.000917 | 0.000178 | 0.000165 | 0.000165 | <span style="color: red">False</span> |
| Q    | 4.89e-05 | 0.0 | 2.95e-05 | 0.00164                                 | 0.0     | 0.000108 | 0.000633 | 0.0      | 8.12e-05 | True                                  |
| I re | 2.92e-05 | 0.0 | 1.74e-05 | 0.00219                                 | 0.0     | 0.00106  | 0.000155 | 0.000143 | 0.000143 | True                                  |
| I im | 6.38e-05 | 0.0 | 3.65e-05 | 0.0111                                  | 0.00188 | 0.00191  | 0.000753 | 0.000135 | 0.000135 | True                                  |  

In steady state after the event, the absolute average error must not exceed 1%:

| Variable | MAE      | Final Error | Compliance |
|----------|----------|-------------|------------|
| V        | 7.05e-05 | 7.05e-05    | True       |
| P        | 0.000172 | 0.000172    | True       |
| Q        | 6.87e-05 | 6.87e-05    | True       |
| I re     | 0.000142 | 0.000142    | True       |
| I im     | 0.000134 | 0.000134    | True       |


## Changing the Log Level

This section explains how to modify the configuration file to change the log level displayed 
by the tool. By default, the tool is configured to inform the user of the processes that are 
performed during execution. Next, the configuration file will be edited to display on screen 
the debugging messages that are generated when running the tool:

```ini
[Global]
#  # File Log level (CRITICAL,FATAL,ERROR,WARNING,INFO,DEBUG)
#  file_log_level = INFO
#  # Console Log level (CRITICAL,FATAL,ERROR,WARNING,INFO,DEBUG)
#  console_log_level = INFO
console_log_level = DEBUG
#  # List of SM pcs to be validated (If it's empty, all the SM pcs are validated)
#  electric_performance_verification_pcs =
#  # List of PPM pcs to be validated (If it's empty, all the PPM pcs are validated)
#  electric_performance_ppm_verification_pcs =
#  # List of BESS pcs to be validated (If it's empty, all the PPM pcs are validated)
#  electric_performance_bess_verification_pcs =
#  # List of PPM model pcs to be validated (If it's empty, all the model pcs are validated)
#  model_ppm_validation_pcs =
#  # List of BESS model pcs to be validated (If it's empty, all the model pcs are validated)
#  model_bess_validation_pcs =
```

Running the above example with the **console_log_level = DEBUG** parameter:

```
(dycov_venv) user@dynawo:~/work/MyTests$ dycov validate IEC2015ReferenceCurves -m IEC2015Dynawo -o IEC2015
2025-01-21 12:03:17,911 |                    DyCoV.Dynawo |      DEBUG |                 dynawo.py:   48 | SPOmega was compiled
2025-01-21 12:03:17,912 |                    DyCoV.Dynawo |      DEBUG |                 dynawo.py:   48 | SynchronousMachineI8SM was compiled
2025-01-21 12:03:17,915 |                DyCoV.Validation |       INFO |             validation.py:  102 | DyCoV Model Validation for Power Park Modules
2025-01-21 12:03:17,916 |                       DyCoV.PCS |      DEBUG |                    pcs.py:   62 | PCS Path /home/user/dycov_repo/dycov_venv/lib/python3.10/site-packages/dycov/templates/PCS/model/PPM/PCS_RTE-I16z1/PCSDescription.ini
2025-01-21 12:03:17,917 |                       DyCoV.PCS |      DEBUG |                    pcs.py:   71 | User PCS Path None
2025-01-21 12:03:17,926 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3
2025-01-21 12:03:17,954 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 | Model definition:
2025-01-21 12:03:17,954 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       SCR=3.0
2025-01-21 12:03:17,954 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_P=Pmax
2025-01-21 12:03:17,955 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_Q=0
2025-01-21 12:03:17,955 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_U=Udim
2025-01-21 12:03:17,955 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 | Event definition:
2025-01-21 12:03:17,956 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       connect_event_to=None
2025-01-21 12:03:17,956 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       sim_t_event_start=30.0
2025-01-21 12:03:17,956 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       fault_duration_HTB2=0.15
2025-01-21 12:03:25,379 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR10
2025-01-21 12:03:25,392 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 | Model definition:
2025-01-21 12:03:25,393 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       SCR=10.0
2025-01-21 12:03:25,393 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_P=Pmax
2025-01-21 12:03:25,393 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_Q=0
2025-01-21 12:03:25,394 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_U=Udim
2025-01-21 12:03:25,394 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 | Event definition:
2025-01-21 12:03:25,394 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       connect_event_to=None
2025-01-21 12:03:25,394 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       sim_t_event_start=30.0
2025-01-21 12:03:25,395 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       fault_duration_HTB2=0.15
2025-01-21 12:03:33,913 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3Qmin
2025-01-21 12:03:33,930 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 | Model definition:
2025-01-21 12:03:33,930 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       SCR=3.0
2025-01-21 12:03:33,930 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_P=Pmax
2025-01-21 12:03:33,930 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_Q=Qmin
2025-01-21 12:03:33,931 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_U=Udim
2025-01-21 12:03:33,931 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 | Event definition:
2025-01-21 12:03:33,931 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       connect_event_to=None
2025-01-21 12:03:33,932 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       sim_t_event_start=30.0
2025-01-21 12:03:33,932 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       fault_duration_HTB2=0.15
2025-01-21 12:03:42,638 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentBolted
2025-01-21 12:03:42,654 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 | Model definition:
2025-01-21 12:03:42,655 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       SCR=10.0
2025-01-21 12:03:42,655 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_P=Pmax
2025-01-21 12:03:42,655 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_Q=0
2025-01-21 12:03:42,655 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_U=Udim
2025-01-21 12:03:42,656 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 | Event definition:
2025-01-21 12:03:42,657 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       connect_event_to=None
2025-01-21 12:03:42,657 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       sim_t_event_start=30.0
2025-01-21 12:03:42,657 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       fault_duration_HTB2=9999.0
2025-01-21 12:03:50,924 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Rise
2025-01-21 12:03:50,934 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 | Model definition:
2025-01-21 12:03:50,934 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       SCR=10.0
2025-01-21 12:03:50,934 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_P=0.5*Pmax
2025-01-21 12:03:50,934 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_Q=Qmin
2025-01-21 12:03:50,934 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_U=0.95*Udim
2025-01-21 12:03:50,935 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 | Event definition:
2025-01-21 12:03:50,935 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       connect_event_to='AVRSetpointPu'
2025-01-21 12:03:50,935 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       sim_t_event_start=30.0
2025-01-21 12:03:50,935 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       fault_duration_HTB2=0.0
2025-01-21 12:03:50,936 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       setpoint_step_value=0.1
2025-01-21 12:03:59,228 |                 DyCoV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Drop
2025-01-21 12:03:59,238 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 | Model definition:
2025-01-21 12:03:59,238 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       SCR=10.0
2025-01-21 12:03:59,238 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_P=0.5*Pmax
2025-01-21 12:03:59,238 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_Q=Qmax
2025-01-21 12:03:59,238 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_U=1.05*Udim
2025-01-21 12:03:59,239 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 | Event definition:
2025-01-21 12:03:59,239 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       connect_event_to='AVRSetpointPu'
2025-01-21 12:03:59,239 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       sim_t_event_start=30.0
2025-01-21 12:03:59,239 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       fault_duration_HTB2=0.0
2025-01-21 12:03:59,239 |            DyCoV.ProducerCurves |      DEBUG |                 curves.py:   84 |       setpoint_step_value=-0.1
2025-01-21 12:04:07,244 |                DyCoV.Validation |      DEBUG |             validation.py:  154 | Sorted summary [Summary(id=16, zone=1, pcs='PCS_RTE-I16z1', benchmark='ThreePhaseFault', operating_condition='TransientBoltedSCR3', compliance=<Compliance.Compliant: 1>, report_name='report.RTE-I16z1.tex'), Summary(id=16, zone=1, pcs='PCS_RTE-I16z1', benchmark='ThreePhaseFault', operating_condition='TransientBoltedSCR10', compliance=<Compliance.Compliant: 1>, report_name='report.RTE-I16z1.tex'), Summary(id=16, zone=1, pcs='PCS_RTE-I16z1', benchmark='ThreePhaseFault', operating_condition='TransientBoltedSCR3Qmin', compliance=<Compliance.Compliant: 1>, report_name='report.RTE-I16z1.tex'), Summary(id=16, zone=1, pcs='PCS_RTE-I16z1', benchmark='ThreePhaseFault', operating_condition='PermanentBolted', compliance=<Compliance.Compliant: 1>, report_name='report.RTE-I16z1.tex'), Summary(id=16, zone=1, pcs='PCS_RTE-I16z1', benchmark='GridVoltageStep', operating_condition='Rise', compliance=<Compliance.NonCompliant: 2>, report_name='report.RTE-I16z1.tex'), Summary(id=16, zone=1, pcs='PCS_RTE-I16z1', benchmark='GridVoltageStep', operating_condition='Drop', compliance=<Compliance.NonCompliant: 2>, report_name='report.RTE-I16z1.tex')]
2025-01-21 12:04:07,245 |                  DyCoV.PDFLatex |      DEBUG |                 report.py:   78 | PCS: PCS_RTE-I16z1 User LaTeX path:/home/dycov/.config/dycov/templates/reports/model/PPM/PCS_RTE-I16z1
2025-01-21 12:04:07,245 |                  DyCoV.PDFLatex |      DEBUG |                 report.py:   82 | PCS: PCS_RTE-I16z1 Tool LaTeX path:/home/dycov/dycov_repo/src/dycov/templates/reports/model/PPM/PCS_RTE-I16z1
2025-01-21 12:04:07,260 |                  DyCoV.PDFLatex |      DEBUG |                 report.py:  387 | Root LaTeX path:/home/dycov/dycov_repo/src/dycov/templates/reports
2025-01-21 12:04:24,230 |                    DyCoV.Report |       INFO |                 report.py:  353 | 
Summary Report
==============

***Run on 2025-01-21 12:04 CET***
***Dynawo version: 1.7.0 (rev:master-d2a92c7)***
***Model: IEC2015Dynawo***
***Reference: IEC2015ReferenceCurves***


Pcs          Benchmark                Operating Condition      Overall Result
-----------------------------------------------------------------------------
PCS_RTE-I16z1ThreePhaseFault          TransientBoltedSCR3      Compliant
PCS_RTE-I16z1ThreePhaseFault          TransientBoltedSCR10     Compliant
PCS_RTE-I16z1ThreePhaseFault          TransientBoltedSCR3Qmin  Compliant
PCS_RTE-I16z1ThreePhaseFault          PermanentBolted          Compliant
PCS_RTE-I16z1GridVoltageStep          Rise                     Non-compliant
PCS_RTE-I16z1GridVoltageStep          Drop                     Non-compliant


2025-01-21 12:04:26,442 |                  DyCoV.PDFLatex |      DEBUG |                 report.py:  480 | 
2025-01-21 12:04:26,443 |                  DyCoV.PDFLatex |       INFO |                 report.py:  482 | PDF done.
2025-01-21 12:04:40,093 |                DyCoV.Validation |       INFO |             validation.py:   42 | Opening the report: IEC2015/Reports/report.pdf
```