#!/bin/bash

########################################################################
#                                                                      #
#   Automated Data Processing Script                                   #
#                                                                      #
#   This script sets environment variables for the current and         #
#   previous day's date (in year, month, and day formats). It then     #
#   executes another bash script named BQRM_ref.sh, which is expected  #
#   to handle automated data processing tasks.                         #
#                                                                      #
#   AUTHOR:                                                            #
#   - Nour El Isslam KERROUMI                                          #
#                                                                      #
#   LAST MODIFICATION:                                                 #
#   - Date: 24-03-2024                                                 #
#                                                                      #
########################################################################

export AA=$(date +%Y)
export MM=$(date +%m)
export DD=$(date +%d)
export AAprec=$(date -d "yesterday" +%Y)
export MMprec=$(date -d "yesterday" +%m)
export DDprec=$(date -d "yesterday" +%d)
export PWD=$(pwd) 
cd /home/bqrm/BQRM-main/scr
./BQRM_ref.sh
