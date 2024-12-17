===========================

TUTORIAL

GENERAL USAGE

(c) 2023&mdash;24 RTE  
Developed by Grupo AIA

===========================

--------------------------------------------------------------------------------

#### Table of Contents

1. [First run](#first-run)
2. [Configuration](#configuration)
3. [Results directory](#results-directory)
4. [Running with debug on](#running-with-debug-on)
5. [The Producer files](#the-producer-files)
6. [The Reference curves](#the-reference-curves)
7. [The Producer curves](#the-producer-curves)
8. [Inputs template](#inputs-template)
9. [Log file and console messages](#log-file-and-console-messages)

--------------------------------------------------------------------------------

# First run

## Assumptions

For the first run of the tool we will assume that:

* Dynawo v1.7.x (Release) already installed
  ```
  user@dynawo:~$ which dynawo.sh
  /opt/dynawo/dynawo.sh
  user@dynawo:~$ dynawo.sh version
  1.7.0 (rev:master-311b916)
  ``` 

* DGCV (dgcv) Tool already installed
  ```
  user@dynawo:~/work/repo_dgcv$ git status
  On branch main
  Your branch is up to date with 'origin/main'.

  nothing to commit, working tree clean
  ``` 

* Python venv activated
  ```
  user@dynawo:~/work/repo_dgcv$ source dgcv_venv/bin/activate
  (dgcv_venv) user@dynawo:~/work/repo_dgcv$
  ``` 

* Fresh start, there is no `~/.config/dgcv` created yet
  ```
  user@dynawo:~/work/repo_dgcv$ ls -al ~/.config/dgcv
  ls: cannot access '/home/user/.config/dgcv': No such file or directory
  ``` 

## Executables

The tool currently has different entry points, at this point we will briefly 
describe each entry point.

### Electric performance verification (for Synchronous Machines):

In this mode the tool runs an execution pipeline consisting in a set of pre-defined 
tests for _Synchronous Machines_, those of _Fiches_ "I" in RTE's DTR.

``` 
(dgcv_venv) user@dynawo:~/work/repo_dgcv$ dgcv performance -h
usage: dgcv performance [-h] [-d] [-l LAUNCHER_DWO] [-m PRODUCER_MODEL]
                    [-c PRODUCER_CURVES] [-p PCS] [-o RESULTS_DIR] [-od]

options:
  -h, --help            show this help message and exit
  -d, --debug           more debug messages
  -l LAUNCHER_DWO, --launcher_dwo LAUNCHER_DWO
                        enter the path to the Dynawo launcher
  -m PRODUCER_MODEL, --producer_model PRODUCER_MODEL
                        enter the path to the folder containing the
                        producer_model files (DYD, PAR, INI)
  -c PRODUCER_CURVES, --producer_curves PRODUCER_CURVES
                        enter the path to the folder containing the curves for
                        the Performance Checking Sheet (PCS)
  -p PCS, --pcs PCS     enter one Performance Checking Sheet (PCS) to validate
  -o RESULTS_DIR, --results_dir RESULTS_DIR
                        enter the path to the results dir
  -od, --only_dtr       validate using only the PCS defined in the DTR
```

Note that, in this mode, the tool can perform the electrical performance
verification using either a user-provided dynawo **model** (running Dynawo
simulations), or a set of user-provided **curves**, or both (in which case 
the curves are used only for showing them on the graphs, along the simulated
curves). Therefore, you must provide either a *PRODUCER_MODEL* or a
*PRODUCER_CURVE* directory, or both.

### Electric performance verification (for Power Park Modules):

In this mode the tool runs an execution pipeline consisting of a set of pre-defined 
tests for _Power Park Modules_, those of _Fiches_ "I" in RTE's DTR.

``` 
(dgcv_venv) user@dynawo:~/work/repo_dgcv$ dgcv performance -h
usage: dgcv performance [-h] [-d] [-l LAUNCHER_DWO] [-m PRODUCER_MODEL]
                     [-c PRODUCER_CURVES] [-p PCS] [-o RESULTS_DIR] [-od]

options:
  -h, --help            show this help message and exit
  -d, --debug           more debug messages
  -l LAUNCHER_DWO, --launcher_dwo LAUNCHER_DWO
                        enter the path to the Dynawo launcher
  -m PRODUCER_MODEL, --producer_model PRODUCER_MODEL
                        enter the path to the folder containing the
                        producer_model files (DYD, PAR, INI)
  -c PRODUCER_CURVES, --producer_curves PRODUCER_CURVES
                        enter the path to the folder containing the curves for
                        the Performance Checking Sheet (PCS)
  -p PCS, --pcs PCS     enter one Performance Checking Sheet (PCS) to validate
  -o RESULTS_DIR, --results_dir RESULTS_DIR
                        enter the path to the results dir
  -od, --only_dtr       validate using only the PCS defined in the DTR

```

Note that, in this mode, the tool can perform the electrical performance
verification using either a user-provided dynawo **model** (running Dynawo
simulations), or a set of user-provided **curves**, or both (in which case the
curves are used only for showing them on the graphs, along the simulated
curves). Therefore, you must provide either a *PRODUCER_MODEL* or a
*PRODUCER_CURVE* directory, or both.

### RMS model validation of PPMs:

In this mode the tool runs an execution pipeline consisting in a set of pre-defined 
tests for _Power Park Modules_, those of _Fiches_ "X" in RTE's DTR.

``` 
(dgcv_venv) user@dynawo:~/work/repo_dgcv$ dgcv validate -h
usage: dgcv validate [-h] [-d] [-l LAUNCHER_DWO]
                     [-m PRODUCER_MODEL | -c PRODUCER_CURVES] [-p PCS]
                     [-o RESULTS_DIR] [-od]
                     [reference_curves]

positional arguments:
  reference_curves      enter the path to the folder containing the reference
                        curves for the Performance Checking Sheet (PCS)

options:
  -h, --help            show this help message and exit
  -d, --debug           more debug messages
  -l LAUNCHER_DWO, --launcher_dwo LAUNCHER_DWO
                        enter the path to the Dynawo launcher
  -m PRODUCER_MODEL, --producer_model PRODUCER_MODEL
                        enter the path to the folder containing the
                        producer_model files (DYD, PAR, INI)
  -c PRODUCER_CURVES, --producer_curves PRODUCER_CURVES
                        enter the path to the folder containing the curves for
                        the Performance Checking Sheet (PCS)
  -p PCS, --pcs PCS     enter one Performance Checking Sheet (PCS) to validate
  -o RESULTS_DIR, --results_dir RESULTS_DIR
                        enter the path to the results dir
  -od, --only_dtr       validate using only the PCS defined in the DTR
```

## Also available, but won’t be further discussed here

### Model compilation of custom Dynawo assembled models:

Note: compilation of internally-defined assembled models is invoked automatically

``` 
(dgcv_venv) user@dynawo:~/work/repo_dgcv$ dgcv compile -h
usage: dgcv compile [-h] [-d] [-l LAUNCHER_DWO] [-m DYNAWO_MODEL] [-f]

Use this command to compile a new Modelica model that you may want to use in your DYD files. If invoked with no model, it makes sure that *all* currently defined Modelica models (the tool's own and the user's, which live under $DGCV_CONFIG/user_models/) are compiled. Therefore it should be run upon first install.

options:
  -h, --help            show this help message and exit
  -d, --debug           more debug messages
  -l LAUNCHER_DWO, --launcher_dwo LAUNCHER_DWO
                        enter the path to the Dynawo launcher
  -m DYNAWO_MODEL, --dynawo_model DYNAWO_MODEL
                        XML file describing a custom Modelica model
  -f, --force           force the recompilation of all Modelica models (the
                        user's and the tool's own)
```

### Generation of Producer Inputs:

It’s an interactive helper tool to aid the user in constructing the 
DYD/PAR/INI files for input to the tool. For now, there is the generate 
option:

``` 
(dgcv_venv) user@dynawo:~/work/repo_dgcv$ dgcv generate -h
usage: dgcv generate [-h] [-d] [-l LAUNCHER_DWO] -o RESULTS_DIR -t {S,S+i,S+Aux,S+Aux+i,M,M+i,M+Aux,M+Aux+i} -v {performance_SM,performance_PPM,model}

options:
  -h, --help            show this help message and exit
  -d, --debug           more debug messages
  -l LAUNCHER_DWO, --launcher_dwo LAUNCHER_DWO
                        enter the path to the Dynawo launcher
  -o RESULTS_DIR, --results_dir RESULTS_DIR
                        enter the path to the results dir
  -t {S,S+i,S+Aux,S+Aux+i,M,M+i,M+Aux,M+Aux+i}, --topology {S,S+i,S+Aux,S+Aux+i,M,M+i,M+Aux,M+Aux+i}
                        enter the desired topology to implement in the DYD file
  -v {performance_SM,performance_PPM,model}, --validation {performance_SM,performance_PPM,model}
                        enter the validation type
```

### Curve Anonymizer:

In this mode the tool generates a set of curves with generic names from 
the input curves to which a noise signal is added.

```
(dgcv_venv) user@dynawo:~/work/repo_dgcv$ dgcv anonymize -h
usage: dgcv anonymize [-h] [-d] [-c PRODUCER_CURVES] [-o RESULTS_DIR]
	                      [-n NOISESTD] [-f FREQUENCY]
	
optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           more debug messages
  -c PRODUCER_CURVES, --producer_curves PRODUCER_CURVES
	                        enter the path to the folder containing the curves for
	                        the Performance Checking Sheet (PCS)
  -o RESULTS_DIR, --results_dir RESULTS_DIR
                        enter the path to the results dir
  -n NOISESTD, --noisestd NOISESTD
                        enter the standard deviation used to to anonymize the
                        curves (recommended value: [0.01, 0.1])
  -f FREQUENCY, --frequency FREQUENCY
                        enter the frequency used for the lowpass filter
```

## Firsts test

The easiest way to start using the tool is to copy one or more of the available examples.
``` 
(dgcv_venv) user@dynawo:~$ mkdir work/MyTests/
(dgcv_venv) user@dynawo:~$ cd work
(dgcv_venv) user@dynawo:~/work$ cp -a ~/work/repo_dgcv/examples/SM/Dynawo/* MyTests
(dgcv_venv) user@dynawo:~/work$ tree MyTests
MyTests
├── Single
│   ├── Producer.dyd
│   ├── Producer.ini
│   └── Producer.par
├── SingleAux
│   ├── Producer.dyd
│   ├── Producer.ini
│   └── Producer.par
├── SingleAuxI
│   ├── Producer.dyd
│   ├── Producer.ini
│   └── Producer.par
└── SingleI
    ├── Producer.dyd
    ├── Producer.ini
    └── Producer.par
```

Each entry point to the tool has parameters to customize its execution, below 
are the parameters for the `dgcv performance` executable:

``` 
(dgcv_venv) user@dynawo:~/work/repo_dgcv$ dgcv performance -h
usage: dgcv performance [-h] [-d] [-l LAUNCHER_DWO] [-m PRODUCER_MODEL] [-c PRODUCER_CURVES] [-p PCS] [-o RESULTS_DIR] [-od]

options:
  -h, --help            show this help message and exit
  -d, --debug           more debug messages
  -l LAUNCHER_DWO, --launcher_dwo LAUNCHER_DWO
                        enter the path to the Dynawo launcher
  -m PRODUCER_MODEL, --producer_model PRODUCER_MODEL
                        enter the path to the folder containing the producer_model files (DYD, PAR, INI)
  -c PRODUCER_CURVES, --producer_curves PRODUCER_CURVES
                        enter the path to the folder containing the curves for the Performance Checking Sheet (PCS)
  -p PCS, --pcs PCS     enter one Performance Checking Sheet (PCS) to validate
  -o RESULTS_DIR, --results_dir RESULTS_DIR
                        enter the path to the results dir
  -od, --only_dtr       validate using only the PCS defined in the DTR
```

* **-h, --help**: 
  Displays the help message with all the configuration parameters available 
  for the selected command.

* **-d, --debug**: 
  This parameter increases the information offered to the user about the execution 
  of the command (it will be described in more detail later).

* **-l, --launcher_dwo**: 
  This parameter allows the user to select the Dynawo executable that will be used 
  to simulate the producer model, if given. If the parameter is ignored, the executable 
  configured by default in the user's PATH will be used. 

* **-m, --producer_model**: 
  Path where the DYD, PAR and INI files that make up the producer's Dynawo model 
  are located. Both this parameter and the producer curves parameter (described below) 
  are optional, but it is mandatory that at least one of the two be present. There 
  are exceptions with certain parameters, whose objective is not to execute validation 
  tests, but rather to get help in using the command or to obtain help in creating its inputs.

* **-c, --producer_curves**: 
  Path where the directory structure with the producer curves are located. Both this 
  parameter and the producer model parameter (described above) are optional, but it
  is mandatory that at least one of the two be present. There are exceptions with
  certain parameters, whose objective is not to execute validation tests, but rather to 
  get help in using the command or to obtain help in creating its inputs.

* **-p, --pcs**: 
  This parameter allows you to limit the tests that will be validated to a single 
  Performance Checking Sheet (*PCS*). 

* **-o, --results_dir**: 
  This parameter allows the user to set the path where the tool will save the 
  execution results. If no specific path is declared for the results, a new *Results* 
  directory will be created in the producer model path, or in the path of the producer
  curves if there is no producer model, to save the results of the execution.

* **-od, --only_dtr**: 
  It allows yo to run the pipeline validating only the PCS defined in the DTR.

  
Note: Regarding the `dgcv performance` executable it has exactly the same 
parameters described, while for the `dgcv validate` executable the parameters 
**--producer_model** and **--producer_curves** are mandatory, for this reason 
they become positional arguments.



The parameters of the executable `dgcv compile` are:

``` 
(dgcv_venv) user@dynawo:~/work/repo_dgcv$ dgcv compile -h
usage: dgcv compile [-h] [-d] [-l LAUNCHER_DWO] [-m DYNAWO_MODEL] [-f]

Use this command to compile a new Modelica model that you may want to use in your DYD files. If invoked with no model, it makes sure that *all* currently defined Modelica models (the tool's own and the user's, which live under $DGCV_CONFIG/user_models/) are compiled. Therefore it should be run upon first install.

options:
  -h, --help            show this help message and exit
  -d, --debug           more debug messages
  -l LAUNCHER_DWO, --launcher_dwo LAUNCHER_DWO
                        enter the path to the Dynawo launcher
  -m DYNAWO_MODEL, --dynawo_model DYNAWO_MODEL
                        XML file describing a custom Modelica model
  -f, --force           force the recompilation of all Modelica models (the user's and the tool's own)
```

* **-m, --dynawo_model**: 
  This parameter is used to force the compilation of a specific Dynawo dynamic model, 
  all other dynamic models will be ignored whether they are previously compiled or not.

* **-f, --force**: 
  This parameter forces the compilation of all dynamic models, both the dynamic models 
  created by the user in the relevant path, and the dynamic models of the tool. This 
  configuration parameter is exclusive, so if it is used, the rest of the parameters 
  must be ignored.

* **-h, --help**: 
  Displays the help message with all the configuration parameters available for the 
  selected command.

* **-l, --launcher_dwo**: 
  This parameter allows the user to select the Dynawo executable that will be used to 
  simulate the producer model, if given. If the parameter is ignored, the executable 
  configured by default in the user's PATH will be used. 

* **-d, --debug**: 
  This parameter increases the information offered to the user about the execution 
  of the command (it will be described in more detail later).


And run one of the copied examples:
* The first-time pre-compilation is automatically launched 
  (6 assembled models used internally by the tool).
* You can also re-compile at any time using `compile_dynawo_models`.
* The console displays the current state of the tool execution in messages.
* Once the execution is finished, a final report is automatically 
  opened with the summary of the execution and all the individual reports 
  of the tests carried out.

Note: console output also goes into the logfile, *dgcv.log*.

An example of the console output:

``` 
(dgcv_venv) user@dynawo:~/work/MyTests$ dgcv performance -m SingleAuxI
2024-02-01 11:52:16,161 |            DGCV.Dynawo |    INFO |            dynawo.py:117 | Precompile SetPointOmega.xml
2024-02-01 11:52:16,164 |            DGCV.Dynawo |    INFO |            dynawo.py:152 | cd /home/user/work/repo_dgcv/src/dgcv/model_lib/modelica_models && /opt/dynawo/dynawo.sh jobs --generate-preassembled --model-list SetPointOmega.xml --non-recursive-modelica-models-dir . --output-dir /home/user/.config/dgcv/ddb
2024-02-01 11:52:39,151 |            DGCV.Dynawo |    INFO |            dynawo.py:117 | Precompile 4AWeccCurrentSource.xml
2024-02-01 11:52:39,153 |            DGCV.Dynawo |    INFO |            dynawo.py:152 | cd /home/user/work/repo_dgcv/src/dgcv/model_lib/modelica_models && /opt/dynawo/dynawo.sh jobs --generate-preassembled --model-list WT4AWeccCurrentSource.xml --non-recursive-modelica-models-dir . --output-dir /home/user/.config/dgcv/ddb
2024-02-01 11:53:35,949 |            DGCV.Dynawo |    INFO |            dynawo.py:117 | Precompile WT4BWeccCurrentSource.xml
2024-02-01 11:53:35,950 |            DGCV.Dynawo |    INFO |            dynawo.py:152 | cd /home/user/work/repo_dgcv/src/dgcv/model_lib/modelica_models && /opt/dynawo/dynawo.sh jobs --generate-preassembled --model-list WT4BWeccCurrentSource.xml --non-recursive-modelica-models-dir . --output-dir /home/user/.config/dgcv/ddb
2024-02-01 11:54:32,140 |            DGCV.Dynawo |    INFO |            dynawo.py:117 | Precompile TransformerTapChanger.xml
2024-02-01 11:54:32,141 |            DGCV.Dynawo |    INFO |            dynawo.py:152 | cd /home/user/work/repo_dgcv/src/dgcv/model_lib/modelica_models && /opt/dynawo/dynawo.sh jobs --generate-preassembled --model-list TransformerTapChanger.xml --non-recursive-modelica-models-dir . --output-dir /home/user/.config/dgcv/ddb
2024-02-01 11:55:11,153 |            DGCV.Dynawo |    INFO |            dynawo.py:117 | Precompile SynchronousMachineI8SM.xml
2024-02-01 11:55:11,154 |            DGCV.Dynawo |    INFO |            dynawo.py:152 | cd /home/user/work/repo_dgcv/src/dgcv/model_lib/modelica_models && /opt/dynawo/dynawo.sh jobs --generate-preassembled --model-list SynchronousMachineI8SM.xml --non-recursive-modelica-models-dir . --output-dir /home/user/.config/dgcv/ddb
2024-02-01 11:56:06,142 |            DGCV.Dynawo |    INFO |            dynawo.py:117 | Precompile SetPointNumcc.xml
2024-02-01 11:56:06,143 |            DGCV.Dynawo |    INFO |            dynawo.py:152 | cd /home/user/work/repo_dgcv/src/dgcv/model_lib/modelica_models && /opt/dynawo/dynawo.sh jobs --generate-preassembled --model-list SetPointNumcc.xml --non-recursive-modelica-models-dir . --output-dir /home/user/.config/dgcv/ddb
2024-02-01 11:56:27,637 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I4.ThreePhaseFault, OPER. COND.: TransientBolted
2024-02-01 11:56:40,688 |          DGCV.PDFLatex |    INFO |            report.py:180 | PDF Done
2024-02-01 11:56:40,744 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I10.Islanding, OPER. COND.: DeltaP10DeltaQ4
2024-02-01 11:56:45,994 |          DGCV.PDFLatex |    INFO |            report.py:180 | PDF Done
2024-02-01 11:56:46,001 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I3.LineTrip, OPER. COND.: 2BReactance
2024-02-01 11:56:52,288 |          DGCV.PDFLatex |    INFO |            report.py:180 | PDF Done
2024-02-01 11:56:52,294 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: AReactance
2024-02-01 11:56:52,562 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: BReactance
2024-02-01 11:56:59,087 |          DGCV.PDFLatex |    INFO |            report.py:180 | PDF Done
2024-02-01 11:56:59,108 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I6.GridVoltageDip, OPER. COND.: Qzero
2024-02-01 11:57:04,844 |          DGCV.PDFLatex |    INFO |            report.py:180 | PDF Done
2024-02-01 11:57:04,850 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I7.GridVoltageSwell, OPER. COND.: QMax
2024-02-01 11:57:10,363 |        DGCV.Validation | WARNING |       performance.py:119 | P has not reached steady state
2024-02-01 11:57:10,440 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I7.GridVoltageSwell, OPER. COND.: QMin
2024-02-01 11:57:17,621 |          DGCV.PDFLatex |    INFO |            report.py:180 | PDF Done
2024-02-01 11:57:17,652 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I8.LoadShedDisturbance, OPER. COND.: PmaxQzero
2024-02-01 11:57:23,223 |          DGCV.PDFLatex |    INFO |            report.py:180 | PDF Done
```

The final report is made up of:

* A brief summary of the result obtained in each test

![Final Report](pngs/final_report.png)

* And a detailed report of each test

![Test Report](pngs/final_report2.png)


Each detailed report is divided into 4 sections:

* Overview: explanation of the case to be tested

![Overview](pngs/overview.png)

* Simulation: Presentation of the most representative curves for the test.

![Simulation](pngs/simulation.png)

* Analysis of results: Presentation of the values that are checked to 
  validate the test.

![Analysis of results](pngs/results.png)

* Compliance checks: Table with the compliance controls that the test 
  must pass to validate the producer's model.

![Compliance checks](pngs/compliance.png)



# Configuration

## The structure of the `~/.config/dgcv` dir

A directory is created after the first run of the tool, it is designed 
both to allow the user to modify the tool configuration 
(`~/.config/dgcv/config.ini`) and to expand the dynamic models available 
for simulation with Dynawo (`~/.config/dgcv/user_models`). 

The `~/.config/dgcv/` directory is structured in:

```
(dgcv_venv) user@dynawo:~/.config$ tree dgcv
dgcv$
├── config.ini
├── config.ini_ADVANCED
├── config.ini_BASIC
├── ddb
│   ├── compile.log
│   ├── dgcv.log
│   ├── SPNumcc
│   ├── SPNumcc.mo
│   ├── SPNumcc.so
│   ├── SPOmega
│   ├── SPOmega.extvar
│   ├── SPOmega.mo
│   ├── SPOmega.so
│   ├── SynchronousMachineI8SM
│   ├── SynchronousMachineI8SM.extvar
│   ├── SynchronousMachineI8SM_INIT.mo
│   ├── SynchronousMachineI8SM.mo
│   ├── SynchronousMachineI8SM.so
│   ├── TransformerTapChanger
│   ├── TransformerTapChanger.extvar
│   ├── TransformerTapChanger_INIT.mo
│   ├── TransformerTapChanger.mo
│   └── TransformerTapChanger.so
├── log
│   └── dgcv.log
├── templates
│   ├── PCS
│   │   ├── model
│   │   │   └── PPM
│   │   ├── performance
│   │   │   ├── PPM
│   │   │   └── SM
│   │   └── README.md
│   ├── README.md
│   └── reports
│       ├── fig_placeholder.pdf
│       ├── model
│       │   └── PPM
│       ├── performance
│       │   ├── PPM
│       │   └── SM
│       ├── README.md
│       └── TSO_logo.pdf
└── user_models
    └── dictionary
```

* **config.ini**: 
  File with the tool's user configuration. Setting up the tool is not part 
  of this tutorial, so it will not be covered further.

* **config.ini_ADVANCED and config.ini_BASIC**: 
  This configuration files contain the default values for all configurable 
  variables in the application. To apply basic settings, rename the 
  config.ini_BASIC file to config.ini. If you prefer to use advanced settings, 
  rename the config.ini_ADVANCED file to config.ini instead. The application 
  will then load its configuration from the config.ini file according to the 
  chosen settings.

* **ddb**: 
  In this path are the dynamic models compiled from the tool, the user's and 
  the tool's own.

* **templates**:
  In this path are the user *PCSs* to validate by the tool.

* **templates/PCS**:
  This is where the user *PCSs* are defined. For the most part, they are
  "ini" files consisting of key-value pairs.  There is also the special case of the
  **TableInfiniteBus.txt** used in some PCSs, which defines the voltage and
  frequency changes of an infinite bus, whose values are templatized using Jinja and
  instantiated at run time.

* **templates/reports**:
  Contains the LaTeX templates for the reports corresponding to each *PCS* of the
  user. The templating system is Jinja.

* **user_models**: 
  In this path are the user dynamic models to be compiled from the tool.

* **user_models/dictionary**: 
  Dynawo is a tool that makes a large number of dynamic models available 
  to the user to represent an electrical network model, where each dynamic 
  model has its own parameters and nomenclature. This causes the tool to 
  need to have a mechanism that allows the translation of its own variables 
  into the corresponding parameters of the selected dynamic model. In this 
  way the user can inform the tool of the variable-parameter relationships 
  for their dynamic models. The variable-parameter relationship is expected 
  as an INI file with the following structure:
  * **[Caption]**: 
    As the first line, the name of the dynamic model is reported in square 
    brackets.
  * **key = value**: 
    Next, a line is declared for each model variable. This line relates a 
    tool variable such as *key* with a dynamic model parameter such as *value*.

Example of the content of an INI file:
```
[Model1]
ActivePower = model1_activepower
ReactivePower = model1_reactivepower
...

[Model2]
ActivePower = model2_activepower
ReactivePower = model2_reactivepower
...
```


# Results directory

## The structure of results

After executing a verification of the tool, a directory is created where 
the results are saved.

The *Results* directory is structured in:

```
(dgcv_venv) user@dynawo:~/work/MyTests$ tree Results -L 3
Results
├── PCS_RTE-I10
│   └── Islanding
│       └── DeltaP10DeltaQ4
├── PCS_RTE-I2
│   └── USetPointStep
│       ├── AReactance
│       └── BReactance
├── PCS_RTE-I5
│   └── ThreePhaseFault
│       └── TransientBolted
├── PCS_RTE-I6
│   └── GridVoltageDip
│       └── Qzero
├── PCS_RTE-I7
│   └── GridVoltageSwell
│       ├── QMax
│       └── QMin
└── Reports
    ├── report.pdf
    └── HTML
        ├── PCS_RTE-I2.USetPointStep.AReactance.html
        ├── PCS_RTE-I2.USetPointStep.BReactance.html
        ├── PCS_RTE-I5.ThreePhaseFault.TransientBolted.html
        ├── PCS_RTE-I6.GridVoltageDip.Qzero.html
        ├── PCS_RTE-I7.GridVoltageSwell.QMax.html
        └── PCS_RTE-I7.GridVoltageSwell.QMin.html
```

* **Reports\report.pdf**: 
  Complete verification report of the supplied model, the report consists of 
  a summary with the results of the *PCS* carried out, as well as the individual 
  reports of each *PCS*.
* **Reports\HTML folder**: 
  Individual HTML figures of each simulated *PCS* and scenario.
* **PCS_\* Directories**: 
  A directory with the output of each simulated *PCS*.

## The structure of a *PCS* output

Each *PCS* that is used to validate the producer model generates its own 
directory, this directory is made up of 2 types of elements:
  * The first type of element is the individual *PCS* report, the report 
    is a PDF file whose name begins with "report_".
  * The second type of element is a directory for each *benchmark* that 
    makes up the *PCS*, and these directories contains, in turn, a 
    directory for each *operating condition* that makes up the *benchmark*.

The tool provides, in its outputs, all the necessary files to be able to 
execute each *operating condition* individually with the Dynawo simulator.

The *operating condition* directory is structured in:

```
(dgcv_venv) user@dynawo:~/work/MyTests/Results$ tree PCS_RTE-I10/Islanding/DeltaP10DeltaQ4 -L 1
PCS_RTE-I10/Islanding/DeltaP10DeltaQ4
├── curves_calculated.csv
├── curves_reference.csv
├── Omega.dyd
├── Omega.par
├── outputs
├── Producer.dyd
├── Producer.par
├── solvers.par
├── TSOModel.crv
├── TSOModel.dyd
├── TSOModel.jobs
└── TSOModel.par
```

* **TSOModel Files**: 
  Files with the implementation of the *PCS* model for the Dynawo simulator.
* **solvers.par**: 
  File with the parameters used for the solvers that the tool can use.
* **Omega Files**: 
  Definition of the dynamic model used to declare OmegaRed and its parameters.
* **Producer Files**: 
  Definition of the producer model supplied by the user and its parameters.
* **curves_calculated.csv**: 
  File with the curves calculated by the tool for validating the producer's 
  model. It is only available if the Dynawo simulator finishes successfully.
* **curves_reference.csv**: 
  File with the reference curves obtained from user input for validating 
  the producer's model. It is only available as output of the `dgcv validate` 
  command.
* **outputs**: 
  Directory with the output generated by the dynamic simulation of the model 
  with Dynawo.

By accessing the directory with the results of an *operating condition* 
it is possible to experiment by modifying one or more parameters of the 
producer model, and obtain new curves with the Dynawo simulator. In the 
following example, the H parameter ("Kinetic constant = kinetic energy 
/ rated power") of the producer's Synchronous Machine found in the 
Producer.par file is modified, changing its value from 4.5 to 6.5. 

Note: Any edit to the TSOModel files will only have effects for executions 
by the user of the Dynawo simulator; future executions of the tool will 
not be affected by these changes.

```
    <!-- Original value -->
    <!-- par type="DOUBLE" name="generator_H" value="4.5"/ -->

    <!-- Testing value -->
    <par type="DOUBLE" name="generator_H" value="6.5"/>
```

![Modified Parameter](pngs/param_change.png)

In order for the tool to validate a change in the parameters of the 
producer model, it is essential to make the changes to the original 
input model files, and run the tool again. In this example, the original 
model is modified with the value of 6.5 in the H parameter of the 
Synchronous Machine, and to avoid losing the results of the first 
verification, an alternative route is indicated for the results of the 
new execution.

``` 
(dgcv_venv) user@dynawo:~/work/MyTests$ dgcv performance -m SingleAuxI -o SingleAuxI/Results_H6_5
2024-02-05 15:13:48,978 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I4.ThreePhaseFault, OPER. COND.: TransientBolted
2024-02-05 15:14:04,376 |          DGCV.PDFLatex |    INFO |            report.py:180 | PDF Done
2024-02-05 15:14:04,425 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I10.Islanding, OPER. COND.: DeltaP10DeltaQ4
2024-02-05 15:14:10,579 |          DGCV.PDFLatex |    INFO |            report.py:180 | PDF Done
2024-02-05 15:14:10,599 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I3.LineTrip, OPER. COND.: 2BReactance
2024-02-05 15:14:17,239 |          DGCV.PDFLatex |    INFO |            report.py:180 | PDF Done
2024-02-05 15:14:17,260 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: AReactance
2024-02-05 15:14:17,572 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I2.USetPointStep, OPER. COND.: BReactance
2024-02-05 15:14:24,072 |          DGCV.PDFLatex |    INFO |            report.py:180 | PDF Done
2024-02-05 15:14:24,092 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I6.GridVoltageDip, OPER. COND.: Qzero
2024-02-05 15:14:30,557 |          DGCV.PDFLatex |    INFO |            report.py:180 | PDF Done
2024-02-05 15:14:30,563 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I7.GridVoltageSwell, OPER. COND.: QMax
2024-02-05 15:14:36,391 |        DGCV.Validation | WARNING |       performance.py:119 | P has not reached steady state
2024-02-05 15:14:36,489 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I7.GridVoltageSwell, OPER. COND.: QMin
2024-02-05 15:14:43,436 |          DGCV.PDFLatex |    INFO |            report.py:180 | PDF Done
2024-02-05 15:14:43,471 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I8.LoadShedDisturbance, OPER. COND.: PmaxQzero
2024-02-05 15:14:49,367 |          DGCV.PDFLatex |    INFO |            report.py:180 | PDF Done
```

Or, if desired, it is possible to validate a *PCS* only

``` 
(dgcv_venv) user@dynawo:~/work/MyTests$ dgcv performance -m SingleAuxI -o SingleAuxI/Results_H6_5 -p PCS_RTE-I10
2024-02-05 15:26:10,407 | DGCV.Operating Condition |    INFO | operating_condition.py:585 | RUNNING BENCHMARK: PCS_RTE-I10.Islanding, OPER. COND.: DeltaP10DeltaQ4
2024-02-05 15:26:16,310 |          DGCV.PDFLatex |    INFO |            report.py:180 | PDF Done
```

# Running with debug on

This section explains the output files generated by the tool when 
a verification is executed in debug mode.

The first and most obvious change is that the log configuration is 
modified to activate debug messages, both in the console and in the 
file.

The changes that apply to the *PCS* output directory:

``` 
(dgcv_venv) user@dynawo:~/work/MyTests$ tree Results_debug/PCS_RTE-I4 -L 3
Results_debug/PCS_RTE-I4
└── ThreePhaseFault
    └── TransientBolted
        ├── curves_calculated.csv
        ├── bisection_last_success
        ├── bisection_last_failure
        ├── Omega.dyd
        ├── Omega.par
        ├── outputs
        ├── Producer.dyd
        ├── Producer.par
        ├── solvers.par
        ├── TSOModel.crv
        ├── TSOModel.dyd
        ├── TSOModel.jobs
        └── TSOModel.par
```

* In PCS that calculate values using a bisection search algorithm, 
* 2 new directories are maintained, each of the new directories 
* containing the complete Dynawo model used in the search, as well 
* as the output of the Dynawo execution. The *bisection_last_success* 
* directory corresponds to the last simulation that completed 
* successfully, while the *bisection_last_failure* directory 
* corresponds to the last simulation that failed.

# The Producer files

## “TSO’s side vs. the Producer’s side”

The network model used in the tool for dynamic simulation is divided 
into 2 parts, on one hand there are the files that model the simplified 
network of the producer, and on the other hand it corresponds to a 
simplified model of the TSO electrical network, the TSO model is defined 
in the PCS specifications.

Each PCS defines a **network model on the TSO side**, all models 
generated for the tool have been generated following the DTR 
specifications. To facilitate the implementation of the models, two 
decisions have been made in their design. First of all, all models 
implement the connection node (PDR node), as a dynamic model of a Bus, 
this facilitates the connection between the TSO model and that of the 
Producer, the producer only has to create in its network model a 
connection between a device of your model with the BusPDR. On the 
other hand, it has been decided to extract the OmegaRef modeling to 
its own set of DYD-PAR files, this eliminates duplication since there 
is no dynamic OmegaRef model that can be coupled to any dynamic 
generator model.

The producer's network model is a simplified representation of the 
producer's electrical network, this includes from the generating unit/s, 
with their corresponding auxiliary loads if they exist, and/or 
transformers, until reaching the BusPDR, a connection point that It is 
modeled on the TSO model. One point to keep in mind is that 
**the producer-side network** must be modeled using one of the standard 
topologies accepted by the tool.

## The 8 standard topologies

A requirement to be able to validate a producer network model is that 
when simulating the different PCS that make up the tool, it is 
guaranteed that the simulation starts at a stable point, without 
oscillations that come from the model and may affect the final result. 
In turn, each PCS has a defined TSO model designed specifically for its 
validation, this implies that the initialization of the models from one 
PCS to another is different and must be calculated individually for 
each validation. For this reason, 8 standard topologies have been 
defined that allow obtaining an equivalent model of the producer's 
network model to use as input to the tool.

### S

This is the simplest topology, it consists of a dynamic model of a 
synchronous generator connected to one side of a transformer, which is 
connected to the BusPDR from the opposite side.

### S + i

This topology is similar to the *S* topology, but instead of connecting 
the transformer directly to the PDR bus, there is an internal line 
between both elements. This line simplifies the entire network that may 
exist between the synchronous generator transformer and the connection 
to the TSO network (Internal network).

![Single](../manual/source/usage/figs_topologies/s.png)

### S + Aux

This topology allows the auxiliary loads of the synchronous generator 
to be modeled in the most simplified model. The auxiliary load is 
connected to its own transformer, and both transformers, that of the 
auxiliary load and that of the synchronous generator, are connected to 
the PDR bus.

### S + Aux + i

This topology is based on the *S + Aux* topology, adding a new internal 
bus model, where the transformers of the model are connected. In this 
model the internal network modeled by a line connects the internal bus 
with the BusPDR

![SingleAux](../manual/source/usage/figs_topologies/saux.png)


### M

This topology allows creating a model with multiple generators, where 
each generator is connected to one side of its own transformer, and an 
internal bus is connected to the other end of the transformer. From the 
internal bus there is a connection to a general transformer which is 
connected to the BusPDR. (Each generator that is modeled is an equivalent 
model of all the generators present in the real model that belong to the 
same family of generators).

### M + i

This topology is similar to the *M* topology, but instead of connecting 
the general transformer directly to the PDR bus, there is an internal 
line between both elements. This line simplifies the entire network that 
may exist between the synchronous generator transformer and the 
connection to the TSO network (Internal network). (Each generator that 
is modeled is an equivalent model of all the generators present in the 
real model that belong to the same family of generators).

![Multiple](../manual/source/usage/figs_topologies/m.png)

### M + Aux

This topology allows the *M* topology to be extended to include the 
auxiliary loads of the generators. These are modeled as a single 
auxiliary load connected to one side of its own transformer, which is 
connected to the internal bus on the opposite side. (Each generator that 
is modeled is an equivalent model of all the generators present in the 
real model that belong to the same family of generators).

### M + Aux + i

This topology is based on the *M + Aux* topology, but instead of 
connecting the general transformer directly to the PDR bus, there is an 
internal line between both elements. This line simplifies the entire 
network that may exist between the synchronous generator transformer 
and the connection to the TSO network (Internal network). (Each generator 
that is modeled is an equivalent model of all the generators present in 
the real model that belong to the same family of generators).

![MultipleAux](../manual/source/usage/figs_topologies/maux.png)

## Supported Dynawo model

Due to the complexity of Dynawo, and the number of dynamic models it has, 
a system has had to be designed in the tool to allow any model to be used. 
The system adopted by the tool consists of a **master dictionary** that 
allows translation from one of the variables declared in the tool to the 
equivalent variable for the selected dynamic model. The master dictionary 
is saved in *INI* files structured in sections, where the title of each 
section corresponds to the name of a Dynawo dynamic model, and in each 
key-value line the relationship between *a tool variable (key)* and 
*a dynamic model variable (value)*.

```
[GeneratorSynchronousFourWindingsTGov1SexsPss2a]
ActivePower0Pu = generator_P0Pu
ReactivePower0Pu = generator_Q0Pu
Voltage0Pu = generator_U0Pu
...
```

It is understood that a Dynawo dynamic model is supported by the tool when 
its definition exists in the tool's master dictionary.

# The Reference curves

## the directory structure

Reference curves are a set of files organized in a directory structure such 
as the one shown in this example:

``` 
(dgcv_venv) user@dynawo:~/work/MyTests$ tree ReferenceCurves
ReferenceCurves
├── CurvesFiles.ini
├── PCS.BenchMark1.OperatingCondition1.csv
├── PCS.BenchMark1.OperatingCondition1.dict
├── PCS.BenchMark1.OperatingCondition2.csv
├── PCS.BenchMark1.OperatingCondition2.dict
├── PCS.BenchMark2.OperatingCondition1.csv
└── PCS.BenchMark2.OperatingCondition1.dict
```

This example shows how the reference curves must be structured. Each operating 
condition has its own set of reference curve files, each consisting of 2 files: 
the reference signals file (in the image in CSV format), and a DICT file.

Reference signals are normally of EMT-type, obtained either from real field tests 
or from an EMT simulator. But they could also be RMS signals, obtained from a phasor 
simulation tool. For this reason, the tool can import reference signal in the 
following formats:

* COMTRADE:
  All versions of the COMTRADE standard up to version C37.111-2013 are admissible. 
  The signals can be provided either as a single file in the SBB format, or as a 
  pair of files in DAT+CFG formats (the two files must in this case have the same 
  name and differ only by their extension).

* EUROSTAG:
  Only the EXP ASCII format is supported.

* CSV:
  The column separator must be ";". A "time" column is required, although it does not 
  need to be the first column (see the DICT file below).

## DICT file
 It is mandatory to provide a companion *DICT* file, regardless of the format of 
 the reference signal file. This file provides two types of information that are 
 otherwise impossible to guess: 
 * The correspondence between the columns of the file and the quantities expected in the PCSs. 
 * Certain simulation parameters used to obtain the curves (depending on the PCS).

```
[Curves-Metadata]
# True when the reference curves are field measurements
is_field_measurements =
# Instant of time at which the event or fault starts
# Variable sim_t_event_start is called simply sim_t_event in the DTR
sim_t_event_start =
# Duration of the event or fault
fault_duration =
# Frequency sampling of the reference curves
frequency_sampling =

[Curves-Dictionary]
time = 
BusPDR_BUS_ActivePower =
BusPDR_BUS_ReactivePower =
BusPDR_BUS_ActiveCurrent =
BusPDR_BUS_ReactiveCurrent =
BusPDR_BUS_Voltage =
NetworkFrequencyPu =
# Replace "[XFMR_ID]" with the transformer id associating to the Wind Turbine or PV Array
[XFMR_ID]_XFMR_Tap =
# Replace "[WT_ID]" with the Wind Turbine id or PV Array id
[WT_ID]_GEN_InjectedActiveCurrent =
[WT_ID]_GEN_InjectedReactiveCurrent =
[WT_ID]_GEN_AVRSetpointPu =
[WT_ID]_GEN_MagnitudeControlledByAVRPu =
[WT_ID]_GEN_InjectedCurrent =
# To represent a signal that is in raw abc three-phase form, the affected signal must be tripled
# and the suffixes _a, _b and _c must be added as in the following example:
#    BusPDR_BUS_Voltage_a =
#    BusPDR_BUS_Voltage_b =
#    BusPDR_BUS_Voltage_c =
```

# The Producer curves

## the directory structure

Producer curves are a set of files organized in a directory 
structure similar to reference curves, as seen in this example:

``` 
(dgcv_venv) user@dynawo:~/work/MyTests$ tree ProducerCurves
ProducerCurves
├── CurvesFiles.ini
├── PCS.BenchMark1.OperatingCondition1.csv
├── PCS.BenchMark1.OperatingCondition1.dict
├── PCS.BenchMark1.OperatingCondition2.csv
├── PCS.BenchMark1.OperatingCondition2.dict
├── PCS.BenchMark2.OperatingCondition1.csv
├── PCS.BenchMark2.OperatingCondition1.dict
└── Producer.ini
```
The main difference is in the need to include the Producer.ini file 
in the directory, this file is essential to inform the tool of the model 
data that cannot be inferred from the curve files.

For a description of the rest of the files go to 
[The Reference curves](#the-reference-curves) section.

# Inputs template

To try to make it easier for the producer to generate the tool inputs, each 
verification command can be executed in a way that generates all the files necessary 
for the simulation of the model. The argument mentioned is ```dgcv generate```. 
When executing one of the verification commands using this argument, the files 
necessary to model the producer network (DYD, PAR) are obtained in the indicated 
path, an INI file with the parameters required by the tool that cannot be acquired 
from the model, and the entire structure to provide the tool with the curves for 
each PCS.

```
(dgcv_venv) user@dynawo:~$ tree SM
SM
├── Producer.dyd
├── Producer.ini
├── Producer.par
└── ReferenceCurves
    ├── CurvesFiles.ini
	├── PCS_RTE-I16z1.GridFreqRamp.W500mHz250ms.csv
	├── PCS_RTE-I16z1.GridFreqRamp.W500mHz250ms.dict
	├── PCS_RTE-I16z1.GridVoltageStep.Drop.csv
	├── PCS_RTE-I16z1.GridVoltageStep.Drop.dict
	├── PCS_RTE-I16z1.GridVoltageStep.Rise.csv
	├── PCS_RTE-I16z1.GridVoltageStep.Rise.dict
	├── PCS_RTE-I16z1.SetPointStep.Active.csv
	├── PCS_RTE-I16z1.SetPointStep.Active.dict
	├── PCS_RTE-I16z1.SetPointStep.Reactive.csv
	├── PCS_RTE-I16z1.SetPointStep.Reactive.dict
	├── PCS_RTE-I16z1.SetPointStep.Voltage.csv
	├── PCS_RTE-I16z1.SetPointStep.Voltage.dict
	├── PCS_RTE-I16z1.ThreePhaseFault.PermanentBolted.csv
	├── PCS_RTE-I16z1.ThreePhaseFault.PermanentBolted.dict
	├── PCS_RTE-I16z1.ThreePhaseFault.PermanentHiZ.csv
	├── PCS_RTE-I16z1.ThreePhaseFault.PermanentHiZ.dict
	├── PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR10.csv
	├── PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR10.dict
	├── PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3.csv
	├── PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3.dict
	├── PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3Qmin.csv
	├── PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3Qmin.dict
	├── PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc500.csv
	├── PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc500.dict
	├── PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800.csv
	├── PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800.dict
	├── PCS_RTE-I16z3.GridVoltageDip.Qzero.csv
	├── PCS_RTE-I16z3.GridVoltageDip.Qzero.dict
	├── PCS_RTE-I16z3.GridVoltageSwell.QMax.csv
	├── PCS_RTE-I16z3.GridVoltageSwell.QMax.dict
	├── PCS_RTE-I16z3.GridVoltageSwell.QMin.csv
	├── PCS_RTE-I16z3.GridVoltageSwell.QMin.dict
	├── PCS_RTE-I16z3.Islanding.DeltaP10DeltaQ4.csv
	├── PCS_RTE-I16z3.Islanding.DeltaP10DeltaQ4.dict
	├── PCS_RTE-I16z3.PSetPointStep.Dec40.csv
	├── PCS_RTE-I16z3.PSetPointStep.Dec40.dict
	├── PCS_RTE-I16z3.PSetPointStep.Inc40.csv
	├── PCS_RTE-I16z3.PSetPointStep.Inc40.dict
	├── PCS_RTE-I16z3.QSetPointStep.Dec20.csv
	├── PCS_RTE-I16z3.QSetPointStep.Dec20.dict
	├── PCS_RTE-I16z3.QSetPointStep.Inc10.csv
	├── PCS_RTE-I16z3.QSetPointStep.Inc10.dict
	├── PCS_RTE-I16z3.ThreePhaseFault.TransientBolted.csv
	├── PCS_RTE-I16z3.ThreePhaseFault.TransientBolted.dict
	├── PCS_RTE-I16z3.USetPointStep.AReactance.csv
	├── PCS_RTE-I16z3.USetPointStep.AReactance.dict
	├── PCS_RTE-I16z3.USetPointStep.BReactance.csv
	└── PCS_RTE-I16z3.USetPointStep.BReactance.dict
```

All files provided are templates, so the user must modify all of them to 
populate their network data in the producer model files, and/or with the 
curve data provided if they wish to use the curve files in the inputs of 
the tool. In the case of curves, in addition to modifying the .DICT files 
provided by the tool, you must provide an additional file with the desired 
curves, the name of this file must be the same as the name of the DICT file, 
but with the extension that corresponds according to the type of curves provided.

# Log file and console messages

The tool has 2 ways to show the logs of its execution, in the console and in 
a file. Special emphasis must be placed on the location of the log files, since 
the file with the logs obtained when compiling new models for Dynawo is saved 
in the same path where the compiled models are saved `./config/dgcv/ddb /dgcv.log`, 
while the logs obtained from validating a model, whether electrical performance 
or model validation, are saved together with the results of the tool with the 
name `dgcv.log`.