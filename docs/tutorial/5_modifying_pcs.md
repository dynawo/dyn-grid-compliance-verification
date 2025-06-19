===========================

TUTORIAL

HOW TO MODIFY PCS

(c) 2023&mdash;25 RTE  
Developed by Grupo AIA

===========================

--------------------------------------------------------------------------------

#### Table of Contents

1. [Running a PCS](#running-a-pcs)
2. [PCS results](#pcs-results)
    1. [Results dir](#results-dir)
    2. [Report structure](#report-structure)
3. [PCS operating conditions](#pcs-operating-conditions)
4. [Changing the operating condition](#changing-the-operating-condition)
5. [Adding a new operating condition](#adding-a-new-operating-condition)
    1. [Modifying the PCS configuration](#modifying-the-pcs-configuration)
    2. [Modifying the latex report template](#modifying-the-latex-report-template)

--------------------------------------------------------------------------------

## Running a PCS

All tool commands have the ```-p PCS, --pcs PCS     enter one pcs to validate``` argument, 
which allows the selected command to be executed only for the selected PCS.

```
(dycov_venv) user@dynawo:~/work/myTests$  dycov validate -m Model/WECC Model/WECC/Curves -p PCS_RTE-I16z1
2024-02-26 11:04:21,608 | DyCoV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3
2024-02-26 11:04:24,081 | DyCoV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR10
2024-02-26 11:04:26,479 | DyCoV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3Qmin
2024-02-26 11:04:28,889 | DyCoV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientHiZTc800
2024-02-26 11:04:37,250 | DyCoV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientHiZTc500
2024-02-26 11:04:51,572 | DyCoV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentBolted
2024-02-26 11:04:55,117 | DyCoV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentHiZ
2024-02-26 11:05:19,773 | DyCoV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Active
2024-02-26 11:05:25,166 | DyCoV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Reactive
2024-02-26 11:05:30,056 | DyCoV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Voltage
2024-02-26 11:05:34,342 | DyCoV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridFreqRamp, OPER. COND.: W500mHz250ms
2024-02-26 11:05:38,195 | DyCoV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Rise
2024-02-26 11:05:42,729 | DyCoV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Drop
2024-02-26 11:06:03,355 |          DyCoV.PDFLatex | WARNING |            figure.py:226 | All curves appear to be flat in PCS_RTE-I16z1.GridFreqRamp.W500mHz250ms; something must be wrong with the simulation
2024-02-26 11:06:30,078 |          DyCoV.PDFLatex |    INFO |            report.py:223 | PDF Done
```

## PCS results

### Results dir 

After execution, the tool generates a report to show a description of the PCS, the results of 
the compliance checks performed, the values used in the checks, and figures of the relevant 
curves. This report is located in the directory indicated by the user if the ```-o RESULTS_DIR, 
--results_dir RESULTS_DIR``` argument has been used, otherwise the tool creates a subdirectory 
called *Results* within the producer model directory.

### Report structure

A PCS report is divided into sections:

- **Simulation**:
    Description of the TSO model and the operating conditions to simulate. 
- **Simulation results**:
    Figures of the most representative curves of the simulated case.
- **Analysis of results**:
    Table with the error values (MXE, ME and MAE) of the calculated curves with respect to the
    reference curves for the following ranges:
    - Pre-event: Values of the curve between the start of the simulation and the moment at which 
                the event occurs.
    - During-event: Values of the curve between the start of the event and the end of the event.
    - Post-event: Values of the curve between the end of the event and the end of the simulation.
- **Compliance checks**:
    Tables with the error values (MXE, ME and MAE), in the same ranges mentioned above, with 
    respect to the maximum configured thresholds. Values that do not respect the maximum threshold
    appear in red.

**Compliance checks example:** 

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

## PCS operating conditions

As mentioned above, in the report there is a section called **Simulation** where the TSO model, 
and the operating conditions that is simulated for the validation of the Producer model are 
described. The operating conditions define everything that is needed to instantiate an actual 
test: the initial operating point (V, P, Q) of the system, the characteristics of the event,
and some parameters of the grid's side model such as the short-circuit impedance Z<sub>SC</sub>.
The operating conditions of each included PCS are declared in the tool's configuration files, and 
at the ned of the user configuration file, an example is shown how the operating conditions are
configured.

```ini
## [PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3]
## # Report filename, if the report is split into multiple files, one by OC 
## report_name = report.ThreePhaseFault.TransientBoltedSCR3.tex
## # PDR Node
## pdr_P = Pmax
## pdr_Q = 0
## pdr_U = Udim
## # Fault duration time until the line is disconnected (s)
## HTB1_fault_t = 0.150
## HTB2_fault_t = 0.150
## HTB3_fault_t = 0.150
## # Short Circuit Ratio
## SCR = 3
```

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

## Changing the operating condition

To modify the operating conditions for a PCS, the operating condition section that will be 
modified, as well as the parameters that will vary, must be added to the user configuration file.

**In the previous example:** 

The operating condition section of the example, and the value of Q in the PDR node are defined
to use _Qmin_ instead of its default value (0). 

```ini
[PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800]
## # Operating conditions
## # PDR Node
## # pdr_Q = 0
pdr_Q = Qmin
```

Results extracted from the report with _Qmin_ and the same reference curves: 

PCS_RTE-I16z1 - Transient fault:High-impedance fault ( V = 0.5U n, 800ms )

Compliance checks on the curves, every 3 columns shown in the table show the errors for a 
specific time range nof the curve, where the first 3 columns (called MXE, ME, and MAE) 
correspond to the pre-event range, the next 3 columns to the range in which the event is happening,
and the last 3 columns correspond to the post-event range:

|      | MXE                                   | ME                                     | MAE                                   | MXE                                   | ME                                    | MAE                                   | MXE                                   | ME                                    | MAE                                   | Compl.                                |
|------|---------------------------------------|----------------------------------------|---------------------------------------|---------------------------------------|---------------------------------------|---------------------------------------|---------------------------------------|---------------------------------------|---------------------------------------|---------------------------------------|
| P    | 0.00878                               | 0.0                                    | 5.1e-05                               | <span style="color: red">0.577</span> | 0.0                                   | <span style="color: red">0.553</span> | <span style="color: red">0.158</span> | 0.00137                               | 0.0015                                | <span style="color: red">False</span> |
| Q    | <span style="color: red">0.4</span>   | <span style="color: red">0.29</span>   | <span style="color: red">0.29</span>  | <span style="color: red">0.177</span> | <span style="color: red">0.123</span> | <span style="color: red">0.123</span> | <span style="color: red">0.309</span> | <span style="color: red">0.286</span> | <span style="color: red">0.286</span> | <span style="color: red">False</span> |
| I re | <span style="color: red">0.121</span> | <span style="color: red"> 0.121</span> | <span style="color: red">0.121</span> | <span style="color: red">0.52</span>  | 0.0                                   | <span style="color: red">0.495</span> | <span style="color: red">0.123</span> | <span style="color: red">0.122</span> | <span style="color: red">0.122</span> | <span style="color: red">False</span> |
| I im | <span style="color: red">0.334</span> | 0.0                                    | <span style="color: red">0.217</span> | <span style="color: red">0.436</span> | 0.0                                   | <span style="color: red">0.424</span> | <span style="color: red">0.348</span> | 0.0                                   | <span style="color: red">0.212</span> | <span style="color: red">False</span> |  

In steady state after the event, the absolute average error must not exceed 1%:

| Variable | MAE     | Final Error | Compliance                            |
|----------|---------|-------------|---------------------------------------|
| V        | 0.0485  | 0.0485      | <span style="color: red">False</span> |
| P        | 0.00144 | 0.00144     | True                                  |
| Q        | 0.286   | 0.286       | <span style="color: red">False</span> |
| I re     | 0.122   | 0.122       | <span style="color: red">False</span> |
| I im     | 0.212   | 0.212       | <span style="color: red">False</span> |

<span style="background-color: #ffcc11;">WARNING:</span> The tool reports are witten using the 
DTR specifications, this means that variation in operating conditions affects the results 
displayed, but not the description of the case within the final report.


## Adding a new operating condition

To add a new operating condition to a PCS the user must create the new files 
in their configuration directory, specifically in the **templates** directory 
within the user configuration directory, this directory is structured in:
```
(dycov_venv) user@dynawo:~/.config$ tree dycov
dycov$
├── config.ini
...
├── templates
│   ├── PCS
│   │   ├── model
│   │   │   ├── BESS
│   │   │   └── PPM
│   │   ├── performance
│   │   │   ├── BESS
│   │   │   ├── PPM
│   │   │   └── SM
│   │   └── README.md
│   ├── README.md
│   └── reports
│       ├── fig_placeholder.pdf
│       ├── model
│       │   ├── BESS
│       │   └── PPM
│       ├── performance
│       │   ├── BESS
│       │   ├── PPM
│       │   └── SM
│       ├── README.md
│       └── TSO_logo.pdf
...
```

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


### Modifying the PCS configuration

Steps to expand the configuration of an existing PCS with new operating conditions:

- Copy the configuration of an existing operating condition in the PCS to the corresponding 
    user configuration file.

  The **PCSDescription.ini** file is created in the **./templates/PCS/model/PPM/PCS_RTE-I16z1** 
  directory, since a new OC is to be added for the *model validation* of the 
  *Power Plant Modules(PPM)* in the PCS called **PCS_RTE-I16z1**.
  ```
    (dycov_venv) user@dynawo:~/.config$ touch ./templates/PCS/model/PPM/PCS_RTE-I16z1/PCSDescription.ini
  ```

  The content of an existing operating condition in the PCS is copied to the new file. It is recommended 
  to copy an operating condition from the benchmark that you want to expand.
  ```ini
     [PCS_RTE-I16z1.GridVoltageStep.Rise]
     # Operating Condition LateX filename
     report_name = report.GridVoltageStep.Rise.tex
     # Tolerance for reference tracking tests should be adapted to the magnitude of the step change
     reference_step_size = 0.1
     # Is this a bolted fault OC?
     bolted_fault = false
     # Is this a hiz fault OC?
     hiz_fault = false
     # OperatingCondition type
     setpoint_change_test_type = Others
     # Force to configure Voltage Droop Mode
     # (Only applies to USetpoint type tests, and generating units with Plant Controller)
     force_voltage_droop = false
     [PCS_RTE-I16z1.GridVoltageStep.Rise.Model]
     # Reactance of the line connected to the PDR point
     #line_XPu =
     # SCR stands for Short Circuit Ratio
     SCR = 10
     # PDR point
     pdr_P = 0.5*Pmax
     pdr_Q = Qmin
     pdr_U = 0.95*Udim
     # Infinite Bus configuration
     # To configure time parameters, the following convention is used:
     # * 'delta_t_': indicates how long the network remains in a certain state, this value will be
     #                added to the time in which the event is triggered.
     # * otherwise: the value of this variable will be used in the tool without prior treatments.
     # TSO Model configuration
     [PCS_RTE-I16z1.GridVoltageStep.Rise.Event]
     # Event connected to setpoint magnitude
     connect_event_to = AVRSetpointPu
     # Instant of time at which the event or fault starts
     # Variable sim_t_event_start is called simply sim_t_event in the DTR
     sim_t_event_start = 30
     # Duration of the event or fault
     #fault_duration =
     # Event setpoint step value
     #  This test presents a voltage drop in the TSO model when the event occurs, the
     #  step field of the event is used to represent it
     setpoint_step_value = 0.1
  ```
- Change the name of the operating conditions, it is advisable to put a name that describes
     the purpose of the new conditions.
     In this example the parameter **pdr_Q** will be modified from *Qmin* to *0*, so it is 
     proposed to modify the name from **Rise** to **RiseQ0**
  ```ini
     [PCS_RTE-I16z1.GridVoltageStep.RiseQ0]
     ...
     [PCS_RTE-I16z1.GridVoltageStep.RiseQ0.Model]
     ...
     [PCS_RTE-I16z1.GridVoltageStep.RiseQ0.Event]
     ...
  ```
- Copy and add the name of the new operating conditions to the corresponding benchmark
  ```ini
     [PCS-OperatingConditions]
     # PCS_RTE-I16z1.GridVoltageStep = Rise,Drop
     PCS_RTE-I16z1.GridVoltageStep = Rise,Drop,RiseQ0
  ```
- Finally, edit the parameters you want to modify     
  ```ini
     [PCS_RTE-I16z1.GridVoltageStep.RiseQ0.Model]
     # PDR point
     pdr_P = 0.5*Pmax
     # pdr_Q = Qmin
     pdr_Q = 0
     pdr_U = 0.95*Udim
  ```

### Modifying the latex report template

Steps to expand the latex report template to include the simulation results with 
the new operating condition:

- Copy the latex template of an existing operating condition in the PCS to the corresponding 
    user configuration file.

  Copy a latex template file to the **./templates/reports/model/PPM/PCS_RTE-I16z1** 
  directory with the new operating condition name, since a new OC is to be added for the 
  *model validation* of the *Power Plant Modules(PPM)* in the PCS called **PCS_RTE-I16z1**. 
  It is recommended to copy an operating condition from the benchmark that you want to expand.
  ```
    (dycov_venv) user@dynawo:~/.config$ cp /home/user/dycov_repo/dycov_venv/lib/python3.10/site-packages/dycov/templates/reports/model/PPM/PCS_RTE-I16z1/report.GridVoltageStep.Rise.tex ./templates/reports/model/PPM/PCS_RTE-I16z1/report.GridVoltageStep.RiseQ0.tex
  ```

- Search the latex file for the placeholders that contain the name of the copied operating 
    condition and replace it with the new name.

    * linkPCSI16z1GridVoltageStepRise -> linkPCSI16z1GridVoltageStepRiseQ0
    * rmPCSI16z1GridVoltageStepRise -> rmPCSI16z1GridVoltageStepRiseQ0
    * thmPCSI16z1GridVoltageStepRise -> thmPCSI16z1GridVoltageStepRiseQ0
    * etc.

- Search the latex file for the placeholders that contain the name of the copied operating 
    condition and replace it with the new name.

- Change the title and description of the test

  ```
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Voltage Step %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

    \renewcommand{\DTRPcs}{GridVoltageStep} % DTR pcs definition
    \renewcommand{\DTRPcsLong}{Grid Voltage Step (Model Validation Zone 1)}
    \renewcommand{\OCname}{RiseQ0}


    \subsection{Step response to grid changes: V swell}

    Checks for compliant behavior of the generating unit under a grid scenario where there
    is a $10\%$ voltage step increase on AC source.

    \begin{description}
        \item Initial conditions used at the PDR bus:
        \begin{itemize}
            \item $P = P_\text{max\_unite}$
            \item $Q = Q_{min}$
            \item $U = U_\text{dim}$
            \item $SCR = 10$
        \end{itemize}
    \end{description}

    \GridCircuitZone

    \GridCurvesZone
    \\[2\baselineskip]
    Go to  {{ linkPCSI16z1GridVoltageStepRiseQ0 }}

    \subsubsection{Analysis of results}
    \begin{center}
        \scriptsize
        \begin{tabular}{lccccccc}
            \toprule
            & \multicolumn{3}{c}{Pre-event} & \multicolumn{3}{c}{Event} \\
            \cmidrule(lr){2-4}\cmidrule(lr){5-7}
            & {MXE}      & {ME}       & {MAE}      & {MXE}      & {ME}       & {MAE}      \\
            \midrule
            \BLOCK{for row in rmPCSI16z1GridVoltageStepRiseQ0}
            {{row[0]}} & {{row[1]}} & {{row[2]}} & {{row[3]}} & {{row[4]}} & {{row[5]}} & {{row[6]}} \\
            \BLOCK{endfor}
            \bottomrule
        \end{tabular}
    \end{center}

    \subsubsection{Compliance checks}

    \noindent Compliance thresholds on the curves:
    \begin{center}
        \scriptsize
        \begin{tabular}{lcccccc}
            \toprule
            & \multicolumn{3}{c}{Pre-event} & \multicolumn{3}{c}{Event} \\
            \cmidrule(lr){2-4}\cmidrule(lr){5-7}
            & {MXE}      & {ME}       & {MAE}      & {MXE}      & {ME}       & {MAE}      \\
            \midrule
            \BLOCK{for row in thmPCSI16z1GridVoltageStepRiseQ0}
            {{row[0]}} & {{row[1]}} & {{row[2]}} & {{row[3]}} & {{row[4]}} & {{row[5]}} & {{row[6]}} \\
            \BLOCK{endfor}
            \bottomrule
        \end{tabular}
    \end{center}

    \noindent Compliance checks on the curves:
    \begin{center}
        \scriptsize
        \begin{tabular}{lccccccc}
            \toprule
            & \multicolumn{3}{c}{Pre-event} & \multicolumn{3}{c}{Event} & \\
            \cmidrule(lr){2-4}\cmidrule(lr){5-7}
            & {MXE}      & {ME}       & {MAE}      & {MXE}      & {ME}       & {MAE}      & Compl.     \\
            \midrule
            \BLOCK{for row in emPCSI16z1GridVoltageStepRiseQ0}
            {{row[0]}} & {{row[1]}} & {{row[2]}} & {{row[3]}} & {{row[4]}} & {{row[5]}} & {{row[6]}} & {{row[7]}} \\
            \BLOCK{endfor}
            \bottomrule
        \end{tabular}
    \end{center}

    \noindent Compliance checks on the step-response characteristic: \\
    \begin{minipage}{\linewidth} % because otherwise, the footnote does not show
        \centering
        \scriptsize
        \begin{tabular}{lccccc}
            \toprule
            Step-response indicator & Simulated  & Reference  & Rel. Err. (\%) & Threshold (\%) & Compl.     \\
            \midrule
            \BLOCK{for row in temPCSI16z1GridVoltageStepRiseQ0}
            {{row[0]}}              & {{row[1]}} & {{row[2]}} & {{row[3]}} & {{row[4]}} & {{row[5]}} \\
            \BLOCK{endfor}
            \bottomrule
        \end{tabular}
    \end{minipage}

    \noindent In steady state after the event, the absolute average error must not exceed {{steadystatethreshold}}\% (configured value):
    \begin{center}
        \scriptsize
        \begin{tabular}{cllc}
            \toprule
            Variable   & MAE        & Final Error & Compliance \\
            \midrule
            \BLOCK{for row in ssemPCSI16z1GridVoltageStepRiseQ0}
            {{row[0]}} & {{row[1]}} & {{row[2]}}  & {{row[3]}} \\
            \BLOCK{endfor}
            \bottomrule
        \end{tabular}
    \end{center}
```


