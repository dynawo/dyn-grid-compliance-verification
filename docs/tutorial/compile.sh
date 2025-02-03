#!/bin/sh

find . -type f -name '*.md' -print0 | xargs -0 -P2 -I{} pandoc --listings -H listings-setup.tex --pdf-engine=xelatex -f markdown {} -o {}.pdf
for f in ./*.md.pdf; do mv -- "${f}" "${f%.md.pdf}.pdf"; done
