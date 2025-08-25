#!/bin/bash
export AA=$(date +%Y)
export MM=$(date +%m)
export DD=$(date +%d)
export AAprec=$(date -d "yesterday" +%Y)
export MMprec=$(date -d "yesterday" +%m)
export DDprec=$(date -d "yesterday" +%d)
export PWD=$(pwd)

cd
cat SMAL*${DDprec}1800 | sed '/^60.*NIL=/d' > Synop_${AAprec}${MMprec}${DDprec}1800
#cat SMAL*${DDprec}1800  > Synop_${AA}${MM}${DDprec}1800
./synop2bufr.exe -i Synop_${AAprec}${MMprec}${DDprec}1800 -o Synop_${AAprec}${MMprec}${DDprec}1800.bufr -c 96
#cat SMAL*${DD}0600  > Synop_${AA}${MM}${DD}0600
cat SMAL*${DD}0600 | sed '/^60.*NIL=/d' > Synop_${AA}${MM}${DD}0600
./synop2bufr.exe -i Synop_${AA}${MM}${DD}0600 -o Synop_${AA}${MM}${DD}0600.bufr -c 96



