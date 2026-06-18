# rte-validation-sigpro

Signal processing module for the reference signals. It performs the following steps:

`abc -> phasors -> rms -> resampling -> lowpass filtering`

The lowpass filtering is not implemented yet.

The entry point to the pipeline is the function `abc_to_psrms` which takes a list of three signals `[a, b, c]` and a sampling frequency, and returns the DyCoV value of the positive sequence.

The function `gen_abc` generates a mockup three-phase signal of 1 sec duration with N samples. 

Summary of inputs and outputs: 

- `gen_abc`
    - in: number of samples (integer)
    - out: abc signals (list of vectors), sampling frequency (integer), time steps (vector)
- `abc_to_psrms`
    - in: abc signals, sampling frequency
    - out: positive sequence DyCoV signal (vector)
- `resample`
    - in: positive sequence DyCoV signal, time steps, new number of samples  (integer)
    - out: resampled signal (vector)
- `lowpass_filter`
    - in: resampled signal, cutoff frequency (integer)
    - out: filtered signal (vector)

Sample execution script
```python
abc, fs, tsteps = gen_abc(100)
ps_rms = abc_to_psrms(abc, fs)
r = resample(ps_rms, tsteps, 2000)
rf = lowpass_filter(r, 50)
```
