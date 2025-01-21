===========================

TUTORIAL

LINUX INSTALLATION

(c) 2023&mdash;24 RTE  
Developed by Grupo AIA

===========================

--------------------------------------------------------------------------------

# Installing Dynamic Grid Compliance Verification

## Table of Contents

1. [Overview](#overview)
2. [Global Information](#global-information)
3. [Model Validation](#model-validation)
4. [Performance Verification](#performance-verification)
5. [Modify a PCS](#modify-a-pcs)
6. [Log level](#log-level)

## Overview

Dynamic Grid Compliance Verification is configured via a **config.ini** file, written in the well-known INI
format (of the [Python flavor](https://docs.python.org/3/library/configparser.html)). The location of 
this file follows the customary standard of each platform for application data:

* Under Linux: ``$HOME/.config/dgcv/``
* Under Windows: ``%APPDATA%\Local\dgcv\``

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

## Model Validation

By default all PCS's are validated when a model validation is executed:

```
(dgcv_venv) user@dynawo:~/work/MyTests$ dgcv validate IEC2015ReferenceCurves -m IEC2015Dynawo -o IEC2015
2025-01-21 11:01:28,689 |                DGCV.Validation |       INFO |             validation.py:  102 | DGCV Model Validation for Power Park Modules
2025-01-21 11:01:28,780 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3
2025-01-21 11:01:31,522 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR10
2025-01-21 11:01:33,908 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3Qmin
2025-01-21 11:01:36,426 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientHiZTc800
2025-01-21 11:01:46,092 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientHiZTc500
2025-01-21 11:01:55,916 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentBolted
2025-01-21 11:01:58,520 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentHiZ
2025-01-21 11:02:07,251 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Active
2025-01-21 11:02:09,523 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Reactive
2025-01-21 11:02:11,498 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Voltage
2025-01-21 11:02:11,532 |                    DGCV.Dynawo |    WARNING |       model_parameters.py:  352 | IECWT4BCurrentSource2015 control mode will be changed
2025-01-21 11:02:13,699 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridFreqRamp, OPER. COND.: W500mHz250ms
2025-01-21 11:02:15,869 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Rise
2025-01-21 11:02:18,224 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Drop
2025-01-21 11:02:20,849 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.USetPointStep, OPER. COND.: AReactance
2025-01-21 11:02:20,894 |                    DGCV.Dynawo |    WARNING |       model_parameters.py:  352 | IECWPP4BCurrentSource2015 control mode will be changed
2025-01-21 11:02:23,405 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.USetPointStep, OPER. COND.: BReactance
2025-01-21 11:02:23,450 |                    DGCV.Dynawo |    WARNING |       model_parameters.py:  352 | IECWPP4BCurrentSource2015 control mode will be changed
2025-01-21 11:02:25,869 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.PSetPointStep, OPER. COND.: Dec40
2025-01-21 11:02:28,580 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.PSetPointStep, OPER. COND.: Inc40
2025-01-21 11:02:31,331 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.QSetPointStep, OPER. COND.: Inc10
2025-01-21 11:02:33,765 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.QSetPointStep, OPER. COND.: Dec20
2025-01-21 11:02:36,221 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.ThreePhaseFault, OPER. COND.: TransientBolted
2025-01-21 11:02:40,185 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.GridVoltageDip, OPER. COND.: Qzero
2025-01-21 11:02:43,611 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.GridVoltageSwell, OPER. COND.: QMax
2025-01-21 11:02:46,746 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.GridVoltageSwell, OPER. COND.: QMin
2025-01-21 11:02:50,264 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z3.Islanding, OPER. COND.: DeltaP10DeltaQ4
2025-01-21 11:02:51,340 |                    DGCV.Dynawo |    WARNING |                 curves.py:  899 | Simulation Fails, logs in ../Results/Model/WindIEC2015/PCS_RTE-I16z3/Islanding/DeltaP10DeltaQ4/outputs/logs/dynawo.log
2025-01-21 11:03:22,537 |                  DGCV.PDFLatex |    WARNING |                 figure.py:  590 | All curves appear to be flat in PCS_RTE-I16z1.GridFreqRamp.W500mHz250ms; something must be wrong with the simulation
2025-01-21 11:04:02,456 |                    DGCV.Report |       INFO |                 report.py:  353 | 
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


2025-01-21 11:04:08,770 |                  DGCV.PDFLatex |       INFO |                 report.py:  482 | PDF done.
2025-01-21 11:04:29,676 |                DGCV.Validation |       INFO |             validation.py:   42 | Opening the report: IEC2015/Reports/report.pdf
```

The user can define which PCS's he wants to validate when running the tool by modifying the configuration 
file. Below is the previous example after modifying the parameter **model_ppm_validation_pcs**:

```ini
#  # List of PPM model pcs to be validated (If it's empty, all the model pcs are validated)
#  model_ppm_validation_pcs =
model_ppm_validation_pcs = PCS_RTE-I16z1
```

It can be observed in the output of the tool that only the selected PCS's have been validated.

```
(dgcv_venv) user@dynawo:~/work/MyTests$ dgcv validate IEC2015ReferenceCurves -m IEC2015Dynawo -o IEC2015
2025-01-21 11:20:13,429 |                DGCV.Validation |       INFO |             validation.py:  102 | DGCV Model Validation for Power Park Modules
2025-01-21 11:20:13,440 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3
2025-01-21 11:20:15,918 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR10
2025-01-21 11:20:18,734 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3Qmin
2025-01-21 11:20:21,327 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientHiZTc800
2025-01-21 11:20:30,859 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientHiZTc500
2025-01-21 11:20:41,049 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentBolted
2025-01-21 11:20:43,603 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentHiZ
2025-01-21 11:20:51,859 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Active
2025-01-21 11:20:54,021 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Reactive
2025-01-21 11:20:56,105 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Voltage
2025-01-21 11:20:56,117 |                    DGCV.Dynawo |    WARNING |       model_parameters.py:  352 | IECWT4BCurrentSource2015 control mode will be changed
2025-01-21 11:20:58,279 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridFreqRamp, OPER. COND.: W500mHz250ms
2025-01-21 11:21:00,421 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Rise
2025-01-21 11:21:03,066 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Drop
2025-01-21 11:21:31,562 |                  DGCV.PDFLatex |    WARNING |                 figure.py:  590 | All curves appear to be flat in PCS_RTE-I16z1.GridFreqRamp.W500mHz250ms; something must be wrong with the simulation
2025-01-21 11:21:39,383 |                    DGCV.Report |       INFO |                 report.py:  353 | 
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


2025-01-21 11:21:41,698 |                  DGCV.PDFLatex |       INFO |                 report.py:  482 | PDF done.
2025-01-21 11:21:57,007 |                DGCV.Validation |       INFO |             validation.py:   42 | Opening the report: IEC2015/Reports/report.pdf
```

## Performance Verification

As in model validation, by default all PCS are validated when a performance verification is executed:

```
(dgcv_venv) user@dynawo:~/work/MyTests$ dgcv performance -m SingleAuxI -o SingleAuxI
2025-01-21 10:34:31,341 |                DGCV.Validation |       INFO |             validation.py:   78 | Electric Performance Verification for Synchronous Machines
2025-01-21 10:34:31,387 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: AReactance
2025-01-21 10:34:31,751 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: BReactance
2025-01-21 10:34:32,059 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I3.LineTrip, OPER. COND.: 2BReactance
2025-01-21 10:34:32,344 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I4.ThreePhaseFault, OPER. COND.: TransientBolted
2025-01-21 10:34:37,033 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I6.GridVoltageDip, OPER. COND.: Qzero
2025-01-21 10:34:37,720 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I7.GridVoltageSwell, OPER. COND.: QMax
2025-01-21 10:34:47,406 |                DGCV.Validation |    WARNING |            performance.py:  142 | P has not reached steady state
2025-01-21 10:34:47,476 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I7.GridVoltageSwell, OPER. COND.: QMin
2025-01-21 10:34:48,064 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I8.LoadShedDisturbance, OPER. COND.: PmaxQzero
2025-01-21 10:34:48,335 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I10.Islanding, OPER. COND.: DeltaP10DeltaQ4
2025-01-21 10:35:03,191 |                    DGCV.Report |       INFO |                 report.py:  353 | 
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


2025-01-21 10:35:12,217 |                  DGCV.PDFLatex |       INFO |                 report.py:  482 | PDF done.
2025-01-21 10:35:12,378 |                DGCV.Validation |       INFO |             validation.py:   42 | Opening the report: SingleAuxI/Reports/report.pdf
```

The user can define which PCS's he wants to validate when running the tool by modifying the configuration 
file. Below is the previous example after modifying the parameter **electric_performance_verification_pcs**:

```ini
#  # List of SM pcs to be validated (If it's empty, all the SM pcs are validated)
#  electric_performance_verification_pcs =
electric_performance_verification_pcs = PCS_RTE-I2,PCS_RTE-I4,PCS_RTE-I8
```

It can be observed in the output of the tool that only the selected PCS's have been validated.

```
(dgcv_venv) user@dynawo:~/work/MyTests$ dgcv performance -m SingleAuxI -o SingleAuxI
2025-01-21 10:52:30,704 |                DGCV.Validation |       INFO |             validation.py:   78 | Electric Performance Verification for Synchronous Machines
2025-01-21 10:52:30,717 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: AReactance
2025-01-21 10:52:30,940 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: BReactance
2025-01-21 10:52:31,157 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I4.ThreePhaseFault, OPER. COND.: TransientBolted
2025-01-21 10:52:35,279 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I8.LoadShedDisturbance, OPER. COND.: PmaxQzero
2025-01-21 10:52:39,255 |                    DGCV.Report |       INFO |                 report.py:  353 | 
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


2025-01-21 10:52:42,402 |                  DGCV.PDFLatex |       INFO |                 report.py:  482 | PDF done.
2025-01-21 10:52:42,426 |                DGCV.Validation |       INFO |             validation.py:   42 | Opening the report: SingleAuxI/Reports/report.pdf
```

## Modify a PCS

PCS editing is only available for advanced users. The user can switch from *basic* to *advanced*
user or vice versa by overwriting the config.ini file with one of the following files:

* **config.ini_BASIC**: configuration file for *basic* users.
* **config.ini_ADVANCED**: configuration file for *advanced* users.

```
(dgcv_venv) user@dynawo:~/.config$ tree dgcv
dgcv$
├── config.ini
├── config.ini_ADVANCED
├── config.ini_BASIC
```

The **config.ini_BASIC** and **config.ini_ADVANCED** files do not contain the configuration parameters 
modified in the **config.ini** file, so it is recommended that the user rename the file to **config.ini.old** 
and modify any parameters that are desired to be kept in the new file.

```
(dgcv_venv) user@dynawo:~/.config$ mv config.ini config.ini.old
(dgcv_venv) user@dynawo:~/.config$ cp config.ini_ADVANCED config.ini
(dgcv_venv) user@dynawo:~/.config$ tree dgcv
dgcv$
├── config.ini
├── config.ini.old
├── config.ini_ADVANCED
├── config.ini_BASIC
```

The new file contains PCS configuration examples:

```ini
#  ## Example of a PCS config file
#  ##    (PCS_RTE-I2 for electrical performance)
#  ##    (PCS_RTE-I16z1 for model validation)

#  ## # Benchmark list by PCS
#  ## [PCS-Benchmarks]
#  ## PCS_RTE-I2 = USetPointStep
#  ## PCS_RTE-I3 = LineTrip
#  ## PCS_RTE-I4 = ThreePhaseFault
#  ## PCS_RTE-I5 = ThreePhaseFault
#  ## PCS_RTE-I6 = GridVoltageDip
#  ## PCS_RTE-I7 = GridVoltageSwell
#  ## PCS_RTE-I8 = LoadShedDisturbance
#  ## PCS_RTE-I10 = Islanding
#  ## PCS_RTE-I16z1 = ThreePhaseFault,SetPointStep,GridFreqRamp,GridVoltageStep
#  ## PCS_RTE-I16z3 = USetPointStep,PSetPointStep,QSetPointStep,ThreePhaseFault,GridVoltageDip,GridVoltageSwell,Islanding

#  ## # Operating conditions list by PCS-Benchmark
#  ## [PCS-OperatingConditions]
#  ## PCS_RTE-I2.USetPointStep = AReactance,BReactance
#  ## PCS_RTE-I3.LineTrip = 2BReactance
#  ## PCS_RTE-I4.ThreePhaseFault = TransientBolted
#  ## PCS_RTE-I5.ThreePhaseFault = TransientBolted
#  ## PCS_RTE-I6.GridVoltageDip = Qzero
#  ## PCS_RTE-I7.GridVoltageSwell = QMax,QMin
#  ## PCS_RTE-I10.Islanding = DeltaP10DeltaQ4
#  ## PCS_RTE-I16z1.ThreePhaseFault = TransientBoltedSCR3,TransientBoltedSCR10,TransientBoltedSCR3Qmin,TransientHiZTc800,TransientHiZTc500,PermanentBolted,PermanentHiZ
#  ## PCS_RTE-I16z1.SetPointStep = Active,Reactive,Voltage
#  ## PCS_RTE-I16z1.GridFreqRamp = W500mHz250ms
#  ## PCS_RTE-I16z1.GridVoltageStep = Rise,Drop
#  ## PCS_RTE-I16z3.USetPointStep = AReactance,BReactance
#  ## PCS_RTE-I16z3.PSetPointStep = Dec40,Inc40
#  ## PCS_RTE-I16z3.QSetPointStep = Dec20,Inc10
#  ## PCS_RTE-I16z3.ThreePhaseFault = TransientBolted
#  ## PCS_RTE-I16z3.GridVoltageDip = Qzero
#  ## PCS_RTE-I16z3.GridVoltageSwell = QMax,QMin
#  ## PCS_RTE-I16z3.Islanding = DeltaP10DeltaQ4
```

Taking as a starting point the last example of model validation, where only the PCS **PCS_RTE-I16z1** 
was validated, the benchmarks to be validated will be modified, as well as some Operating conditions.

First, the settings are recovered from the *config.ini* file if the file has been overwritten:

```ini
#  # List of PPM model pcs to be validated (If it's empty, all the model pcs are validated)
#  model_ppm_validation_pcs =
model_ppm_validation_pcs = PCS_RTE-I16z1
```

Below, only the benchmarks called *ThreePhaseFault* and *GridVoltageStep* are validated::

```ini
#  ## # Benchmark list by PCS
#  ## [PCS-Benchmarks]
[PCS-Benchmarks]
#  ## PCS_RTE-I16z1.ThreePhaseFault = TransientBoltedSCR3,TransientBoltedSCR10,TransientBoltedSCR3Qmin,TransientHiZTc800,TransientHiZTc500,PermanentBolted,PermanentHiZ
PCS_RTE-I16z1.ThreePhaseFault = TransientBoltedSCR3,TransientBoltedSCR10,TransientBoltedSCR3Qmin,PermanentBolted
```

And finally, the *ThreePhaseFault* benchmark does not want to validate the operating conditions called *HiZ*:

```ini
#  ## # Operating conditions list by PCS-Benchmark
#  ## [PCS-OperatingConditions]
[PCS-OperatingConditions]
#  ## PCS_RTE-I16z1 = ThreePhaseFault,SetPointStep,GridFreqRamp,GridVoltageStep
PCS_RTE-I16z1 = ThreePhaseFault,GridVoltageStep
```

The result of running the tool only has the PCS, benchmarks and operating conditions configured.

```
(dgcv_venv) user@dynawo:~/work/MyTests$ dgcv validate IEC2015ReferenceCurves -m IEC2015Dynawo -o IEC2015
2025-01-21 12:00:08,479 |                DGCV.Validation |       INFO |             validation.py:  102 | DGCV Model Validation for Power Park Modules
2025-01-21 12:00:08,513 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3
2025-01-21 12:00:13,667 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR10
2025-01-21 12:00:16,338 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3Qmin
2025-01-21 12:00:19,777 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentBolted
2025-01-21 12:00:22,939 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Rise
2025-01-21 12:00:25,543 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Drop
2025-01-21 12:00:51,997 |                    DGCV.Report |       INFO |                 report.py:  353 | 
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


2025-01-21 12:00:55,848 |                  DGCV.PDFLatex |       INFO |                 report.py:  482 | PDF done.
2025-01-21 12:00:57,018 |                DGCV.Validation |       INFO |             validation.py:   42 | Opening the report: IEC2015/Reports/report.pdf
```

The **modify_pcs.md** tutorial explains how to modify the parameters that define a PCS, 
Benchmark and/or Operating condition.


## Log Level

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
(dgcv_venv) user@dynawo:~/work/MyTests$ dgcv validate IEC2015ReferenceCurves -m IEC2015Dynawo -o IEC2015
2025-01-21 12:03:17,911 |                    DGCV.Dynawo |      DEBUG |                 dynawo.py:   48 | SPNumcc was compiled
2025-01-21 12:03:17,911 |                    DGCV.Dynawo |      DEBUG |                 dynawo.py:   48 | TransformerTapChanger was compiled
2025-01-21 12:03:17,911 |                    DGCV.Dynawo |      DEBUG |                 dynawo.py:   48 | SPOmega was compiled
2025-01-21 12:03:17,912 |                    DGCV.Dynawo |      DEBUG |                 dynawo.py:   48 | SynchronousMachineI8SM was compiled
2025-01-21 12:03:17,915 |                DGCV.Validation |       INFO |             validation.py:  102 | DGCV Model Validation for Power Park Modules
2025-01-21 12:03:17,916 |                       DGCV.PCS |      DEBUG |                    pcs.py:   62 | PCS Path /home/user/dgcv_repo/dgcv_venv/lib/python3.10/site-packages/dgcv/templates/PCS/model/PPM/PCS_RTE-I16z1/PCSDescription.ini
2025-01-21 12:03:17,917 |                       DGCV.PCS |      DEBUG |                    pcs.py:   71 | User PCS Path None
2025-01-21 12:03:17,926 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3
2025-01-21 12:03:17,954 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 | Model definition:
2025-01-21 12:03:17,954 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       SCR=3.0
2025-01-21 12:03:17,954 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_P=Pmax
2025-01-21 12:03:17,955 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_Q=0
2025-01-21 12:03:17,955 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_U=Udim
2025-01-21 12:03:17,955 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 | Event definition:
2025-01-21 12:03:17,956 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       connect_event_to=None
2025-01-21 12:03:17,956 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       sim_t_event_start=30.0
2025-01-21 12:03:17,956 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       fault_duration_HTB2=0.15
2025-01-21 12:03:25,379 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR10
2025-01-21 12:03:25,392 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 | Model definition:
2025-01-21 12:03:25,393 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       SCR=10.0
2025-01-21 12:03:25,393 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_P=Pmax
2025-01-21 12:03:25,393 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_Q=0
2025-01-21 12:03:25,394 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_U=Udim
2025-01-21 12:03:25,394 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 | Event definition:
2025-01-21 12:03:25,394 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       connect_event_to=None
2025-01-21 12:03:25,394 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       sim_t_event_start=30.0
2025-01-21 12:03:25,395 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       fault_duration_HTB2=0.15
2025-01-21 12:03:33,913 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3Qmin
2025-01-21 12:03:33,930 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 | Model definition:
2025-01-21 12:03:33,930 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       SCR=3.0
2025-01-21 12:03:33,930 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_P=Pmax
2025-01-21 12:03:33,930 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_Q=Qmin
2025-01-21 12:03:33,931 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_U=Udim
2025-01-21 12:03:33,931 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 | Event definition:
2025-01-21 12:03:33,931 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       connect_event_to=None
2025-01-21 12:03:33,932 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       sim_t_event_start=30.0
2025-01-21 12:03:33,932 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       fault_duration_HTB2=0.15
2025-01-21 12:03:42,638 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentBolted
2025-01-21 12:03:42,654 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 | Model definition:
2025-01-21 12:03:42,655 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       SCR=10.0
2025-01-21 12:03:42,655 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_P=Pmax
2025-01-21 12:03:42,655 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_Q=0
2025-01-21 12:03:42,655 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_U=Udim
2025-01-21 12:03:42,656 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 | Event definition:
2025-01-21 12:03:42,657 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       connect_event_to=None
2025-01-21 12:03:42,657 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       sim_t_event_start=30.0
2025-01-21 12:03:42,657 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       fault_duration_HTB2=9999.0
2025-01-21 12:03:50,924 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Rise
2025-01-21 12:03:50,934 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 | Model definition:
2025-01-21 12:03:50,934 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       SCR=10.0
2025-01-21 12:03:50,934 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_P=0.5*Pmax
2025-01-21 12:03:50,934 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_Q=Qmin
2025-01-21 12:03:50,934 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_U=0.95*Udim
2025-01-21 12:03:50,935 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 | Event definition:
2025-01-21 12:03:50,935 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       connect_event_to='AVRSetpointPu'
2025-01-21 12:03:50,935 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       sim_t_event_start=30.0
2025-01-21 12:03:50,935 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       fault_duration_HTB2=0.0
2025-01-21 12:03:50,936 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       setpoint_step_value=0.1
2025-01-21 12:03:59,228 |                 DGCV.Benchmark |       INFO |              benchmark.py:  545 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Drop
2025-01-21 12:03:59,238 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 | Model definition:
2025-01-21 12:03:59,238 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       SCR=10.0
2025-01-21 12:03:59,238 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_P=0.5*Pmax
2025-01-21 12:03:59,238 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_Q=Qmax
2025-01-21 12:03:59,238 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       pdr_U=1.05*Udim
2025-01-21 12:03:59,239 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 | Event definition:
2025-01-21 12:03:59,239 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       connect_event_to='AVRSetpointPu'
2025-01-21 12:03:59,239 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       sim_t_event_start=30.0
2025-01-21 12:03:59,239 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       fault_duration_HTB2=0.0
2025-01-21 12:03:59,239 |            DGCV.ProducerCurves |      DEBUG |                 curves.py:   84 |       setpoint_step_value=-0.1
2025-01-21 12:04:07,244 |                DGCV.Validation |      DEBUG |             validation.py:  154 | Sorted summary [Summary(id=16, zone=1, pcs='PCS_RTE-I16z1', benchmark='ThreePhaseFault', operating_condition='TransientBoltedSCR3', compliance=<Compliance.Compliant: 1>, report_name='report.RTE-I16z1.tex'), Summary(id=16, zone=1, pcs='PCS_RTE-I16z1', benchmark='ThreePhaseFault', operating_condition='TransientBoltedSCR10', compliance=<Compliance.Compliant: 1>, report_name='report.RTE-I16z1.tex'), Summary(id=16, zone=1, pcs='PCS_RTE-I16z1', benchmark='ThreePhaseFault', operating_condition='TransientBoltedSCR3Qmin', compliance=<Compliance.Compliant: 1>, report_name='report.RTE-I16z1.tex'), Summary(id=16, zone=1, pcs='PCS_RTE-I16z1', benchmark='ThreePhaseFault', operating_condition='PermanentBolted', compliance=<Compliance.Compliant: 1>, report_name='report.RTE-I16z1.tex'), Summary(id=16, zone=1, pcs='PCS_RTE-I16z1', benchmark='GridVoltageStep', operating_condition='Rise', compliance=<Compliance.NonCompliant: 2>, report_name='report.RTE-I16z1.tex'), Summary(id=16, zone=1, pcs='PCS_RTE-I16z1', benchmark='GridVoltageStep', operating_condition='Drop', compliance=<Compliance.NonCompliant: 2>, report_name='report.RTE-I16z1.tex')]
2025-01-21 12:04:07,245 |                  DGCV.PDFLatex |      DEBUG |                 report.py:   78 | PCS: PCS_RTE-I16z1 User LaTeX path:/home/dgcv/.config/dgcv/templates/reports/model/PPM/PCS_RTE-I16z1
2025-01-21 12:04:07,245 |                  DGCV.PDFLatex |      DEBUG |                 report.py:   82 | PCS: PCS_RTE-I16z1 Tool LaTeX path:/home/dgcv/dgcv_repo/src/dgcv/templates/reports/model/PPM/PCS_RTE-I16z1
2025-01-21 12:04:07,260 |                  DGCV.PDFLatex |      DEBUG |                 report.py:  387 | Root LaTeX path:/home/dgcv/dgcv_repo/src/dgcv/templates/reports
2025-01-21 12:04:24,230 |                    DGCV.Report |       INFO |                 report.py:  353 | 
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


2025-01-21 12:04:26,442 |                  DGCV.PDFLatex |      DEBUG |                 report.py:  480 | 
2025-01-21 12:04:26,443 |                  DGCV.PDFLatex |       INFO |                 report.py:  482 | PDF done.
2025-01-21 12:04:40,093 |                DGCV.Validation |       INFO |             validation.py:   42 | Opening the report: IEC2015/Reports/report.pdf
```