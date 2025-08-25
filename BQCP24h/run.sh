#!/bin/bash

########################################################################
#                                                                      #
#   Bufr and Arpege Data Retrieval and Processing Script               #
#                                                                      #
#   This script connects to FTP and SFTP servers to retrieve BUFR      #
#   and Arpege data files. It then downloads these files, processes    #
#   them using Python scripts, and performs necessary operations       #
#   such as plotting geopotential height and mean sea level pressure,  #
#   and converting BUFR data to Excel format.                          #
#                                                                      #
#                                                                      #
########################################################################
export AA=$(date +%Y)
export MM=$(date +%m)
export DD=$(date +%d)
export PWD=$(pwd)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_DIRECTORY="${SCRIPT_DIR}"

python3 "${LOCAL_DIRECTORY}/Bulletin.py"