#!/bin/bash
#
# Run this script to convert all tutorials from Markdown format to PDF.
# You will need pandoc and LaTeX (including the deb package "texlive-latex-recommended" under Debian/Ubuntu).

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail

for INPUT_FILE in ./*.md; do
   OUTPUT_FILE=${INPUT_FILE%.md}.pdf
   echo pandoc -f markdown --pdf-engine=pdflatex --listings -H listings-setup.tex -o "$OUTPUT_FILE" "$INPUT_FILE"
   pandoc -f markdown --pdf-engine=pdflatex --listings -H listings-setup.tex -o "$OUTPUT_FILE" "$INPUT_FILE"
done

