===========================

SIGNAL PROCESSING WORKFLOW

(c) 2024 RTE
Developed by Grupo AIA

===========================

# Model Validation

## Get the curves to process

Read the file containing the **calculated curves**. The curves contained 
in this file come from the result of a dynamic simulation performed 
with Dynawo in the case where the user has entered the modeling of his 
network. If the user has entered 2 sets of curves as inputs to the tool, 
this file contains the producer's curves.

Read the file containing the **reference curves**.

## First resampling: Ensure constant time step signal.

This section consists of 3 steps:

- Convert the EMT signals to RMS, if necessary. Currently this step only 
applies to **reference curves**. (The user can use a set of curves as input to 
the tool, instead of a dynamic model, in this case should this step be applied 
to the **calculated curves**?)

- Resample the curves using common frequency sampling.

- Pass the curves through a low-pass filter, using common cutoff values ​​and 
frequency sampling.

## Second resampling: Ensure same time grid for both signals.

The tool shortens the **calculated and reference curves** to ensure that both 
sets of curves have exactly the same time range.

## Third: Calculate signal windows.

The pre, during and post windows are calculated (pre and post if the event is 
not temporary) taking into account the exclusion ranges for each window, as well 
as the maximum length defined in the standards.

From the sets of curves, the sets of curves are generated for each window 
obtained in the previous step.

## Validation tests

To run the validation tests, all the sets of curves obtained are used: pre, 
during (if it exists), post and the complete curve of each set of the tool 
(calculated and reference).

## Report

Only the complete curves from the **calculated curve** set and the 
**reference curve** set are used to create the final report.

## Roadmap

- Provide a time shift option when comparing two curve sets to synchronize the 
time at which the **reference curve** set event is triggered with the 
**calculated curve** set.


# Performance Verifications

## Get the curves to process

Read the file containing the **calculated curves**. The curves contained 
in this file come from the result of a dynamic simulation performed 
with Dynawo in the case where the user has entered the modeling of his 
network. If the user has entered a set of curves as input to the tool, 
this file contains the producer's curves.

Read the file containing the **complementary curves**. This second set of curves 
will only be shown in the final report together with the calculated curves; 
they will not be validated under any circumstances.

## Validation tests

To run the validation tests, only the **calculated curves** set are used.

## Report

The curves from the **calculated curves** set and the 
**complementary curves** set are used to create the final report.

## Roadmap

- Ensure that the time step signal is constant across all sets of curves, 
if **complementary curves** exist.

- Ensure same time grid for both signals, if **complementary curves** exist.

- Provide a time shift option when there are two curve sets to synchronize the 
time at which the **complementary curves** set event is triggered with the 
**calculated curve** set.
