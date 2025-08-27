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
########################################################################

# --- Logging Setup ---
LOG_DIR="logs"
LOG_FILE="${LOG_DIR}/Bulletin18.log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log messages with a timestamp, printing to console and appending to log file
log_message() {
   local message="$1"
   echo "$(date '+%Y-%m-%d %H:%M:%S') - $message" | tee -a "$LOG_FILE"
}

# Start logging
log_message "Script started."
log_message "Log file: $LOG_FILE"

# --- Exporting Environment Variables ---
export AA=$(date +%Y)
export MM=$(date +%m)
export DD=$(date +%d)

#export AA=2025
#export MM=07
#export DD=16
#export PWD=$(pwd) # Current working directory of the script

log_message "Date variables set: AA=$AA, MM=$MM, DD=$DD"
log_message "Script's current working directory: PWD=$PWD"

# --- Define Directories and Paths ---
LOCAL_DIRECTORY=${PWD}
BUFR_INPUT_ROOT="bufr_data/observations" # Relative path to BUFR source
TAC_INPUT="bqrm_data/observations"

log_message "LOCAL_DIRECTORY set to: $LOCAL_DIRECTORY"
log_message "BUFR_INPUT_ROOT set to: $BUFR_INPUT_ROOT"
log_message "TAC_INPUT set to: $TAC_INPUT"

# Original commented-out FTP/SFTP blocks are left as is, but their logic is not active.
# The script's current logic relies on local file paths.

# --- Copy BUFR File ---
# This acts as the "download" step in the current active script logic.
log_message "Attempting to copy BUFR file from ${LOCAL_DIRECTORY}/../${BUFR_INPUT_ROOT}/${AA}/${MM}/${DD}/Synop_${AA}${MM}${DD}0600.bufr to ${LOCAL_DIRECTORY}/Synop/"
# Ensure the target directory exists before copying
mkdir -p "${LOCAL_DIRECTORY}/Synop/" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
   log_message "ERROR: Failed to create directory ${LOCAL_DIRECTORY}/Synop/. Exiting."
   exit 1
fi

BUFR_COPY_SUCCESS=0
cp "${LOCAL_DIRECTORY}/../${BUFR_INPUT_ROOT}/${AA}/${MM}/${DD}/Synop_${AA}${MM}${DD}0600.bufr" "${LOCAL_DIRECTORY}/Synop/" 2>&1 | tee -a "$LOG_FILE"
if [ $? -eq 0 ]; then
   log_message "BUFR file Synop_${AA}${MM}${DD}0600.bufr copied successfully to ${LOCAL_DIRECTORY}/Synop/."
else
   log_message "ERROR: Failed to copy BUFR file Synop_${AA}${MM}${DD}0600.bufr. Exit code: $?"
   BUFR_COPY_SUCCESS=1 # Set flag for failure
fi

# --- Change to LOCAL_DIRECTORY and Execute Python Script ---
log_message "Changing current directory to $LOCAL_DIRECTORY."
cd "$LOCAL_DIRECTORY" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
   log_message "ERROR: Failed to change directory to $LOCAL_DIRECTORY. Exiting script."
   exit 1
fi
log_message "Current directory changed to $LOCAL_DIRECTORY."

# The original script's conditional logic was flawed here.
# This block now correctly checks the success of the BUFR file copy before proceeding.
if [ $BUFR_COPY_SUCCESS -eq 0 ]; then
   log_message "Proceeding with Python script execution as BUFR file copy was successful."
   log_message "Executing python3 Synop24h18.py..."
   python3 Synop24h18.py 2>&1 | tee -a "$LOG_FILE"
   if [ $? -eq 0 ]; then
       log_message "Python script Synop24h18.py executed successfully."
   else
       log_message "ERROR: Python script Synop24h18.py failed. Exit code: $?"
   fi
else
   log_message "Skipping Python script execution due to previous BUFR file copy failure."
fi

# --- File Operations: Cleanup and Moving ---

# Remove old agricole.xlsx
log_message "Navigating to $LOCAL_DIRECTORY/templates/ to remove agricole.xlsx."
cd "$LOCAL_DIRECTORY/templates/" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
   log_message "ERROR: Failed to change directory to $LOCAL_DIRECTORY/templates/. Skipping old agricole.xlsx removal."
else
   if [ -f "agricole.xlsx" ]; then
       rm agricole.xlsx 2>&1 | tee -a "$LOG_FILE"
       if [ $? -eq 0 ]; then
           log_message "Removed $LOCAL_DIRECTORY/templates/agricole.xlsx."
       else
           log_message "ERROR: Failed to remove $LOCAL_DIRECTORY/templates/agricole.xlsx. Exit code: $?"
       fi
   else
       log_message "agricole.xlsx not found in $LOCAL_DIRECTORY/templates/. Skipping removal."
   fi
fi

# Return to LOCAL_DIRECTORY
log_message "Returning to $LOCAL_DIRECTORY."
cd "$LOCAL_DIRECTORY" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
   log_message "ERROR: Failed to change directory back to $LOCAL_DIRECTORY. Subsequent operations might be affected."
   # Decide if to exit or continue. For now, continue.
fi

# Move newly generated agricole.xlsx
log_message "Moving agricole_${MM}${DD}0600.xlsx to $LOCAL_DIRECTORY/templates/agricole.xlsx."
mv "agricole_${MM}${DD}0600.xlsx" "$LOCAL_DIRECTORY/templates/agricole.xlsx" 2>&1 | tee -a "$LOG_FILE"
if [ $? -eq 0 ]; then
   log_message "Moved agricole_${MM}${DD}0600.xlsx successfully."
else
   log_message "ERROR: Failed to move agricole_${MM}${DD}0600.xlsx. Exit code: $?"
fi

# Create directory for text files and move them
log_message "Creating directory $LOCAL_DIRECTORY/txt/${AA}/${MM} if it doesn't exist."
mkdir -p "$LOCAL_DIRECTORY/txt/${AA}/${MM}" 2>&1 | tee -a "$LOG_FILE"
if [ $? -eq 0 ]; then
   log_message "Directory $LOCAL_DIRECTORY/txt/${AA}/${MM} created/exists."
else
   log_message "ERROR: Failed to create directory $LOCAL_DIRECTORY/txt/${AA}/${MM}. Exit code: $?"
fi

log_message "Moving all *.txt files to $LOCAL_DIRECTORY/txt/${AA}/${MM}."
mv *.txt "$LOCAL_DIRECTORY/txt/${AA}/${MM}" 2>&1 | tee -a "$LOG_FILE"
if [ $? -eq 0 ]; then
   log_message "Moved *.txt files successfully."
else
   log_message "WARNING: No *.txt files found or failed to move *.txt files. Exit code: $?"
fi

# Remove remaining .xlsx and .docx files in LOCAL_DIRECTORY
log_message "Removing all *.xlsx files in $LOCAL_DIRECTORY."
rm -f *.xlsx 2>&1 | tee -a "$LOG_FILE" # Use -f to suppress error if no files match
if [ $? -eq 0 ]; then
   log_message "Removed *.xlsx files successfully from $LOCAL_DIRECTORY."
else
   log_message "WARNING: Failed to remove some *.xlsx files from $LOCAL_DIRECTORY. Exit code: $?"
fi

log_message "Removing all *.docx files in $LOCAL_DIRECTORY."
rm -f *.docx 2>&1 | tee -a "$LOG_FILE" # Use -f to suppress error if no files match
if [ $? -eq 0 ]; then
   log_message "Removed *.docx files successfully from $LOCAL_DIRECTORY."
else
   log_message "WARNING: Failed to remove some *.docx files from $LOCAL_DIRECTORY. Exit code: $?"
fi

# Remove .xlsx files from Climxlsx directory
log_message "Removing all *.xlsx files in $LOCAL_DIRECTORY/Climxlsx/."
rm -f "$LOCAL_DIRECTORY/Climxlsx/"*.xlsx 2>&1 | tee -a "$LOG_FILE" # Use -f for robustness
if [ $? -eq 0 ]; then
   log_message "Removed *.xlsx files from $LOCAL_DIRECTORY/Climxlsx/ successfully."
else
   log_message "WARNING: Failed to remove some *.xlsx files from $LOCAL_DIRECTORY/Climxlsx/. Exit code: $?"
fi

# Create backup directories
# Change log_info to log_message
log_message "Creating backup directories: ${LOCAL_DIRECTORY}/Backup/${AA}/${MM} and ${LOCAL_DIRECTORY}/Backup/${AA}/${MM}/${DD}."
mkdir -p "${LOCAL_DIRECTORY}/Backup/${AA}/${MM}" || { log_message "ERROR: Failed to create backup/${AA}/${MM} directory."; } # Change log_error to log_message
mkdir -p "${LOCAL_DIRECTORY}/Backup/${AA}/${MM}/${DD}" || { log_message "ERROR: Failed to create backup/${AA}/${MM}/${DD} directory."; } # Change log_error to log_message
if [ $? -ne 0 ]; then log_message "ERROR: Failed to create one or more backup directories."; fi # Change log_error to log_message

# Change log_info to log_message
log_message "Copying SMAL*${DD}0600* from ${LOCAL_DIRECTORY}/../../../../${TAC_INPUT}/${AA}/${MM}/${DD}/ to ${LOCAL_DIRECTORY}/Backup/${AA}/${MM}/${DD}."
cp -r "${LOCAL_DIRECTORY}/../../../../${TAC_INPUT}/${AA}/${MM}/${DD}" "${LOCAL_DIRECTORY}/Backup/${AA}/${MM}"
if [ $? -ne 0 ]; then log_message "ERROR: Failed to copy SMAL* files to backup. Check source path or permissions."; fi # Change log_error to log_message
# Change log_info to log_message
log_message "Script finished."