
# Outline for a hands-on workshop introducing the DGCG workshop


## Proposed agenda:
- [15 min, RTE] General presentation: Background and motivation for creating RMS model validation requirements
- [10 min, AIA] Tool presentation
- [45 min, AIA] Tutorial: Getting to grips with the tool on a live example
- [20 min, AIA] Questions & Answers


## General presentation (RTE, ~15 min)
- Context: new requirements in the DTR.
- Motivation (open models, transparency, automation). Target users & use cases.
- Brief roadmap.


## Tool presentation (AIA, ~10 min)
- Requirements (OS, Dynawo, Python, LaTeX).
- Overall workflow for general usage
- Explain the hierarchy for tests: PCS --> Benchmarks --> Operating Conditions (use CIGRE paper)


## Tutorial: Getting to grips with the tool on a live example (AIA, ~45 min)

- [5 min] Installation:
    * Demystify and show how easy it is (i.e., download a file and execute)
    * Windows install is even easier (installs the VS compilers, LaTeX, and Python)

- [10 min] Launch an example and inspect the report (PDF+HTML)
    * Show quickly where the examples are
	* Show the command-line help and launch the example
	* Show the PDF report and the corresponding HTML graphs 

- [5 min] Q&A

- [10 min] Usage in more detail (RMS MODEL VALIDATION):
    * Show the command-line
    * Brief explanation of the available examples
    * Copy an example into a chosen working directory
    * User inputs: explain what the DYD/PAR/INI files are and show a brief inspection of their content
    * Run the tool, explain briefly what the console output means
    * Results: inspect the results directory (tree structure and its contents)

- [10 min] Preparing the inputs
    * Emphasize working from the provided examples, but also briefly mention "dycov generate"
	* Re-emphasize that initialization parameters are not needed, the tool calculates them
    * Emphasize the DICT files necessary for the reference curves
    * Jump into an already-prepared example to finish the example (no time for a live demo)

- [5 min] Configuration:
    * Explain briefly the structure and sections of config.ini  (only the BASIC config options)
    * Show an example: change something in the ini and show what happens
        1. Enabling/disabling certain tests and re-run
        2. Changing the value of a certain KPI threshold and see the different results

## Q & A (~20 min)

