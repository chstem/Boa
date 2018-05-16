#!/bin/bash
# exports everything from the database and creates the complete Book of Abstracts

BoAdir=`pwd`
# go one directory up and export everything
cd ..
Boa.py export abstracts --mask_email
Boa.py export talks
Boa.py export posters
Boa.py export timetable
Boa.py export index

# go back and create BoA
cd $BoAdir
bash make_BoA.sh
