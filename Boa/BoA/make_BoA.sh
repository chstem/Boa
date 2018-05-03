#!/bin/bash
# run pdflatex to create the complete Book of Abstracts

# set variables
if [[ -f texlivedir.txt ]]; then
    pdflatex=`cat texlivedir.txt`/pdflatex
else
    pdflatex=`which pdflatex`
fi

# make log entry
# echo `date` BOA >> history.log
logfile=BOA.stdout
rm -f $logfile

# run pdflatex
$pdflatex -no-shell-escape -interaction=batchmode  BOA.tex >> $logfile
$pdflatex -no-shell-escape -interaction=batchmode  BOA.tex >> $logfile

# clean up
# rm BOA.aux BOA.idx BOA.out BOA.toc BOA.ind

exit 0
