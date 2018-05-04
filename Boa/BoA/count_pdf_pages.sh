#!/bin/bash
if [ -f $1 ]; then
	pdfinfo $1 | grep 'Pages' | awk '{print $2}'
else
	echo 0
fi


