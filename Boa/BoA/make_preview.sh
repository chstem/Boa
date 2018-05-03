#!/bin/bash
#
# creates a preview pdf for the selected abstract-ID
# the pdf will be moved to the respective folder of the abstract
# call with './make_preview.sh -d <ID> [-h]'

# make sure to be in correct working directory
cd `dirname $0`

# set variables
if [[ -f texlivedir.txt ]]; then
    pdflatex=`cat texlivedir.txt`/pdflatex
else
    pdflatex=`which pdflatex`
fi

halt_on_error=false

# get command line options
ID=$1
while getopts hd: opt; do
    case $opt in
        h) halt_on_error=true;;
        d) ID=$OPTARG;;
    esac
done

# make log entry
# echo `date` $1 >> history.log
logfile=tex.stdout

# create tex file
sed s/_ID_/$ID/g preview_template.tex > $ID.tex

# run pdflatex
if [ "$halt_on_error" = true ]; then
    $pdflatex -no-shell-escape -halt-on-error -interaction=batchmode $ID.tex >> $logfile
else
    $pdflatex -no-shell-escape -interaction=batchmode $ID.tex >> $logfile
fi

# move output and clean up
mv $ID.log $logfile abstracts/$ID/
if [ -f $ID.pdf ]; then
	mv $ID.pdf abstracts/$ID/
fi
rm $ID.*

exit 0
