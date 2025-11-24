
# How to add a new PCS to the execution pipeline:

## Option 1 - All the tests that you want to carry out are already created 
and you simply have to check a new PCS.

    1. Create a new directory in the user config directory (see Note1) called with the name of the 
        PCS. At a minimum, it should contain the .ini file with the external model required and 
        its configuration, and if necessary, the TableInfiniteBus.txt file.

    2. Create a directory with a Latex template in the user config directory (see Note2) to fill in 
        the report of the different tests (observe how it is created in the other PCSs to replicate 
        the name of the variables to replace and their format). It must have its corresponding makefile.

---
**Note1:** 
  * ~/.config/dycov/templates/PCS/model for Model Validation PCS 
  * ~/.config/dycov/templates/PCS/performance_PPM for Electric performance 
    verification (for Power Park Modules) 
  * ~/.config/dycov/templates/PCS/performance_SM for Electric performance 
    verification (for Synchronous Machines) 

**Note2:** 
  * ~/.config/dycov/templates/reports/model for Model Validation PCS 
  * ~/.config/dycov/templates/reports/performance_PPM for Electric performance 
    verification (for Power Park Modules) 
  * ~/.config/dycov/templates/reports/performance_SM for Electric performance 
    verification (for Synchronous Machines) 
---

## Option 2 - The new PCS has to perform a new test that is not implemented yet.

    1. Follow the steps in Option 1 to add the new PCS.
    
    2. Next, in every .ini file in the PCS templates directory (see Note3), add the new test 
        with its corresponding name and the PCSs that will execute it in the 
        [Performance-Validations] section if it is a performance test, or in the 
        [Model-Validations] section if it is a model test.
    
    3. In the src/dycov/model/benchmark.py file, the new test must be inserted in the 
        __initialize_validation_by_benchmark function, reading the list of PCSs that are going to 
        execute it and adding it to validation_lists (look at some example of the same function).
    
    4. In the appropriate script for the type of test (performance.py, model.py or common.py), in 
        the directory src/dycov/validation/, a new condition must be added to execute the test, as 
        it is done in the other tests that are already defined, and in the same script a new 
        function must be defined to execute the python test. Once this is done, the result should 
        be added to the results dictionary as desired.
    
    5. Finally, in the _pcs_replace function of the src/dycov/report/report.py file, a new 
        line must be added with the name of the placeholder that you have chosen to show in the 
        final report.
    
---
**Note3:** 
  * ~/src/dycov/templates/PCS/model for Model Validation PCS 
  * ~/src/dycov/templates/PCS/performance_PPM for Electric performance 
    verification (for Power Park Modules) 
  * ~/src/dycov/templates/PCS/performance_SM for Electric performance 
    verification (for Synchronous Machines) 
---

# Software explanation

When a new PCS is added, first of all the template and the report 
must be created, since they will be used throughout the execution 
pipeline. In addition, in the default configuration file there is a 
section where the possible tests to be executed and which PCSs use 
them are defined. In addition, for the PCS to be executed correctly, 
a section must be added to give the initialization values. Also, 
depending on what has been defined in the report template, the curves 
that you want to show must be added in the corresponding section.

If we look at the execution pipeline, the first thing that is done is 
parse the defaultConfig.ini and, as a result, we obtain the 
initialization values, the tests that are going to be executed in each 
PCS and the curves that their reports require, among others. To do 
this, we must define the action we perform in 2.3 in order to detect the 
new test.

This information is transferred to validations.py, and there, we must 
define a condition to check if the test we want to execute is within the 
tests of the PCS, and make the call to the function that executes it 
if it is inside. The result is saved in a dictionary called results that 
will be used when creating the report to replace the placeholder that we 
have defined in the latex template of the PCS and put the desired result.
