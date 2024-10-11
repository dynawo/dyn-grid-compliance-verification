==================
Adding a new PCS
==================

.. _option1:

Option 1
^^^^^^^^

All the tests that you want to carry out are already created and you simply have to check a new
pcs

#. Create a new directory in src/dgcv/templates/PCS/ called with the name of the pcs. It must contain the necessary files to simulate the part of the external network (not the producer's part). At a minimum, it should contain .dyd, .par, .jobs and .crv with the corresponding curves to perform the tests.
#. Create a directory with a Latex template in src/dgcv/templates/reports/ to fill in the report of the different tests (observe how it is created in the other pcs to replicate the name of the variables to replace and their format). It must have its corresponding makefile.
#. Add to the list of executions and to the list of tests to be executed in the file src/dgcv/config/defaultConfig.ini the new case with the name of the folders created in the previous steps. A new section must also be added in this same file with the name of the pcs and its initialization values. Finally, the new pcs name should also be added to the lists of graphs of curves that you want to show in the report.

Option 2
^^^^^^^^

The new pcs has to perform a new test that is not implemented yet

#. Follow :ref:`Option 1 steps <option1>`.
#. Next, in src/dgcv/config/defaultConfig.ini, add the new test with its corresponding name and the pcs that will execute it in the [PCS-Validations] section.
#. In the model_validation.py file, the new test must be inserted in the initialize_validation function, reading the list of pcs that are going to execute it and adding it to validation_lists (look at some example of the same function).
#. In the src/dgcv/validation/validations.py script a new condition must be added to execute the test, as it is done in the other tests that are already defined, and in the same script a new function must be defined to execute the python test. Once this is done, the result should be added to the results dictionary as desired.
#. Finally, in the pcs_replace function of the src/dgcv/report/create_report.py file, a new line must be added with the name of the placeholder that you have chosen to show in the final report.

Software explanation
--------------------

When a new pcs is added, first of all the template and the report must be created, since they
will be used throughout the execution pipeline. In addition, in the default configuration file
there is a section where the possible tests to be executed and which pcs use them are defined.
In addition, for the pcs to be executed correctly, a section must be added to give the
initialization values. Also, depending on what has been defined in the report template, the curves
that you want to show must be added in the corresponding section.

If we look at the execution pipeline, the first thing that is done is parse the defaultConfig.ini
and, as a result, we obtain the initialization values, the tests that are going to be executed in
each pcs and the curves that their reports require, among others. To do this, we must define the
action we perform in 2.3 in order to detect the new test.

This information is transferred to validations.py, and there, we must define a condition to check
if the test we want to execute is within the tests of the pcs, and make the call to the function
that executes it if it is inside. The result is saved in a dictionary called results that will be
used when creating the report to replace the placeholder that we have defined in the latex template
of the pcs and put the desired result.
