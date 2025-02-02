
# Outline for a hands-on workshop introducing the DGCG workshop


## Proposed agenda:
- General presentation: Background and motivation for creating RMS model validation requirements (~15 minutes) RTE
- Tool presentation (~10 minutes) AIA
- Tutorial: Getting to grips with the tool on a live example (40min-1h) AIA
- Questions/Answers (~20 minutes)


## General presentation (RTE, ~15 min)
- Context: new requirements in the DTR.
- Motivation (open models, transparency, automation). Target users & use cases.
- Brief roadmap.


## Tool presentation (AIA, ~10 min)
- Requirements (OS, Dynawo, Python, LaTeX).
- Overall workflow for general usage
- Explain the hierarchy for tests: PCS --> Benchmarks --> Operating Conditions (use CIGRE paper)


## Tutorial: Getting to grips with the tool on a live example (AIA, ~40min--1h)

- [5 min] Installation:
    * Demystify and show how easy it is (i.e., download a file and execute)
    * Windows install is even easier (installs the VS compilers, LaTeX, and Python)

- [20 min] CLI usage (RMS MODEL VALIDATION):
    * Show the command-line
    * Brief explanation of the available full examples
    * Copy an example into a chosen working directory
    * User inputs: explain what the DYD/PAR/INI files are and show a brief inspection of their content
    * Run the tool, explain briefly what the console output means
    * Results: inspect the results directory (tree structure and its contents), show the PDF Reports & HTML curves.

- [10 min] Preparing the inputs:
    * Explain how "dgcv generate" works
    * Emphasize the DICT files necessary for the reference curves
    * But jump into an already-prepared example to finish the example (no time for a live demo)

- [10 min] Configuration:
    * Explain briefly the structure and sections of config.ini  (only the BASIC config options)
    * Show an example: change something in the ini and show what happens
        1. Enabling/disabling certain tests and re-run
        2. Changing the value of a certain KPI threshold and see the different results


## Q & A (~20 min)



