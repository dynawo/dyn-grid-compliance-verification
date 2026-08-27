# Signal processing workflow

(c) 2024 RTE — Developed by Grupo AIA

Canonical description of the signal-processing pipeline that DyCoV applies to the curves used in
RMS model validation, and of the choices and adaptations made with respect to IEC 61400-27-2.
This document describes *what is implemented and why each deviation was adopted*; the theoretical
rationale (DSP background, filter comparisons, phasor-extraction analysis) is developed in the
companion technical note.

## Related resources

- `docs/signals_technote/signals_technote.tex` — *"Proper signal-processing techniques for the
  purposes of comparing transient signals"* (2023). Frozen reference: analyzes the IEC 61400-27-2
  prescriptions and justifies the deviations adopted here (interpolator choice, ordering of
  filtering vs. resampling, filter type, cutoff frequency).
- Developer manual, *Configuration* section — reference for every `[GridCode]` signal-processing
  parameter mentioned below.
- Code: `src/dycov/sigpro/` (pipeline stages), `src/dycov/curves/manager.py`
  (`CurvesManager.apply_signal_processing`, the orchestrator that fixes the stage order).

## Scope

The pipeline runs only for **model validation**, where a *calculated* set of curves (Dynawo
simulation or user-provided) is compared point-wise against a *reference* set (EMT simulation or
field measurements). It is invoked from `validation/model.py` via
`CurvesManager.apply_signal_processing` (`curves/manager.py`).

**Performance verifications** apply no signal processing: only the calculated curves are
validated, and the optional complementary curves are shown in the report as-is, never processed
nor validated.

## Pipeline

The stages below run in this exact order; the order is load-bearing (see *Adaptations* table).

### 1. EMT → RMS positive-sequence conversion (reference curves only)

`sigpro.ensure_rms_signals` (`sigpro/sigpro.py`). Columns named `*_a`, `*_b`, `*_c` are treated as
three-phase EMT waveforms and converted to a positive-sequence RMS signal: the phasor of each
phase is extracted with a moving-window STFT taking the bin closest to the 50 Hz fundamental —
the no-frequency-tracking approach of IEC 61400-27-2 Annex C, which the technote found to behave
better around transients than frequency-tracking variants — then the symmetrical components are
built and the magnitude scaled by 1/√2. Columns already in RMS form pass through untouched.

### 2. First resampling: fixed time step, per set

`sigpro.resample_to_fixed_step`. Dynawo uses variable-step integrators, so each set of curves is
independently resampled to a fixed step using **monotone piece-wise interpolation (PCHIP)**,
which cannot overshoot at sharp transitions (cubic splines or FFT-based resamplers would ring).
Repeated time points (emitted by the solver at events) are removed first. The new step is the
minimum step observed in the signal's own grid, capped at 1 ms (`fs_max = 1000 Hz`): each set
keeps its own native resolution — there is deliberately **no** common grid yet.

### 3. Event-time alignment

`sigpro.apply_time_shift`. When the event start time of the reference curves differs from the
simulated one, the calculated curves are shifted so both events coincide, making the later
point-wise comparison meaningful.

### 4. Windowing

`sigpro/signal_windows.py` (`calculate`). Two families of pre/during/post windows are derived
from the event start time and duration (an event outlasting the simulation is treated as
permanent: no *during* window):

- **`sigpro` windows** — raw split at the event boundaries `[t0, t_fault]`, `[t_fault, t_clear]`,
  `[t_clear, t_end]`. Used only to drive per-window filtering (stage 5).
- **`validate` windows** — the windows over which compliance KPIs are computed. They apply
  exclusion zones on top of the raw boundaries:
  - *before*: ends at `t_fault − t_integrator_tol − t_faultLPF_excl`, with a fixed length of 1 s
    (DTR Fiche I16 prescribes 1 s of established regime before the event);
  - *during*: starts at `t_fault + t_integrator_tol + t_faultQS_excl`, ends
    `t_windowLPF_excl_end` before clearing;
  - *after*: starts at `t_clear + t_integrator_tol + t_clearQS_excl`, ends
    `t_windowLPF_excl_end` before the end of the signal.

  `t_integrator_tol` absorbs Dynawo's event-timing jitter. The `*QS_excl` exclusions are the
  IEC/DTR quasi-stationary exclusions; the `*LPF_excl` ones exist to discard the boundary
  artifacts of the low-pass filter (a DyCoV addition, see below). For setpoint-tracking tests on
  the controlled magnitude, the QS exclusions collapse to the LPF boundary exclusion, since the
  controlled quantity is expected to react immediately.

### 5. Low-pass filtering

`sigpro.filter_curves` / `sigpro/lp_filters.py`. Both sets are filtered with the same filter:
a **second-order critically-damped biquad** (the IEC 61400-27-2 choice, kept because it has
minimal step-response ringing) with cutoff `cutoff = 15 Hz` (IEC value, configurable). Bessel,
Butterworth and Chebyshev-I implementations exist for experimentation.

DyCoV's application of the filter differs from a naive reading of the standard:

- **Zero-phase filtering**: the filter runs forward+backward (`scipy.signal.filtfilt`, Gustafsson
  boundary handling), so it introduces no time lag between filtered and unfiltered features.
- **Per-window filtering** (default): each `sigpro` window is filtered separately, so the filter
  never smears the signal across the event discontinuities; the residual artifacts at window
  boundaries are then excluded from validation via the `*LPF_excl` zones of stage 4.
  `disable_window_filtering = True` reverts to whole-signal filtering.
- **Flat signals are not filtered** (constant or peak-to-peak < 1e-4): the filter would only
  create artifacts and break the flat-curve sanity check performed at report time.
- `disable_LP_filtering` (Debug section) bypasses filtering entirely.

### 6. Second resampling: common time grid

`sigpro.resample_to_common_tgrid`. Both sets are resampled (PCHIP again) onto one shared grid
with step `t_com = 2 ms`, trimmed to their overlapping time range (the *after* validate-windows
are re-trimmed accordingly). For most signals this is a **downsampling**, which is only safe now
that both signals are band-limited by stage 5. The sanity check
`check_sampling_interval` enforces the Nyquist condition `t_com < 1 / (2 · cutoff)`.

### 7. Consumption

The compliance checks compute the error indicators (MXE, ME, MAE) and step-response
characteristics per validate-window and over the whole curve; a stability sanity check
(`check_pre_stable`) verifies the *before* window is in steady state. The final report plots the
complete processed curves.

## Adaptations with respect to IEC 61400-27-2

| Topic | IEC 61400-27-2 | DyCoV | Motivation |
|---|---|---|---|
| Interpolation method | Not specified | Monotone PCHIP everywhere | No overshoot/ringing at sharp transitions; time-domain fidelity (technote §3) |
| Order of operations | Common resampling suggested before filtering | Per-set resampling → filter → common downsampling | Downsampling before band-limiting would alias (technote §4–5) |
| Filter application | Single-pass (causal) implied | Zero-phase `filtfilt`, Gustafsson padding | No filter-induced time shift between compared signals |
| Filtering extent | Whole signal | Per pre/during/post window + LPF boundary exclusions | Keeps the filter from smearing event discontinuities into the windows |
| Filter type | 2nd-order critically-damped | Same (default) | Kept: minimal step-response ringing; alternatives available for study |
| Cutoff frequency | 15 Hz | 15 Hz default, configurable | Kept for standard compliance; the technote argues RMS simulations are credible well above 15 Hz |
| QS exclusion zones | ≤ 140 ms after fault, ≤ 500 ms after clearing | 20 ms / 60 ms (RTE PCS I16 values, configurable) | DTR prescription; IEC values are upper bounds motivated by WT-specific model limits |
| Window lengths | Not fixed | 1 s pre-event (DTR); post window runs to the end of the simulation (DTR asks for 5 s of post-event data) | DTR Fiche I16 prescription |
| Event alignment | Not addressed | Calculated curves time-shifted to the reference event time | Field/EMT references rarely share the simulation's event timestamp |
| Setpoint tracking | Not addressed (wind-fault oriented) | QS exclusions collapse to the LPF exclusion for the controlled magnitude | The controlled quantity must be observable immediately after the step |

## Configuration summary

All knobs live in `[GridCode]` unless noted: `t_com`, `cutoff`, `t_integrator_tol`,
`t_windowLPF_excl_start`, `t_windowLPF_excl_end`, `t_faultLPF_excl`, `t_faultQS_excl`,
`t_clearQS_excl`, `disable_window_filtering`, and `disable_LP_filtering` (`[Debug]`). Defaults
and constraints are documented in the developer manual's *Configuration* section.
