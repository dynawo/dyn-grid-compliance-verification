# PCS 

Contains the configuration files with the description of the PCS. And it is
made up of 3 directories:
* **model/PPM**: DyCoV Model Validation tests (Power Parks)
* **performance/PPM**: Electric Performance tests (Power Parks)
* **performance/SM**: Electric Performance tests (Synchronous Machines)

# Modify an existing PCS

1. Create the PCS directory, if it does not exist, of the desired verification mode.
2. Enter to the PCS directory of the desired verification mode.
3. Create the INI file with the same name as the PCS, if it does not exist, and edit it.
4. Add the new benchmarks to the *PCS-Benchmarks* section, if it is desired, and the configuration
of the new benchmarks in their corresponding sections.
   ```
    [PCS-Benchmarks]
    DummySample = Benchmark1,Benchmark2

    [DummySample.Benchmark2]
    job_name = Pcs - Synchronous Machine
    TSO_model = RefTracking_1Line_InfBus
    Omega_model = DYNModelSPOmega
   ```
5. Add the new Operating Conditions to the *PCS-OperatingConditions* section, if it is desired,
and the configuration of the new benchmarks in their corresponding sections.
   ```
    [PCS-OperatingConditions]
    DummySample.Benchmark1 = OC1,OC2
    DummySample.Benchmark2 = OC3

    [DummySample.Benchmark1.OperatingCondition1]
    report_name = report.Benchmark1.OperatingCondition1.tex
    # Uncomment only the desired option (line_XPu, SRC, or Zcc). 
# If there is more than one uncommented option, the tool will use the first option according to the order:
#    1. line_XPu
#    2. SRC
#    3. Zcc
# Use when the reactance of the line connected to the PDR point is specified in the DTR
# Used in the DTR fiches I2, I3, I4, I5 and I8 and their equivalents in the DTR Fiche I16 zone 3
    line_XPu = a
    # PDR point
    pdr_P = Pmax
    pdr_Q = 0
    pdr_U = Udim
    # Event definition
    connection_event = AVRSetpointPu
    time_event = 20
    value0_event = U0
    height_event = 0.02*Udim
    reference_step_size = 0.02
   ```
6. Modify the Validations section to select the compliance that the new benchmarks must meet.
Note: for SM and PPM performance the section is *Performance-Verifications* and for mode validation
the section is *Model-Validations*
   ```
    [Performance-Validations]
    # Analyses to perform in every pcs
    # Static difference between the controlled quantity injected into the primary voltage regulator and the voltage adjustment setpoint
    static_diff = DummySample.Benchmark1
    # Time at which the power supplied V stays within the +/-5% tube centered on the final value of V
    time_5U = DummySample.Benchmark1
   ```
7. Modify the *ReportCurves* section to select the figures that will be shown in the report for the new 
benchmarks.
   ```
    [ReportCurves]
    fig_P = DummySample.Benchmark1
    fig_Q = DummySample.Benchmark1
    fig_Ustator = DummySample.Benchmark1
    fig_V = DummySample.Benchmark1
    fig_W = DummySample.Benchmark1
    fig_Theta =
    fig_WRef =
    fig_I =
    fig_Tap =
   ```
   
# Add a new PCS

1. Create the PCS directory of the desired verification mode.
2. Enter to the PCS directory of the desired verification mode.
3. Create the INI file with the same name as the PCS, and edit it.
4. Add the PCS section and its configuration
   ```
    [DummySample]
    # Report name
    report_name = report_I.tex
   ```

From this point follow the steps indicated to modify a PCS. 


