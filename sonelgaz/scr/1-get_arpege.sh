#!/bin/bash 

REMOTE_DIRECTORY="/share/meteofrance/Arpege_Orig"
LOCAL_DIRECTORY=${PWD}
FTP_SERVER="ftp1.meteo.dz"
FTP_USERNAME="messir"
FTP_PASSWORD="123Messir123"
PARENT_DIR="/home/aoumeur/bqrm/sonelgaz/"
echo $PARENT_DIR 

# Get yesterday's date in YYYYMMDD format
date=$(date +"%Y%m%d")
echo "Fetching files for date: $date"

# First, check if files exist on the FTP server
echo "Checking if files exist on FTP server..."
file_list=$(ftp -n "$FTP_SERVER" <<END_SCRIPT
quote USER $FTP_USERNAME
quote PASS $FTP_PASSWORD
cd $REMOTE_DIRECTORY
ls
quit
END_SCRIPT
)

# Filter for the files we want
matching_files=$(echo "$file_list" | grep "SP1.*${date}000")

if [ -z "$matching_files" ]; then
    echo "No matching files found on FTP server for date $date"
    echo "Launching 1-get-aladin.py instead..."
    cd $PARENT_DIR/scr
    python3 1-get-aladin.py
    exit $?
else
    echo "Found matching files:"
    echo "$matching_files"
    
    # FTP Connection and File Transfer
    echo "Downloading files..."
    ftp -n "$FTP_SERVER" <<END_SCRIPT
quote USER $FTP_USERNAME
quote PASS $FTP_PASSWORD
lcd $LOCAL_DIRECTORY
cd $REMOTE_DIRECTORY
binary
prompt off
mget *SP1*${date}000*
quit
END_SCRIPT

    # Check if files were downloaded
    downloaded_files=$(ls *SP1*${date}000* 2>/dev/null)
    if [ -z "$downloaded_files" ]; then
        echo "ERROR: No files were downloaded despite being listed"
        exit 1
    fi

    mv *SP1*${date}000* $PARENT_DIR/tmp/
    cd $PARENT_DIR/scr
    echo "Launching 2-conv.py"
    python3 2-conv.py
    exit $?
fi