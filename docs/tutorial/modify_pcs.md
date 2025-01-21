===========================

TUTORIAL

MODIFY PCS

(c) 2023&mdash;24 RTE  
Developed by Grupo AIA

===========================

--------------------------------------------------------------------------------

#### Table of Contents

1. [Running a PCS](#running-a-pcs)
2. [PCS results](#pcs-results)
3. [PCS thresholds](#pcs-thresholds)
4. [PCS operating conditions](#pcs-operating-conditions)

--------------------------------------------------------------------------------

# Running a PCS

All tool commands have the ```-p PCS, --pcs PCS     enter one pcs to validate``` argument, 
which allows the selected command to be executed only for the selected PCS.

```
(dgcv_venv) user@dynawo:~/work/myTests$  dgcv validate -m Model/WECC Model/WECC/Curves -p PCS_RTE-I16z1
2024-02-26 11:04:21,608 | DGCV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3
2024-02-26 11:04:24,081 | DGCV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR10
2024-02-26 11:04:26,479 | DGCV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientBoltedSCR3Qmin
2024-02-26 11:04:28,889 | DGCV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientHiZTc800
2024-02-26 11:04:37,250 | DGCV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: TransientHiZTc500
2024-02-26 11:04:51,572 | DGCV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentBolted
2024-02-26 11:04:55,117 | DGCV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.ThreePhaseFault, OPER. COND.: PermanentHiZ
2024-02-26 11:05:19,773 | DGCV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Active
2024-02-26 11:05:25,166 | DGCV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Reactive
2024-02-26 11:05:30,056 | DGCV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.SetPointStep, OPER. COND.: Voltage
2024-02-26 11:05:34,342 | DGCV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridFreqRamp, OPER. COND.: W500mHz250ms
2024-02-26 11:05:38,195 | DGCV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Rise
2024-02-26 11:05:42,729 | DGCV.Operating Condition |    INFO | operating_condition.py:886 | RUNNING BENCHMARK: PCS_RTE-I16z1.GridVoltageStep, OPER. COND.: Drop
2024-02-26 11:06:03,355 |          DGCV.PDFLatex | WARNING |            figure.py:226 | All curves appear to be flat in PCS_RTE-I16z1.GridFreqRamp.W500mHz250ms; something must be wrong with the simulation
2024-02-26 11:06:30,078 |          DGCV.PDFLatex |    INFO |            report.py:223 | PDF Done
```

# PCS results

## Results dir 

After execution, the tool generates a report to show a description of the PCS, the results of 
the compliance checks performed, the values used in the checks, and figures of the relevant 
curves. This report is located in the directory indicated by the user if the ```-o RESULTS_DIR, 
--results_dir RESULTS_DIR``` argument has been used, otherwise the tool creates a subdirectory 
called *Results* within the producer model directory.

## Report structure

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

# PCS thresholds

## Definition

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

## Changing the defaults values

By having the model validation thresholds defined in the tool configuration file, the user
can modify them if desired by editing the user configuration file (`config.ini`) located in the 
`~/.config/dgcv` dir. In this file the user has all the configuration options available for the 
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

**Previous example after modify the `thr_P_mxe_during` threshold:** 

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


# PCS operating conditions

## Definition

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

## Changing the operating conditions

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


## Adding a new operating conditions

Steps to expand an existing PCS with new operating conditions:

1. Configuration:
   - Copy the configuration of an existing operating conditions in the PCS to the user 
        configuration file.
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
        the purpose of the ner conditions.
     ```ini
        # In this example the parameter pdr_Q will be modified from Qmin to 0, so it is proposed
        # to modify the name from Rise to RiseQ0
     
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
        # Reactance of the line connected to the PDR point
        #line_XPu =
        # SCR stands for Short Circuit Ratio
        SCR = 10
        # PDR point
        pdr_P = 0.5*Pmax
        # pdr_Q = Qmin
        pdr_Q = 0
        pdr_U = 0.95*Udim
        # Infinite Bus configuration
        # To configure time parameters, the following convention is used:
        # * 'delta_t_': indicates how long the network remains in a certain state, this value will be
        #                added to the time in which the event is triggered.
        # * otherwise: the value of this variable will be used in the tool without prior treatments.
        # TSO Model configuration
     ```
2. Report: Modify or expand the latex report template to include the simulation results wtih 
the new operating conditions. 

<span style="background-color: #4976ba;">INFO:</span> The process for expanding a report is not 
covered in this tutorial. 