# reports

Contains the LaTex report files of the PCS. And it is made up of 3 directories:
* **model/PPM**: DGCV Model Validation tests (Power Parks)
* **performance/PPM**: Electric Performance tests (Power Parks)
* **performance/SM**: Electric Performance tests (Synchronous Machines)

# Modify an existing PCS

1. Create the PCS directory, if it does not exist, of the desired verification mode.
2. Enter to the PCS directory of the desired verification mode.
3. Create the LaTex report file for new Operating Conditions.
   
# Add a new PCS

1. Create the PCS directory of the desired verification mode.
2. Enter to the PCS directory of the desired verification mode.
3. Create the LaTex report file for new PCS.

Note: It is recommended to split the LaTex report as follows:
* the main report with:
  * title.
  * table if contents.
  * a block to include the Operating Condition reports.
  * bibliography.
* a report by Operating Condition with:
  * Simulation description.
  * Simulation results.
  * Analysis of results.
  * Compliance checks.