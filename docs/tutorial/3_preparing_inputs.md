===========================

TUTORIAL

HOW TO PREPARE INPUTS

(c) 2023&mdash;25 RTE  
Developed by Grupo AIA

===========================

--------------------------------------------------------------------------------

#### Table of Contents

1. [The Producer files](#the-producer-files)
   1. [“TSO’s side vs. the Producer’s side”](#tsos-side-vs-the-producers-side)
   2. [The Producer model](#the-producer-model)
   3. [The Producer curves](#the-producer-curves)
2. [The Reference curves](#the-reference-curves)
   1. [The Reference curves structure](#the-producer-curves-structure)
   2. [DICT file](#dict-file)
3. [Generating inputs automatically](#generating-inputs-automatically)
--------------------------------------------------------------------------------

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

## The Producer model

### The Producer model structure

Producer model are a set of files organized in a directory structure such 
as the one shown in this example:

``` 
(dycov_venv) user@dynawo:~/work/MyTests$ tree Dynawo
Dynawo
├── Producer.dyd
├── Producer.par
└── Producer.ini
```

* **Producer.dyd**: 
  File with the producer network definition. In this file the user defines the 
  dynamic models to be used for each equipment on the producer's network, as 
  well as the connectivity between them.

  The following example shows a network consisting of a wind generation plant 
  with an auxiliary load (The full example can be seen at 
  *examples/PPM/Dynawo/SingleAux/IEC2015*):

  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <dyn:dynamicModelsArchitecture xmlns:dyn="http://www.rte-france.com/dynawo">
    <!-- Producer -->
    <dyn:blackBoxModel id="AuxLoad_Xfmr" lib="TransformerFixedRatio" parFile="Producer.par" parId="AuxLoad_Xfmr"/>
    <dyn:blackBoxModel id="Aux_Load" lib="LoadPQ" parFile="Producer.par" parId="Aux_Load"/>
    <dyn:blackBoxModel id="StepUp_Xfmr" lib="TransformerRatioTapChanger" parFile="Producer.par" parId="StepUp_Xfmr"/>
    <dyn:blackBoxModel id="Wind_Turbine" lib="IECWPP4BCurrentSource2015" parFile="Producer.par" parId="Wind_Turbine"/>
    <dyn:connect id1="AuxLoad_Xfmr" var1="transformer_terminal1" id2="BusPDR" var2="bus_terminal"/>
    <dyn:connect id1="StepUp_Xfmr" var1="transformer_terminal1" id2="BusPDR" var2="bus_terminal"/>
    <dyn:connect id1="Aux_Load" var1="load_terminal" id2="AuxLoad_Xfmr" var2="transformer_terminal2"/>
    <dyn:connect id1="Wind_Turbine" var1="WPP_terminal" id2="StepUp_Xfmr" var2="transformer_terminal2"/>
  </dyn:dynamicModelsArchitecture>
  ``` 

  In order for the tool to validate the model, the producer's network must be 
  connected to a bus called **BusPDR**, this bus is defined in the TSO network 
  (**TSO side**), so the user does not have to define it.

  In the previous example, it can be seen how the transformer of the wind 
  generation plant and the auxiliary load are connected to BusPDR, although this 
  equipment is not declared in the file:

  ```xml
    <dyn:connect id1="AuxLoad_Xfmr" var1="transformer_terminal1" id2="BusPDR" var2="bus_terminal"/>
    <dyn:connect id1="StepUp_Xfmr" var1="transformer_terminal1" id2="BusPDR" var2="bus_terminal"/>
  ``` 


* **Producer.par**: 
  The par file contains all the parameters of the producer's network equipment 
  for the simulation.

  The following example shows the parameters to define the auxiliary load of 
  the previous example (The full example can be seen at 
  *examples/PPM/Dynawo/SingleAux/IEC2015*):

  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <parametersSet xmlns="http://www.rte-france.com/dynawo">
    ...
    <set id="AuxLoad_Xfmr">
      <par type="DOUBLE" name="transformer_RPu" value="0.00001"/>
      <par type="DOUBLE" name="transformer_XPu" value="0.0001"/>
      <par type="DOUBLE" name="transformer_BPu" value="0.0"/>
      <par type="DOUBLE" name="transformer_GPu" value="0.0"/>
      <par type="DOUBLE" name="transformer_rTfoPu" value="1.0"/>
    </set>
    ...
  </parametersSet>
  ```

* **Producer.ini**: 
  This file is essential to inform the tool of the model data that cannot be 
  inferred from the curve files.

  The following example shows the model data for a network consisting of a 
  wind generation plant with an auxiliary load (The full example can be seen at 
  *examples/PPM/Dynawo/SingleAux/IEC2015*):

  ```ini
  # p_{max_unite} as defined by the DTR in MW
  p_max = 75
  # u_nom is the nominal voltage in the PDR Bus (in kV)
  # Allowed values: 400, 225, 150, 90, 63 (land) and 132, 66 (offshore)
  u_nom = 225
  # s_nom is the nominal apparent power of all generating units (in MVA)
  # This is the value that will be used for the base conversion in the PDR bus active/reactive power
  s_nom = 100
  # q_max is the maximum reactive power of the generator unit (in MVar)
  q_max = 40
  # q_min is the minimum reactive power of the generator unit (in MVar)
  q_min = -40
  # topology
  topology = S+Aux
  ```

## The Producer curves

### The Producer curves structure

What we call "Producer curves" refers to curves that will be used *instead*
of Dynawo-simulated curves. In other words, this are the curves that will be
compared to the reference curves.

Producer curves are a set of files organized in a directory 
structure similar to reference curves, as seen in this example:

``` 
(dycov_venv) user@dynawo:~/work/MyTests$ tree ProducerCurves
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


# The Reference curves

## The Reference curves structure

Reference curves are a set of files organized in a directory structure such 
as the one shown in this example:

``` 
(dycov_venv) user@dynawo:~/work/MyTests$ tree ReferenceCurves
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

```ini
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

# Generating inputs automatically

In order to facilitate the generation of inputs for the producer, the tool provides a helper that 
guides the user throw the generation of all the files necessary for the simulation of the model.

Below is the execution of the command to generate the inputs to perform a performance check 
for synchronous generation units, the network to be modeled only has one generating unit, and 
has auxiliary load.

```
(dycov_venv) user@dynawo:~$ dycov generate -t S+Aux -v performance_SM -o ../SM_SA
2025-01-23 15:30:18,839 |        dycov.Create input files |       INFO |         input_template.py:   23 | Creating the input DYD file in ../SM_SA.
Edit the Producer.dyd file is necessary to complete each equipment in the model with a dynamic model. Press Enter when finishing editing.
```

In this first step, the tool has copied all the templates to the target directory, and has 
edited the DYD file to generate the desired connectivity:
```
(dycov_venv) user@dynawo:~$ tree ../SM_SA
../SM_SA
├── Producer.dyd
├── Producer.ini
├── Producer.par
└── ReferenceCurves
    ├── PCS_RTE-I10.Islanding.DeltaP10DeltaQ4.dict
    ├── PCS_RTE-I2.USetPointStep.AReactance.dict
    ├── PCS_RTE-I2.USetPointStep.BReactance.dict
    ├── PCS_RTE-I3.LineTrip.2BReactance.dict
    ├── PCS_RTE-I4.ThreePhaseFault.TransientBolted.dict
    ├── PCS_RTE-I6.GridVoltageDip.Qzero.dict
    ├── PCS_RTE-I7.GridVoltageSwell.QMax.dict
    ├── PCS_RTE-I7.GridVoltageSwell.QMin.dict
    └── PCS_RTE-I8.LoadShedDisturbance.PmaxQzero.dict
```

The next step is to manually edit the generated DYD file. As can be seen in the previous 
example, the DYD file has several lines with comments, in these lines the valid dynamic 
models to use instead of the placeholders that the tool has set are indicated:
```xml
<?xml version='1.0' encoding='UTF-8'?>
<dyn:dynamicModelsArchitecture xmlns:dyn="http://www.rte-france.com/dynawo">
  <!--Topology: S+Aux-->
  <dyn:blackBoxModel id="AuxLoad_Xfmr" lib="XFMR_DYNAMIC_MODEL" parFile="Producer.par" parId="AuxLoad_Xfmr"/>
  <dyn:blackBoxModel id="Aux_Load" lib="LOAD_DYNAMIC_MODEL" parFile="Producer.par" parId="Aux_Load"/>
  <dyn:blackBoxModel id="StepUp_Xfmr" lib="XFMR_DYNAMIC_MODEL" parFile="Producer.par" parId="StepUp_Xfmr"/>
  <dyn:blackBoxModel id="Synch_Gen" lib="SM_DYNAMIC_MODEL" parFile="Producer.par" parId="Synch_Gen"/>
  <dyn:connect id1="AuxLoad_Xfmr" var1="transformer_terminal1" id2="BusPDR" var2="bus_terminal"/>
  <dyn:connect id1="StepUp_Xfmr" var1="transformer_terminal1" id2="BusPDR" var2="bus_terminal"/>
  <dyn:connect id1="Aux_Load" var1="load_terminal" id2="AuxLoad_Xfmr" var2="transformer_terminal2"/>
  <dyn:connect id1="Synch_Gen" var1="generator_terminal" id2="StepUp_Xfmr" var2="transformer_terminal2"/>
  <!--Replace the placeholder: 'XFMR_DYNAMIC_MODEL', available_options: ['TransformerFixedRatio', 'TransformerPhaseTapChanger', 'TransformerRatioTapChanger']-->
  <!--Replace the placeholder: 'SM_DYNAMIC_MODEL', available_options: ['GeneratorSynchronousFourWindingsTGov1SexsPss2a', 'GeneratorSynchronousThreeWindingsDTRI8']-->
  <!--Replace the placeholder: 'LOAD_DYNAMIC_MODEL', available_options: ['LoadPQ','LoadAlphaBeta']-->
</dyn:dynamicModelsArchitecture>
```

In this step we are going to modify the file to leave it like the following example:
```xml
<?xml version='1.0' encoding='UTF-8'?>
<dyn:dynamicModelsArchitecture xmlns:dyn="http://www.rte-france.com/dynawo">
  <!--Topology: S+Aux-->
  <dyn:blackBoxModel id="AuxLoad_Xfmr" lib="TransformerFixedRatio" parFile="Producer.par" parId="AuxLoad_Xfmr"/>
  <dyn:blackBoxModel id="Aux_Load" lib="LoadPQ" parFile="Producer.par" parId="Aux_Load"/>
  <dyn:blackBoxModel id="StepUp_Xfmr" lib="TransformerFixedRatio" parFile="Producer.par" parId="StepUp_Xfmr"/>
  <dyn:blackBoxModel id="Synch_Gen" lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a" parFile="Producer.par" parId="Synch_Gen"/>
  <dyn:connect id1="AuxLoad_Xfmr" var1="transformer_terminal1" id2="BusPDR" var2="bus_terminal"/>
  <dyn:connect id1="StepUp_Xfmr" var1="transformer_terminal1" id2="BusPDR" var2="bus_terminal"/>
  <dyn:connect id1="Aux_Load" var1="load_terminal" id2="AuxLoad_Xfmr" var2="transformer_terminal2"/>
  <dyn:connect id1="Synch_Gen" var1="generator_terminal" id2="StepUp_Xfmr" var2="transformer_terminal2"/>
  <!--Replace the placeholder: 'XFMR_DYNAMIC_MODEL', available_options: ['TransformerFixedRatio', 'TransformerPhaseTapChanger', 'TransformerRatioTapChanger']-->
  <!--Replace the placeholder: 'SM_DYNAMIC_MODEL', available_options: ['GeneratorSynchronousFourWindingsTGov1SexsPss2a', 'GeneratorSynchronousThreeWindingsDTRI8']-->
  <!--Replace the placeholder: 'LOAD_DYNAMIC_MODEL', available_options: ['LoadPQ','LoadAlphaBeta']-->
</dyn:dynamicModelsArchitecture>
```

After saving the edited DYD file, press *Enter* in the terminal where the command was 
executed, the tool will validate the DYD file, and modify the PAR file based on 
the dynamic models selected in the DYD file:

```
(dycov_venv) user@dynawo:~$ dycov generate -t S+Aux -v performance_SM -o ../SM_SA
2025-01-23 15:30:18,839 |        dycov.Create input files |       INFO |         input_template.py:   23 | Creating the input DYD file in ../SM_SA.
Edit the Producer.dyd file is necessary to complete each equipment in the model with a dynamic model. Press Enter when finishing editing.
2025-01-23 15:48:18,403 |        dycov.Create input files |       INFO |         input_template.py:   37 | Creating the input PAR file in ../SM_SA.
Edit the Producer.par file is necessary to complete each parameter with a value. Press Enter when finishing editing.    
```

At this point, the user must manually edit the PAR file to enter the parameters 
for each device on their network. The generated PAR file looks similar to the 
following one. In it you can see that each device declared in the DYD file 
expects a set of parameters that define it. In the file you can see that there 
are parameters with an assigned value, this value is equal to the default value 
defined in the dynamic model, if it is defined. The user must enter the 
parameters without a value, as well as modify the parameters that do not fit 
their network model:
```xml
<?xml version='1.0' encoding='UTF-8'?>
<parametersSet xmlns="http://www.rte-france.com/dynawo">
  <set id="AuxLoad_Xfmr">
    <par type="DOUBLE" name="transformer_BPu" value=""/>
    <par type="DOUBLE" name="transformer_GPu" value=""/>
    <par type="DOUBLE" name="transformer_RPu" value=""/>
    <par type="DOUBLE" name="transformer_XPu" value=""/>
    <par type="DOUBLE" name="transformer_rTfoPu" value=""/>
    <par type="INT" name="transformer_NbSwitchOffSignals" value="2"/>
    <par type="INT" name="transformer_State0" value="2"/>
    <par type="BOOL" name="transformer_SwitchOffSignal10" value="false"/>
    <par type="BOOL" name="transformer_SwitchOffSignal20" value="false"/>
    <par type="BOOL" name="transformer_SwitchOffSignal30" value="false"/>
  </set>
  <set id="Aux_Load">
    <par type="DOUBLE" name="load_P0Pu" value=""/>
    <par type="DOUBLE" name="load_Q0Pu" value=""/>
    <par type="DOUBLE" name="load_U0Pu" value=""/>
    <par type="DOUBLE" name="load_UPhase0" value=""/>
    <par type="INT" name="load_NbSwitchOffSignals" value="2"/>
    <par type="INT" name="load_State0" value="2"/>
    <par type="BOOL" name="load_SwitchOffSignal10" value="false"/>
    <par type="BOOL" name="load_SwitchOffSignal20" value="false"/>
    <par type="BOOL" name="load_SwitchOffSignal30" value="false"/>
  </set>
  <set id="StepUp_Xfmr">
    <par type="DOUBLE" name="transformer_BPu" value=""/>
    <par type="DOUBLE" name="transformer_GPu" value=""/>
    <par type="DOUBLE" name="transformer_RPu" value=""/>
    <par type="DOUBLE" name="transformer_XPu" value=""/>
    <par type="DOUBLE" name="transformer_rTfoPu" value=""/>
    <par type="INT" name="transformer_NbSwitchOffSignals" value="2"/>
    <par type="INT" name="transformer_State0" value="2"/>
    <par type="BOOL" name="transformer_SwitchOffSignal10" value="false"/>
    <par type="BOOL" name="transformer_SwitchOffSignal20" value="false"/>
    <par type="BOOL" name="transformer_SwitchOffSignal30" value="false"/>
  </set>
  <set id="Synch_Gen">
    <par type="DOUBLE" name="generator_DPu" value=""/>
    <par type="INT" name="generator_ExcitationPu" value=""/>
    <par type="DOUBLE" name="generator_H" value=""/>
    <par type="DOUBLE" name="generator_MdPuEfd" value=""/>
    <par type="DOUBLE" name="generator_P0Pu" value=""/>
    <par type="DOUBLE" name="generator_PNomAlt" value=""/>
    <par type="DOUBLE" name="generator_PNomTurb" value=""/>
    <par type="DOUBLE" name="generator_Q0Pu" value=""/>
    <par type="DOUBLE" name="generator_RTfPu" value=""/>
    <par type="DOUBLE" name="generator_RaPu" value=""/>
    <par type="DOUBLE" name="generator_SNom" value=""/>
    <par type="DOUBLE" name="generator_SnTfo" value=""/>
    <par type="DOUBLE" name="generator_Tpd0" value=""/>
    <par type="DOUBLE" name="generator_Tppd0" value=""/>
    <par type="DOUBLE" name="generator_Tppq0" value=""/>
    <par type="DOUBLE" name="generator_Tpq0" value=""/>
    <par type="DOUBLE" name="generator_U0Pu" value=""/>
    <par type="DOUBLE" name="generator_UBaseHV" value=""/>
    <par type="DOUBLE" name="generator_UBaseLV" value=""/>
    <par type="DOUBLE" name="generator_UNom" value=""/>
    <par type="DOUBLE" name="generator_UNomHV" value=""/>
    <par type="DOUBLE" name="generator_UNomLV" value=""/>
    <par type="DOUBLE" name="generator_UPhase0" value=""/>
    <par type="BOOL" name="generator_UseApproximation" value=""/>
    <par type="DOUBLE" name="generator_XTfPu" value=""/>
    <par type="DOUBLE" name="generator_XdPu" value=""/>
    <par type="DOUBLE" name="generator_XlPu" value=""/>
    <par type="DOUBLE" name="generator_XpdPu" value=""/>
    <par type="DOUBLE" name="generator_XppdPu" value=""/>
    <par type="DOUBLE" name="generator_XppqPu" value=""/>
    <par type="DOUBLE" name="generator_XpqPu" value=""/>
    <par type="DOUBLE" name="generator_XqPu" value=""/>
    <par type="DOUBLE" name="generator_md" value=""/>
    <par type="DOUBLE" name="generator_mq" value=""/>
    <par type="DOUBLE" name="generator_nd" value=""/>
    <par type="DOUBLE" name="generator_nq" value=""/>
    <par type="DOUBLE" name="governor_Dt" value=""/>
    <par type="DOUBLE" name="governor_R" value=""/>
    <par type="DOUBLE" name="governor_VMax" value=""/>
    <par type="DOUBLE" name="governor_VMin" value=""/>
    <par type="DOUBLE" name="governor_t1" value=""/>
    <par type="DOUBLE" name="governor_t2" value=""/>
    <par type="DOUBLE" name="governor_t3" value=""/>
    <par type="DOUBLE" name="pss_Ks1" value=""/>
    <par type="DOUBLE" name="pss_Ks2" value=""/>
    <par type="DOUBLE" name="pss_Ks3" value=""/>
    <par type="INT" name="pss_M" value=""/>
    <par type="INT" name="pss_N" value=""/>
    <par type="DOUBLE" name="pss_OmegaMaxPu" value=""/>
    <par type="DOUBLE" name="pss_OmegaMinPu" value=""/>
    <par type="DOUBLE" name="pss_PGenMaxPu" value=""/>
    <par type="DOUBLE" name="pss_PGenMinPu" value=""/>
    <par type="DOUBLE" name="pss_SNom" value=""/>
    <par type="DOUBLE" name="pss_VPssMaxPu" value=""/>
    <par type="DOUBLE" name="pss_VPssMinPu" value=""/>
    <par type="DOUBLE" name="pss_t1" value=""/>
    <par type="DOUBLE" name="pss_t2" value=""/>
    <par type="DOUBLE" name="pss_t3" value=""/>
    <par type="DOUBLE" name="pss_t4" value=""/>
    <par type="DOUBLE" name="pss_t6" value=""/>
    <par type="DOUBLE" name="pss_t7" value=""/>
    <par type="DOUBLE" name="pss_t8" value=""/>
    <par type="DOUBLE" name="pss_t9" value=""/>
    <par type="DOUBLE" name="pss_tW1" value=""/>
    <par type="DOUBLE" name="pss_tW2" value=""/>
    <par type="DOUBLE" name="pss_tW3" value=""/>
    <par type="DOUBLE" name="pss_tW4" value=""/>
    <par type="DOUBLE" name="voltageRegulator_EMax" value=""/>
    <par type="DOUBLE" name="voltageRegulator_EMin" value=""/>
    <par type="DOUBLE" name="voltageRegulator_K" value=""/>
    <par type="DOUBLE" name="voltageRegulator_Ta" value=""/>
    <par type="DOUBLE" name="voltageRegulator_Tb" value=""/>
    <par type="DOUBLE" name="voltageRegulator_Te" value=""/>
    <par type="INT" name="generator_NbSwitchOffSignals" value="3"/>
    <par type="INT" name="generator_State0" value="2"/>
    <par type="BOOL" name="generator_SwitchOffSignal10" value="false"/>
    <par type="BOOL" name="generator_SwitchOffSignal20" value="false"/>
    <par type="BOOL" name="generator_SwitchOffSignal30" value="false"/>
    <par type="DOUBLE" name="generator_iStart0Pu_im" value="0"/>
    <par type="DOUBLE" name="generator_iStart0Pu_re" value="0"/>
    <par type="DOUBLE" name="governor_add_k1" value="1"/>
    <par type="DOUBLE" name="governor_add_k2" value="-1"/>
    <par type="INT" name="governor_limitedFirstOrder_I_initType" value="3"/>
    <par type="DOUBLE" name="governor_limitedFirstOrder_I_k" value="1"/>
    <par type="BOOL" name="governor_limitedFirstOrder_I_use_reset" value="false"/>
    <par type="BOOL" name="governor_limitedFirstOrder_I_use_set" value="false"/>
    <par type="DOUBLE" name="governor_limitedFirstOrder_K" value="1"/>
    <par type="INT" name="governor_limitedFirstOrder_lim_homotopyType" value="1"/>
    <par type="BOOL" name="governor_limitedFirstOrder_lim_limitsAtInit" value="true"/>
    <par type="BOOL" name="governor_limitedFirstOrder_lim_strict" value="false"/>
    <par type="DOUBLE" name="governor_transferFunction_a_1_" value="1"/>
    <par type="DOUBLE" name="governor_transferFunction_b_1_" value="1"/>
    <par type="INT" name="governor_transferFunction_initType" value="1"/>
    <par type="INT" name="governor_transferFunction_na" value="2"/>
    <par type="INT" name="governor_transferFunction_nb" value="2"/>
    <par type="INT" name="governor_transferFunction_nx" value="1"/>
    <par type="DOUBLE" name="governor_transferFunction_y_start" value="0"/>
    <par type="DOUBLE" name="pss_KOmega" value="1"/>
    <par type="DOUBLE" name="pss_KOmegaRef" value="0"/>
    <par type="DOUBLE" name="pss_add_k2" value="1"/>
    <par type="INT" name="pss_firstOrder1_initType" value="1"/>
    <par type="DOUBLE" name="pss_firstOrder1_y_start" value="0"/>
    <par type="INT" name="pss_firstOrder_initType" value="1"/>
    <par type="DOUBLE" name="pss_firstOrder_k" value="1"/>
    <par type="DOUBLE" name="pss_firstOrder_y_start" value="0"/>
    <par type="INT" name="pss_limiter1_homotopyType" value="1"/>
    <par type="BOOL" name="pss_limiter1_limitsAtInit" value="true"/>
    <par type="BOOL" name="pss_limiter1_strict" value="false"/>
    <par type="INT" name="pss_limiter2_homotopyType" value="1"/>
    <par type="BOOL" name="pss_limiter2_limitsAtInit" value="true"/>
    <par type="BOOL" name="pss_limiter2_strict" value="false"/>
    <par type="INT" name="pss_limiter_homotopyType" value="1"/>
    <par type="BOOL" name="pss_limiter_limitsAtInit" value="true"/>
    <par type="BOOL" name="pss_limiter_strict" value="false"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_K" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_NMax" value="4"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_Y0" value="0"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__K" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__MMax" value="6"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__firstOrderCascade_0__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__firstOrderCascade_0__k" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__firstOrderCascade_1__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__firstOrderCascade_1__k" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__firstOrderCascade_2__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__firstOrderCascade_2__k" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__firstOrderCascade_3__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__firstOrderCascade_3__k" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__firstOrderCascade_4__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__firstOrderCascade_4__k" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__leadlag_a_1_" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__leadlag_initType" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__leadlag_na" value="2"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__leadlag_nb" value="2"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__leadlag_nx" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__leadlag_x_start_0_" value="0"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_0__leadlag_y_start" value="0"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__K" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__MMax" value="6"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__firstOrderCascade_0__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__firstOrderCascade_0__k" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__firstOrderCascade_1__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__firstOrderCascade_1__k" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__firstOrderCascade_2__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__firstOrderCascade_2__k" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__firstOrderCascade_3__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__firstOrderCascade_3__k" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__firstOrderCascade_4__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__firstOrderCascade_4__k" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__leadlag_a_1_" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__leadlag_initType" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__leadlag_na" value="2"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__leadlag_nb" value="2"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__leadlag_nx" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__leadlag_x_start_0_" value="0"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_1__leadlag_y_start" value="0"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__K" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__MMax" value="6"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__firstOrderCascade_0__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__firstOrderCascade_0__k" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__firstOrderCascade_1__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__firstOrderCascade_1__k" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__firstOrderCascade_2__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__firstOrderCascade_2__k" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__firstOrderCascade_3__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__firstOrderCascade_3__k" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__firstOrderCascade_4__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__firstOrderCascade_4__k" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__leadlag_a_1_" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__leadlag_initType" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__leadlag_na" value="2"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__leadlag_nb" value="2"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__leadlag_nx" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__leadlag_x_start_0_" value="0"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_2__leadlag_y_start" value="0"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__K" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__MMax" value="6"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__firstOrderCascade_0__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__firstOrderCascade_0__k" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__firstOrderCascade_1__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__firstOrderCascade_1__k" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__firstOrderCascade_2__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__firstOrderCascade_2__k" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__firstOrderCascade_3__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__firstOrderCascade_3__k" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__firstOrderCascade_4__initType" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__firstOrderCascade_4__k" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__leadlag_a_1_" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__leadlag_initType" value="1"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__leadlag_na" value="2"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__leadlag_nb" value="2"/>
    <par type="INT" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__leadlag_nx" value="1"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__leadlag_x_start_0_" value="0"/>
    <par type="DOUBLE" name="pss_rampTrackingFilter_leadMOrderLagCascade_3__leadlag_y_start" value="0"/>
    <par type="DOUBLE" name="pss_transferFunction1_a_1_" value="1"/>
    <par type="DOUBLE" name="pss_transferFunction1_b_1_" value="1"/>
    <par type="INT" name="pss_transferFunction1_initType" value="1"/>
    <par type="INT" name="pss_transferFunction1_na" value="2"/>
    <par type="INT" name="pss_transferFunction1_nb" value="2"/>
    <par type="INT" name="pss_transferFunction1_nx" value="1"/>
    <par type="DOUBLE" name="pss_transferFunction1_x_start_0_" value="0"/>
    <par type="DOUBLE" name="pss_transferFunction1_y_start" value="0"/>
    <par type="DOUBLE" name="pss_transferFunction_a_1_" value="1"/>
    <par type="DOUBLE" name="pss_transferFunction_b_1_" value="1"/>
    <par type="INT" name="pss_transferFunction_initType" value="1"/>
    <par type="INT" name="pss_transferFunction_na" value="2"/>
    <par type="INT" name="pss_transferFunction_nb" value="2"/>
    <par type="INT" name="pss_transferFunction_nx" value="1"/>
    <par type="DOUBLE" name="pss_transferFunction_x_start_0_" value="0"/>
    <par type="DOUBLE" name="pss_transferFunction_y_start" value="0"/>
    <par type="DOUBLE" name="pss_washout1_U0" value="0"/>
    <par type="INT" name="pss_washout1_derivative_initType" value="1"/>
    <par type="DOUBLE" name="pss_washout1_derivative_y_start" value="0"/>
    <par type="INT" name="pss_washout2_derivative_initType" value="1"/>
    <par type="DOUBLE" name="pss_washout2_derivative_y_start" value="0"/>
    <par type="DOUBLE" name="pss_washout3_U0" value="0"/>
    <par type="INT" name="pss_washout3_derivative_initType" value="1"/>
    <par type="DOUBLE" name="pss_washout3_derivative_y_start" value="0"/>
    <par type="INT" name="pss_washout_derivative_initType" value="1"/>
    <par type="DOUBLE" name="pss_washout_derivative_y_start" value="0"/>
    <par type="DOUBLE" name="voltageRegulator_add3_k1" value="1"/>
    <par type="DOUBLE" name="voltageRegulator_add3_k2" value="-1"/>
    <par type="DOUBLE" name="voltageRegulator_add3_k3" value="1"/>
    <par type="DOUBLE" name="voltageRegulator_leadLag_a_1_" value="1"/>
    <par type="DOUBLE" name="voltageRegulator_leadLag_b_1_" value="1"/>
    <par type="INT" name="voltageRegulator_leadLag_initType" value="1"/>
    <par type="INT" name="voltageRegulator_leadLag_na" value="2"/>
    <par type="INT" name="voltageRegulator_leadLag_nb" value="2"/>
    <par type="INT" name="voltageRegulator_leadLag_nx" value="1"/>
    <par type="INT" name="voltageRegulator_limitedFirstOrder_I_initType" value="3"/>
    <par type="DOUBLE" name="voltageRegulator_limitedFirstOrder_I_k" value="1"/>
    <par type="BOOL" name="voltageRegulator_limitedFirstOrder_I_use_reset" value="false"/>
    <par type="BOOL" name="voltageRegulator_limitedFirstOrder_I_use_set" value="false"/>
    <par type="INT" name="voltageRegulator_limitedFirstOrder_lim_homotopyType" value="1"/>
    <par type="BOOL" name="voltageRegulator_limitedFirstOrder_lim_limitsAtInit" value="true"/>
    <par type="BOOL" name="voltageRegulator_limitedFirstOrder_lim_strict" value="false"/>
  </set>
</parametersSet>
```

After saving the edited PAR file, press *Enter* in the terminal where the command was 
executed, the tool will validate the PAR file, and modify the INI file:

```
(dycov_venv) user@dynawo:~$ dycov generate -t S+Aux -v performance_SM -o ../SM_SA
2025-01-23 15:30:18,839 |        dycov.Create input files |       INFO |         input_template.py:   23 | Creating the input DYD file in ../SM_SA.
Edit the Producer.dyd file is necessary to complete each equipment in the model with a dynamic model. Press Enter when finishing editing.
2025-01-23 15:48:18,403 |        dycov.Create input files |       INFO |         input_template.py:   37 | Creating the input PAR file in ../SM_SA.
Edit the Producer.par file is necessary to complete each parameter with a value. Press Enter when finishing editing.    
2025-01-23 15:58:24,777 |        dycov.Create input files |       INFO |         input_template.py:   51 | Creating the input INI file in ../SM_SA.
Edit the Producer.ini file is necessary to complete each parameter with a value. Press Enter when finishing editing.
```

Again the user must complete the generated INI file, giving value to all the 
parameters that the tool needs but cannot infer from the Dynawo model:

```ini
# p_{max_unite} as defined by the DTR in MW
p_max =
# u_nom is the nominal voltage in the PDR Bus (in kV)
# Allowed values: 400, 225, 150, 90, 63 (land) and 132, 66 (offshore)
u_nom =
# s_nom is the nominal apparent power of all generating units (in MVA)
# This is the value that will be used for the base conversion in the PDR bus active/reactive power
s_nom =
# q_max is the maximum reactive power of the generator unit (in MVar)
q_max =
# q_min is the minimum reactive power of the generator unit (in MVar)
q_min =
# topology
topology = S+Aux
```

After saving the edited INI file, press *Enter* in the terminal where the command was 
executed, the tool will validate the INI file, and generate the CurvesFiles.ini file:

```
(dycov_venv) user@dynawo:~$ dycov generate -t S+Aux -v performance_SM -o ../SM_SA
2025-01-23 15:30:18,839 |        dycov.Create input files |       INFO |         input_template.py:   23 | Creating the input DYD file in ../SM_SA.
Edit the Producer.dyd file is necessary to complete each equipment in the model with a dynamic model. Press Enter when finishing editing.
2025-01-23 15:48:18,403 |        dycov.Create input files |       INFO |         input_template.py:   37 | Creating the input PAR file in ../SM_SA.
Edit the Producer.par file is necessary to complete each parameter with a value. Press Enter when finishing editing.    
2025-01-23 15:58:24,777 |        dycov.Create input files |       INFO |         input_template.py:   51 | Creating the input INI file in ../SM_SA.
Edit the Producer.ini file is necessary to complete each parameter with a value. Press Enter when finishing editing.
2025-01-23 16:02:18,040 |        dycov.Create input files |       INFO |         input_template.py:   66 | Creating the reference curves files in ../SM_SA/ReferenceCurves.
Edit the CurvesFiles.ini file is necessary to complete each parameter with a curves file. Press Enter when finishing editing.
```

The generated file is similar to the following example:
```ini
[Curves-Files]
PCS_RTE-I2.USetPointStep.AReactance = 
PCS_RTE-I2.USetPointStep.BReactance = 
PCS_RTE-I3.LineTrip.2BReactance = 
PCS_RTE-I4.ThreePhaseFault.TransientBolted = 
PCS_RTE-I6.GridVoltageDip.Qzero = 
PCS_RTE-I7.GridVoltageSwell.QMax = 
PCS_RTE-I7.GridVoltageSwell.QMin = 
PCS_RTE-I8.LoadShedDisturbance.PmaxQzero = 
PCS_RTE-I10.Islanding.DeltaP10DeltaQ4 = 


[Curves-Dictionary] 
time =  
BusPDR_BUS_Voltage = 
BusPDR_BUS_ActivePower = 
BusPDR_BUS_ReactivePower = 
StepUp_Xfmr_XFMR_Tap = 
Synch_Gen_GEN_RotorSpeedPu = 
Synch_Gen_GEN_InternalAngle = 
Synch_Gen_GEN_AVRSetpointPu = 
Synch_Gen_GEN_MagnitudeControlledByAVRP = 
Synch_Gen_GEN_NetworkFrequencyPu = 
# To represent a signal that is in raw abc three-phase form, the affected signal must be tripled 
# and the suffixes _a, _b and _c must be added as in the following example: 
#    BusPDR_BUS_Voltage_a = 
#    BusPDR_BUS_Voltage_b = 
#    BusPDR_BUS_Voltage_c = 
```

The user must edit this file to indicate the location of the curve files that 
the tool must use for each PCS, as well as to relate the columns contained in 
the curve files with the columns expected by the tool. Additionally, each PCS 
has a DICT file that allows the relationship of columns between the reference 
curve file for each specific PCS to be made. If the names of the columns in 
the curve file do not vary, it is not necessary to modify the DICT file.

Example of an edited CurvesFiles.ini file:
```ini
[Curves-Files]
PCS_RTE-I2.USetPointStep.AReactance = PCS_RTE-I2.USetPointStep.AReactance.csv
PCS_RTE-I2.USetPointStep.BReactance = PCS_RTE-I2.USetPointStep.BReactance.csv
PCS_RTE-I3.LineTrip.2BReactance = PCS_RTE-I3.LineTrip.2BReactance.csv
PCS_RTE-I4.ThreePhaseFault.TransientBolted = PCS_RTE-I4.ThreePhaseFault.TransientBolted.csv
PCS_RTE-I6.GridVoltageDip.Qzero = PCS_RTE-I6.GridVoltageDip.Qzero.csv
PCS_RTE-I7.GridVoltageSwell.QMax = PCS_RTE-I7.GridVoltageSwell.QMax.csv
PCS_RTE-I7.GridVoltageSwell.QMin = PCS_RTE-I7.GridVoltageSwell.QMin.csv
PCS_RTE-I8.LoadShedDisturbance.PmaxQzero = PCS_RTE-I8.LoadShedDisturbance.PmaxQzero.csv
PCS_RTE-I10.Islanding.DeltaP10DeltaQ4 = PCS_RTE-I10.Islanding.DeltaP10DeltaQ4.csv


[Curves-Dictionary]
time = time
BusPDR_BUS_Voltage = BusPDR_BUS_Voltage
BusPDR_BUS_ActivePower = BusPDR_BUS_ActivePower
BusPDR_BUS_ReactivePower = BusPDR_BUS_ReactivePower
BusPDR_BUS_ActiveCurrent = BusPDR_BUS_ActiveCurrent
BusPDR_BUS_ReactiveCurrent = BusPDR_BUS_ReactiveCurrent
StepUp_Xfmr_XFMR_Tap = StepUp_Xfmr_XFMR_Tap
NetworkFrequencyPu = NetworkFrequencyPu
# To represent a signal that is in raw abc three-phase form, the affected signal must be tripled
# and the suffixes _a, _b and _c must be added as in the following example:
#    BusPDR_BUS_Voltage_a =
#    BusPDR_BUS_Voltage_b =
#    BusPDR_BUS_Voltage_c =
```

After saving the edited CurvesFiles.ini file, press *Enter* in the terminal where the command was 
executed, the tool will validate the CurvesFiles.ini file, and ends the execution of the command.
