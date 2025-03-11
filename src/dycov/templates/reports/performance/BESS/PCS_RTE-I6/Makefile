# This makefile is for compiling the report template and the TikZ figure, but
# the code does not use it. It's useful for editing purposes.

PCS=I6
PCS_NAME=RTE-I6
DOC=report_$(PCS)
TIKZFIG=circuit_$(PCS)
LATEX_OPTS=-shell-escape -halt-on-error

default:
	cp ../../TSO_logo.pdf .
	python3 ../../create_figures.py ../.. . $(PCS_NAME)
	pdflatex $(LATEX_OPTS) $(DOC)

report: default
	pdflatex $(LATEX_OPTS) $(DOC)

tikzfig:
	pdflatex $(TIKZFIG).tikz
	pdftoppm $(TIKZFIG).pdf $(TIKZFIG) -png -rx 300 -ry 300

pretty:
	latexindent -s -y="defaultIndent:'  '" -w $(DOC).tex

clean:
	rm -f *.toc *.aux *.log *.out *.bbl *.blg *.run.xml *.bcf TSO_logo.pdf fig_*PCS_RTE-I*.pdf

mrproper: clean
	rm -f *~ $(DOC).pdf $(TIKZFIG).tikz.pdf $(TIKZFIG).pdf $(TIKZFIG)-1.png

