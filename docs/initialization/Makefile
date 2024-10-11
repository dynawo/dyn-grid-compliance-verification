
DOC=initialization
TIKZFIG=pi_model
LATEX_OPTS=-shell-escape -halt-on-error

default:
	pdflatex $(LATEX_OPTS) $(DOC)

doc: default
	biber $(DOC)
	pdflatex $(LATEX_OPTS) $(DOC)
	pdflatex $(LATEX_OPTS) $(DOC)

tikzfig:
	pdflatex $(TIKZFIG).tikz

pretty:
	latexindent -s -y="defaultIndent:'  '" -w $(DOC).tex

clean:
	rm -f *.toc *.aux *.log *.out *.bbl *.blg *.run.xml *.bcf

mrproper: clean
	rm -f *~ $(DOC).pdf $(TIKZFIG).tikz.pdf

