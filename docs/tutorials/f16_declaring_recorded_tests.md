# Declaring the on-site tests of PCS F16

This tutorial explains, step by step, how to write the `F16Description.ini`
that a producer delivers with the commissioning records of an installation,
so that DyCoV runs the open phasor model against those records and applies
the compliance tests of the DTR Fiche F16.

It assumes you have read [RMS model validation](rms_model_validation.md) and
[Preparing inputs](preparing_inputs.md).

---

## 1. Overview

PCS F16 is the second phase of the open phasor model validation. In phase 1
(PCS I16) the model is compared with another simulation; in phase 2 it is
compared with the **on-site measurements recorded during the commissioning
tests** of the installation. It applies to **Zone 3 only**, at the connection
point (PDR).

The fiche selects no test of its own. The producer proposes the on-site tests,
RTE approves them, and the recorded signals become the reference. The fiche
only fixes:

- the **active power levels** every test runs at: minimum, 50 % of the maximum
  and maximum injection (for storage: maximum and 50 % consumption, 50 % and
  maximum injection);
- the **indicators** of I16 (ME, MAE and MXE of the controlled magnitude;
  reaction, rise and settling times; overshoot; steady-state error) with the
  tolerances of F16.

DyCoV therefore ships `PCS_RTE-F16z3` **without any test**. The tests you
recorded are declared, with their records, in a file named
`F16Description.ini`. This file tells DyCoV:

1. which kinds of test were recorded (the **benchmarks**),
2. at which operating points, with which grid and which event (the
   **operating conditions**),
3. which **compliance tests** to apply to each benchmark,
4. which **figures** to draw in the report.

DyCoV knows six kinds of test at the connection point: the active, reactive
and voltage **setpoint steps**, which a commissioning applies on purpose, and
five grid events an installation may have gone through while recording: a
**three-phase fault**, a **voltage dip**, a **voltage swell**, a **frequency
ramp** and an **islanding**. Each one is declared the same way, with the
keys of its kind. The chapter *The F16 declaration file* of the user manual
is the reference of every key of this file, and *Compliance tests* of every
test it can activate.

---

## 2. Prerequisites

Before writing the declaration you need:

**The Zone 3 model of the installation**, as for PCS I16:

```text
Dynawo/
└── Zone3/
    ├── Producer.dyd
    ├── Producer.par
    └── Producer.ini
```

F16 needs no Zone 1 model: the commissioning records are taken at the PDR,
and the model of the complete installation is the only one compared with them.
`Dynawo/` may therefore hold `Zone3/` alone, as long as the run is limited to
`PCS_RTE-F16z3` with `-p` (see the run below): without `-p` the run also
covers PCS I16, whose zone-1 PCS needs `Zone1/`.

`Producer.ini` must declare, besides the usual limits, the **minimum active
power** the tests start from:

```ini
# p_{max_unite} injection as defined by the DTR in MW
p_max_injection_at_PDR = 75
# p_{min_unite} injection in MW, the lowest active power the on-site tests of the DTR
# Fiche F16 start from
p_min_injection_at_PDR = 7.5
```

Storage installations declare `p_min_consumption_at_PDR` as well. A missing
key is read as 0 MW.

**One record per test and per active power level**, in the reference curves
directory, in any of the formats DyCoV reads (COMTRADE, EUROSTAG EXP or CSV):

```text
ReferenceCurves/
├── F16Description.ini                       ← the declaration (this tutorial)
└── Producer/
    ├── CurvesFiles.ini
    ├── PCS_RTE-F16z3.PSetPointStep.Pmin.csv
    ├── PCS_RTE-F16z3.PSetPointStep.Pmin.dict
    ├── PCS_RTE-F16z3.PSetPointStep.P50.csv
    ├── PCS_RTE-F16z3.PSetPointStep.P50.dict
    └── ...
```

The records are described in [step 4](#7-step-4--the-records).

---

## 3. Where the file goes, and how DyCoV finds it

Put `F16Description.ini` **next to the reference curves**, at the root of the
`ReferenceCurves` directory you pass to `dycov validate`. DyCoV reads every
`*Description.ini` found there and takes as the description of a PCS the file
that names that PCS in its `[PCS-Benchmarks]` section. For F16 that is:

```ini
[PCS-Benchmarks]
PCS_RTE-F16z3 = PSetPointStep,USetPointStep
```

The file is read as the **user description** of `PCS_RTE-F16z3`: it patches
the description shipped with the tool, which already carries the PCS header
(`zone = 3`, the report template, the F16 tolerance family). You only write
the tests.

A declaration delivered with the curves takes the place of a
`PCSDescription.ini` of the same PCS in your configuration directory
(`~/.config/dycov/templates/PCS/model/<technology>/PCS_RTE-F16z3/`). DyCoV
leaves a copy of the shipped template there at start-up, commented out: you
can complete that copy instead, but it then applies to every case you run on
that machine. The file delivered with the records is the one to use for a
real installation.

When no file declares a test for `PCS_RTE-F16z3`, the run logs
`PCS_RTE-F16z3: no test declared, nothing to validate` and goes on with the
other PCS.

---

## 4. Step 1 — Declare one benchmark per kind of recorded test

A benchmark is the grid model on the TSO side plus the kind of event. Declare
one per kind of test you recorded:

```ini
[PCS-Benchmarks]
PCS_RTE-F16z3 = PSetPointStep,USetPointStep

[PCS_RTE-F16z3.PSetPointStep]
# Job name to apply in the JOBS file
job_name = PCS F16-Zone3 (Power Park Modules) - Active Setpoint Step
# TSO model side
TSO_model = RefTracking_1Line_InfBus
# Omega model
Omega_model = SetPoint

[PCS_RTE-F16z3.USetPointStep]
job_name = PCS F16-Zone3 (Power Park Modules) - Voltage Setpoint Step
TSO_model = RefTracking_1Line_InfBus
Omega_model = SetPoint
```

`TSO_model` and `Omega_model` select the grid DyCoV simulates on the TSO
side and the frequency reference of the units; together they are the kind of
test. Take them from this table:

| Kind of recorded test | `TSO_model` | `Omega_model` | Benchmark name |
|---|---|---|---|
| Active, reactive or voltage setpoint step | `RefTracking_1Line_InfBus` | `SetPoint` | free |
| Three-phase fault on the grid near the PDR | `Fault_4Lines_InfBus` | `SetPoint` | free |
| Voltage dip imposed by the grid | `GridVWDisturbance_InfBusFromTab` | `InfiniteBus` | must be `GridVoltageDip` |
| Voltage swell imposed by the grid | `GridVWDisturbance_InfBusFromTab` | `InfiniteBus` | must be `GridVoltageSwell` |
| Frequency ramp imposed by the grid | `GridVWDisturbance_1Line_InfBus` | `Ramp` | free |
| Islanding on a load | `Islanding_2Loads_SynchCond` | `DYNModelOmegaRef` | free |

The names are free except for the dip and the swell: the voltage profile the
grid imposes is a table DyCoV ships with the PCS under the name of the
benchmark, so those two must be named `GridVoltageDip` and `GridVoltageSwell`.

The setpoint steps are the tests a commissioning can apply on purpose; the
other kinds are grid events the installation went through while recording,
declared the same way.

---

## 5. Step 2 — One operating condition per active power level

Each benchmark runs at the three active power levels the fiche fixes, so it
has three operating conditions. Name them after the level:

```ini
[PCS-OperatingConditions]
PCS_RTE-F16z3.PSetPointStep = Pmin,P50,Pmax
PCS_RTE-F16z3.USetPointStep = Pmin,P50,Pmax
```

A grid event is recorded at whatever level the installation was running at:
declare the levels you have a record for.

Every operating condition is written in three sections. This step writes
them for a setpoint step; [step 3](#6-step-3--the-other-kinds-of-test) gives
what changes for the other kinds. The first section describes the test:

```ini
[PCS_RTE-F16z3.PSetPointStep.Pmax]
# Every declared test is reported with the same template
report_name = report.F16z3.DeclaredTest.tex
# Tolerance for reference tracking tests should be adapted to the magnitude of the step change
reference_step_size = 0.4*Pmax
# Is this a bolted fault OC?
bolted_fault = false
# Is this a Hi-Z fault OC?
hiz_fault = false
# OperatingCondition type: PSetpoint, QSetpoint, USetpoint or Others
setpoint_change_test_type = PSetpoint
```

| Key | Meaning |
|---|---|
| `report_name` | Always `report.F16z3.DeclaredTest.tex`: the template DyCoV ships for a declared test. |
| `reference_step_size` | Size of the step, used to frame the figures around it. It takes no part in the checks. |
| `bolted_fault`, `hiz_fault` | `true` only for a recorded three-phase fault; DyCoV then searches the fault impedance. |
| `setpoint_change_test_type` | The control mode the model must be in for the test: `PSetpoint`, `QSetpoint`, `USetpoint`, or `Others` for every kind that is not a setpoint step. If the model's parameters do not implement that mode, the test is reported as *Not applicable*. |

The `.Model` section is the operating point and the grid **during the test**:

```ini
[PCS_RTE-F16z3.PSetPointStep.Pmax.Model]
# The grid during the test: the reactance of the line to the PDR, in pu (line_XPu),
# or the short-circuit impedance seen from the PDR (Zcc)
line_XPu = b
# PDR point: the active power level the DTR fixes, and the recorded Q and U
pdr_P = Pmax
pdr_Q = 0
pdr_U = Udim
```

- `line_XPu` is the reactance of the line between the grid and the PDR, in pu
  of the installation; `a` and `b` are the two values the DTR tabulates by
  connection voltage, which I16 uses. Write the value measured or estimated
  for the day of the test. `Zcc` (short-circuit impedance) and `SCR` are
  accepted instead.
- `pdr_P` is the level the fiche fixes: `Pmin`, `0.5*Pmax` and `Pmax` (for
  storage `PmaxConsumption`, `0.5*PmaxConsumption`, `0.5*PmaxInjection` and
  `PmaxInjection`).
- `pdr_Q` and `pdr_U` are the reactive power and the voltage recorded before
  the event.

Values follow the grammar `[±factor*]Name`, where `Name` is one of `Pmax`,
`Pmin`, `Qmax`, `Qmin`, `Snom`, `Udim` or `Unom`, or a plain number in pu:
`Pmax`, `-0.5*Pmax`, `0.1*Qmax`, `1.02*Unom`, `0.98`.

The `.Event` section is what was applied, when:

```ini
[PCS_RTE-F16z3.PSetPointStep.Pmax.Event]
# Event connected to setpoint magnitude
connect_event_to = ActivePowerSetpointPu
# Instant of time at which the event starts
sim_t_event_start = 20
# Duration of the event or fault
#fault_duration =
# Event setpoint step value
setpoint_step_value = -0.4*Pmax
```

| Key | Meaning |
|---|---|
| `connect_event_to` | The magnitude the event drives, which is also the *controlled magnitude* the tracking tests look at: `ActivePowerSetpointPu`, `ReactivePowerSetpointPu`, `VoltageSetpointPu` or `NetworkFrequencyPu`. |
| `sim_t_event_start` | Instant of the event in the simulation, in seconds. It must be the same instant the record's `.dict` declares, so that both curves are aligned. |
| `fault_duration` | Duration of a fault, a dip, a swell or a ramp, in seconds. Leave it out for a setpoint step. |
| `setpoint_step_value` | Size and sign of the step, with the same grammar as above. The ME, MAE and MXE of the controlled magnitude are expressed in pu of this value. |

Write the two other levels (`P50`, `Pmin`) the same way, changing `pdr_P` and,
when the sign of the step depends on the level, `setpoint_step_value`. A
reactive power step is declared with `QSetpoint`, `ReactivePowerSetpointPu`
and a step in pu of the 100 MVA base; a voltage step with `USetpoint`,
`VoltageSetpointPu` and a step in pu of the nominal voltage (`0.02*Udim`).

---

## 6. Step 3 — The other kinds of test

A grid event is declared with the same three sections. What changes is the
test type, the grid keys and the event keys; everything not shown stays as in
step 2.

**Three-phase fault.** The fault sits on one of four parallel lines, which
opens at the end of the fault. `bolted_fault = true` makes DyCoV search the
fault impedance that leaves the residual voltage under the bolted-fault
threshold of the installation's size. `fault_duration` is the clearing time
recorded.

```ini
[PCS_RTE-F16z3.ThreePhaseFault.Pmax]
report_name = report.F16z3.DeclaredTest.tex
bolted_fault = true
hiz_fault = false
setpoint_change_test_type = Others

[PCS_RTE-F16z3.ThreePhaseFault.Pmax.Model]
line_XPu = 3*b
pdr_P = Pmax
pdr_Q = 0
pdr_U = Udim

[PCS_RTE-F16z3.ThreePhaseFault.Pmax.Event]
sim_t_event_start = 30
fault_duration = 0.150
```

**Voltage dip.** The voltage at the PDR follows the recorded profile: the
pre-fault value, `u_fault` for `fault_duration`, a linear recovery to 0.85 pu
reached `delta_t_rec2` seconds after the event, held until `delta_t_rec3`,
then the pre-fault value. The benchmark is named `GridVoltageDip`.

```ini
[PCS_RTE-F16z3.GridVoltageDip.Pmax]
report_name = report.F16z3.DeclaredTest.tex
bolted_fault = false
hiz_fault = false
setpoint_change_test_type = Others

[PCS_RTE-F16z3.GridVoltageDip.Pmax.Model]
Zcc = true
pdr_P = Pmax
pdr_Q = 0
pdr_U = Udim
u_fault = 0.05
delta_t_rec2 = 1.15
delta_t_rec3 = 5.0

[PCS_RTE-F16z3.GridVoltageDip.Pmax.Event]
sim_t_event_start = 20
fault_duration = 0.15
```

**Voltage swell.** The voltage rises to 1.3 pu for `fault_duration`, holds
1.25 pu until `delta_t_rec2` and 1.15 pu until `delta_t_rec3`; the levels are
those of the DTR profile, only the instants are declared. The benchmark is
named `GridVoltageSwell`, and `pdr_Q` is the reactive power recorded before
the swell (`Qmax` or `Qmin` in I16).

```ini
[PCS_RTE-F16z3.GridVoltageSwell.Pmax]
report_name = report.F16z3.DeclaredTest.tex
bolted_fault = false
hiz_fault = false
setpoint_change_test_type = Others

[PCS_RTE-F16z3.GridVoltageSwell.Pmax.Model]
Zcc = true
pdr_P = Pmax
pdr_Q = Qmax
pdr_U = Udim
delta_t_rec2 = 2.5
delta_t_rec3 = 30.0

[PCS_RTE-F16z3.GridVoltageSwell.Pmax.Event]
sim_t_event_start = 20
fault_duration = 0.05
```

**Frequency ramp.** The ramp DyCoV simulates is fixed by its `Ramp` frequency
model: +0.01 pu (0.5 Hz) over 0.25 s, starting at 20 s. A record can be
declared as this kind only if it shows that excursion, and the event keys
describe that same ramp to the tests.

```ini
[PCS_RTE-F16z3.GridFreqRamp.Pmax]
report_name = report.F16z3.DeclaredTest.tex
reference_step_size = 0.01
bolted_fault = false
hiz_fault = false
setpoint_change_test_type = Others

[PCS_RTE-F16z3.GridFreqRamp.Pmax.Model]
SCR = 3
pdr_P = Pmax
pdr_Q = 0
pdr_U = Udim

[PCS_RTE-F16z3.GridFreqRamp.Pmax.Event]
connect_event_to = NetworkFrequencyPu
sim_t_event_start = 20
fault_duration = 0.250
setpoint_step_value = 0.01
```

**Islanding.** The installation feeds a load equal to its operating point,
with a line to a small inertial grid; the load is stepped at the event.

```ini
[PCS_RTE-F16z3.Islanding.Pmax]
report_name = report.F16z3.DeclaredTest.tex
bolted_fault = false
hiz_fault = false
setpoint_change_test_type = Others

[PCS_RTE-F16z3.Islanding.Pmax.Model]
line_XPu = b
pdr_P = Pmax
pdr_Q = 0
pdr_U = Udim

[PCS_RTE-F16z3.Islanding.Pmax.Event]
sim_t_event_start = 20
step_event_PPu = 0.1*Pmax
step_event_QPu = 0.04*Pmax
```

---

## 7. Step 4 — The records

One record per operating condition, named after it:

```text
PCS_RTE-F16z3.<Benchmark>.<OperatingCondition>.csv
PCS_RTE-F16z3.<Benchmark>.<OperatingCondition>.dict
```

The `.dict` file carries the metadata of the record and maps the DyCoV
signal names to the columns of the file:

```ini
[Curves-Metadata]
# True when the reference curves are field measurements
is_field_measurements = True
# Instant of time at which the event or fault starts
sim_t_event_start = 20.0
# Duration of the event or fault
fault_duration = 0.0
# Frequency sampling of the reference curves
frequency_sampling = 15.0

[Curves-Dictionary]
time = time
BusPDR_BUS_Voltage = BusPDR_BUS_Voltage
BusPDR_BUS_ActivePower = BusPDR_BUS_ActivePower
BusPDR_BUS_ReactivePower = BusPDR_BUS_ReactivePower
BusPDR_BUS_ActiveCurrent = BusPDR_BUS_ActiveCurrent
BusPDR_BUS_ReactiveCurrent = BusPDR_BUS_ReactiveCurrent
NetworkFrequencyPu = NetworkFrequencyPu
```

- `is_field_measurements = True` says the record is a measurement. It
  selects the field-measurement tolerances of the fault and dip checks; the
  tolerances of the setpoint-tracking checks are fixed by the fiche, not by
  this flag.
- `sim_t_event_start` and `fault_duration` locate the event in the record.
  They define the *before*, *during* and *after* windows of every check:
  the same instant as the declaration, and the duration of a fault, a dip,
  a swell or a ramp (0 for a step or an islanding).
- Zone 3 compares six curves: the voltage, active and reactive power, active
  and reactive current at the PDR, and the network frequency. A record that
  lacks one of them is reported as *Missing some reference curves* for the
  tests that need it.

`CurvesFiles.ini` lists the records of the directory:

```ini
[Curves-Files]
PCS_RTE-F16z3.PSetPointStep.Pmin = PCS_RTE-F16z3.PSetPointStep.Pmin.csv
PCS_RTE-F16z3.PSetPointStep.P50 = PCS_RTE-F16z3.PSetPointStep.P50.csv
PCS_RTE-F16z3.PSetPointStep.Pmax = PCS_RTE-F16z3.PSetPointStep.Pmax.csv
```

The formats and the signal processing applied to a record are described in
[Preparing inputs](preparing_inputs.md).

---

## 8. Step 5 — Activate the compliance tests

The compliance tests are activated in the `[Model-Validations]` section. Each
key names the benchmarks the test applies to, as a comma-separated list of
`PCS.Benchmark`; a benchmark not listed under a key is not checked for it.

The set the fiche prescribes for a **setpoint step** is:

```ini
[Model-Validations]
# Step-response characteristics of the controlled magnitude, simulated vs recorded
reaction_time = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
rise_time = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
settling_time = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
overshoot = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
# ME, MAE and MXE of the controlled magnitude, per window, against the F16 table
setpoint_tracking_controlled_magnitude = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
# Mean absolute error in the final steady state, below 1 % of the magnitude
mean_absolute_error_power_1P = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
mean_absolute_error_injection_1P = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
mean_absolute_error_voltage = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
```

What each one checks, in short (the exact definitions, the curves compared
and the configuration keys are in the *Compliance tests* chapter of the user
manual):

| Key | Checks | Needs |
|---|---|---|
| `reaction_time` | The time to reach 10 % of the step, simulated vs recorded, within `thr_reaction_time` (10 %). | A step on the controlled magnitude. |
| `rise_time` | The time to reach 90 % of the step, within `thr_rise_time` (10 %). | Idem. |
| `settling_time` | The time to enter and stay in the tolerance band of the final value, within `thr_settling_time` (10 %). | Idem. |
| `overshoot` | The excess of the maximum over the final value, within `thr_overshoot` (15 %). | Idem. |
| `setpoint_tracking_controlled_magnitude` | ME, MAE and MXE of the controlled magnitude in each window, in pu of the step, against the F16 table. | A step on the controlled magnitude. |
| `mean_absolute_error_power_1P` | MAE of P and Q in the final steady state below `thr_final_ss_mae` (1 %), with the simulation stable. | Any event. |
| `mean_absolute_error_injection_1P` | The same for Ip and Iq. | Any event. |
| `mean_absolute_error_voltage` | The same for the voltage. | Any event. |

The other kinds of test activate the tests of their event instead of the
tracking ones; the steady-state errors apply to every kind:

| Kind of test | Tests to activate |
|---|---|
| Three-phase fault, voltage dip | `voltage_dips_active_power`, `voltage_dips_reactive_power`, `voltage_dips_active_current`, `voltage_dips_reactive_current`, `active_power_recovery`, the three `mean_absolute_error_*` |
| Voltage swell, islanding | The four `voltage_dips_*`, the three `mean_absolute_error_*` |
| Frequency ramp | `ramp_time_lag`, `ramp_error`, `settling_time`, `overshoot`, the four `voltage_dips_*`, `mean_absolute_error_power_1P`, `mean_absolute_error_injection_1P` |

| Key | Checks | Needs |
|---|---|---|
| `voltage_dips_active_power`, `voltage_dips_reactive_power`, `voltage_dips_active_current`, `voltage_dips_reactive_current` | ME, MAE and MXE of P, Q, Ip and Iq in each window, against the fault and dip tables (field-measurement table when `is_field_measurements = True`). | A fault, dip, swell, ramp or islanding with its `fault_duration`. |
| `active_power_recovery` | The time to recover 90 % of the pre-fault active power, simulated vs recorded, within the lesser of 10 % and 100 ms. | A fault or a dip. |
| `ramp_time_lag`, `ramp_error` | Time lag and value error of the response to a frequency ramp, within `thr_ramp_time_lag` and `thr_ramp_error` (10 %). | `connect_event_to = NetworkFrequencyPu` with a `fault_duration` equal to the ramp duration. |
| `setpoint_tracking_active_power`, `setpoint_tracking_reactive_power` | ME, MAE and MXE of P or Q, also in pu of the step, besides the controlled magnitude. | A setpoint step. |
| `response_time` | The time to enter the tolerance band of the final value is computed, without a threshold or a verdict. | A step on the controlled magnitude. |

The tolerances live in the `[GridCode]` section of the configuration. The
F16 table for the controlled magnitude is the `thr_FT_reftrack_*` family,
selected by the `setpoint_tracking_thresholds = FT` key of the shipped
`PCS_RTE-F16z3` description; you do not need to write it. See *Configuring
KPI thresholds* in the user manual to change a tolerance.

---

## 9. Step 6 — Choose the figures of the report

The `[ReportCurves]` section names, for each figure, the benchmarks it is
drawn for. The six figures of the connection point apply to every kind of
test:

```ini
[ReportCurves]
fig_P = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
fig_Q = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
fig_Ip = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
fig_Iq = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
fig_Ustator = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
fig_V = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep
```

| Figure | Draws | Kinds of test |
|---|---|---|
| `fig_V` | Voltage at the PDR. | Every kind |
| `fig_P`, `fig_Q` | Active and reactive power at the PDR, with the setpoint overlaid in a setpoint step. | Every kind |
| `fig_Ip`, `fig_Iq` | Active and reactive current at the PDR. | Every kind |
| `fig_Ustator` | Magnitude controlled by the plant voltage regulation and its setpoint. | Every kind |
| `fig_I` | Current magnitude at the generator terminals. | Fault, dip, swell |
| `fig_UIt` | Voltage at the terminals of the units, with its setpoint when the converter controls that node. | Fault, dip, swell |
| `fig_Tap` | Tap position of the main transformer. | Fault |
| `fig_WRef` | Network frequency. | Frequency ramp, islanding |
| `fig_SyncCondP`, `fig_SyncCondQ`, `fig_SyncCondFreq` | Active power, reactive power and frequency of the inertial grid of the island. | Islanding |
| `fig_LoadP`, `fig_LoadQ` | Active and reactive power of the stepped load. | Islanding |

Every figure also draws the record, the exclusion windows around the event
and the markers of the checked characteristics.

---

## 10. Run it and read the report

```bash
dycov validate -m Dynawo ReferenceCurves -o Results -p PCS_RTE-F16z3
```

Without `-p` the run also covers PCS I16, which needs its own reference
curves. The summary lists every declared test with its verdict:

```text
Producer  PCS_RTE-F16z3  PSetPointStep  Pmin  Compliant
Producer  PCS_RTE-F16z3  PSetPointStep  P50   Non-compliant
Producer  PCS_RTE-F16z3  USetPointStep  Pmax  Not applicable test
```

- *Compliant* / *Non-compliant*: every activated test passed, or at least one
  failed. The report has a section per test, *Recorded test
  &lt;Benchmark&gt;.&lt;OperatingCondition&gt;*, with the figures, the errors
  against their tolerances, the step-response characteristics and the
  steady-state error.
- *Not applicable test*: the model is not in the control mode
  `setpoint_change_test_type` asks for.
- *Missing some reference curves*: the record is missing, or lacks a curve the
  activated tests compare.
- *Invalid test*: the simulation did not reach a steady state.

---

## 11. A complete example

The `Wind/IECB2015` example ships a complete declaration,
`examples/Model/Wind/IECB2015/ReferenceCurves/F16Description.ini`, with active
and voltage setpoint steps at the three levels and their twelve records; the
`BESS/WECC` example does the same for storage, at its four levels. The tests
are invented for the example and the records are the tool's own simulations
anonymized as measurements, so they show the mechanics, not a real
commissioning.

The shipped template, with every key of this tutorial commented out and
explained, is `src/dycov/templates/PCS/model/<technology>/PCS_RTE-F16z3/PCSDescription.ini`
in the source tree, and its copy in your configuration directory.

---

## 12. Common issues

- **`no test declared, nothing to validate`**: the file is not at the root of
  the reference curves directory, is not named `*Description.ini`, or its
  `[PCS-Benchmarks]` does not name `PCS_RTE-F16z3`.
- **Every test is *Not applicable***: `setpoint_change_test_type` asks for a
  control mode the model's `.par` does not implement. Check the control-mode
  parameters of the model against the mode of the test.
- **Large errors right after the event**: `sim_t_event_start` of the
  declaration and of the record's `.dict` differ, so the two curves are
  compared out of phase. A frequency ramp always starts at 20 s.
- **Errors far larger than expected everywhere**: `setpoint_step_value` does
  not match the step actually applied; the errors of the controlled magnitude
  are expressed in pu of that value.
- **A dip or a swell does not simulate, Dynawo missing `TableInfiniteBus.txt`**:
  the benchmark is not named `GridVoltageDip` or `GridVoltageSwell`.
- **`Pmin` resolves to 0**: `p_min_injection_at_PDR` is missing from
  `Producer.ini`.
