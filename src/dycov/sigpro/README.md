# dycov.sigpro

Signal-processing stages used to prepare the calculated and reference curves for point-wise
comparison in model validation:

- `sigpro.py` — pipeline stages: EMT→RMS positive-sequence conversion (`ensure_rms_signals`),
  fixed-step and common-grid resampling (`resample_to_fixed_step`, `resample_to_common_tgrid`),
  event-time alignment (`apply_time_shift`) and low-pass filtering (`filter_curves`).
- `lp_filters.py` — second-order low-pass filter implementations (critically-damped biquad,
  Bessel, Butterworth, Chebyshev-I) applied zero-phase via `filtfilt`.
- `signal_windows.py` — pre/during/post windows and exclusion zones for filtering and validation.

The stages are orchestrated, in a fixed order, by `CurvesManager.apply_signal_processing`
(`dycov/curves/manager.py`).

The full workflow, and the choices and adaptations made with respect to IEC 61400-27-2, are
documented in `docs/design/Signal_processing_workflow.md`; the theoretical rationale is developed
in `docs/signals_technote/signals_technote.tex`.
