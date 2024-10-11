
=========================================

Fiche X

Detailed description of all Tests

=========================================


# Introduction

This document will spell out the detailed specifications of the tests performed
within `FicheX`, which is focused on **RMS-model validation** (in the context of
dynamic performance testing of generation units and power farms).

Most of the tests are derived from IEC Standards `IEC 61400-27-2` and `IEC
61400-21-2`.

Tests are to be executed at two different levels:

  1. Park-level tests (a.k.a. "Zone 3" in the DTR Fiche X)
  2. Unit-level tests (a.k.a. "Zone 1" in the DTR Fiche X, individual wind turbines)
       - Unit-level plus any Q-compensation equipment at the PDR, if present
         (a.k.a. "Zone 1*")


Preliminary plan in the DRAFT FicheX:

   1. Park-level tests: like those in Fiches: 
      - I2: stability test
      - I5: fault ride-through
      - I6: grid voltage drop
      - I7: grid voltage surge
      - I10: islanding event

   2. Unit-level tests: new tests:
      - Transient faults
      - Ramping and step-change events (V, P, Q)
      - Permanent faults


### QUESTIONS TO BE DISCUSSED:

> For validation of Power Park models, the IEC standard (Section 8) only
> requires three tests (dyn response to P/Q or V control setpoint). But the
> DRAFT FicheX talks about several others. Why? What is going to be included in
> the DTR?

> For validation of WT-unit models, the IEC standard (Section 7) lists many
> (sections 7.2--7.8) and that list seems to be different than the tests listed
> in the DRAFT FicheX.  Which tests are going to go in the final FicheX?




# Test IEC_PPM1: Dynamic Response to step changes in active power control 

## GridTopology
Grid-side: Infinite bus plus a line with configurable reactance X. (TEMP: use Xa for
now)

Producer's side: the full PPM model.


## OperatingPoint (a): step-down the P setpoint

P setpoint initially at `P = 0.6 P_maxunite`  
P setpoint step of 0.4, that is: `P = 0.2 P_maxunite`  
Note that `P_maxunite` is the global Pmax of the whole Power Park.

What to show/measure:
- Curves of Psetpoint and P at the PDR (note: `P_available` doesn't make sense
  in simulations)
- Reaction time, Rise time, Overshoot/Undershoot, and Settling Time of P curve
  (see definitions in the illustration in the IEC std).
- Thresholds used as criteria for pass/fail: TO BE DEFINED


## OperatingPoint (b): step-up in P setpoint

Same as in (a), but with these settings:
P setpoint initially at `P = 0.2 P_maxunite`  
P setpoint step increase of 0.4, that is: `P = 0.6 P_maxunite`  
Note that `P_maxunite` is the global Pmax of the whole Power Park.





# Test IEC_PPM2: Dynamic Response to step changes in reactive power control 

## GridTopology
TODO

## OperatingPoint (a): step-down Q setpoint


## OperatingPoint (b): step-up in Q setpoint


