#!/bin/bash
cd abstracts
# get page number and save in file 'pages'
find -type f -name *.pdf -print -exec sh ../count_pdf_pages.sh {} \; > pages

# search for pdfs with more than 1 page
grep -w -B 1 '[0|2-9]' pages            # search for page numbers 2-9 and 0
grep -w -B 1 '[1-9][0-9][0-9]*' pages   # search for page number > 9
