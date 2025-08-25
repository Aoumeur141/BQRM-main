#!/bin/bash

# Enable strict mode for better error handling:
# -e: Exit immediately if a command exits with a non-zero status.
# -u: Treat unset variables as an error and exit.
# -o pipefail: The return value of a pipeline is the status of the last command to exit with a non-zero status,
#              or zero if all commands in the pipeline exit successfully.
set -euo pipefail

# --- Logging Configuration ---
# Define the directory for logs relative to the script's current working directory
export LOG_DIR="${PWD}/logs"
export LOG_FILE="${LOG_DIR}/BQRM_ref.log"

# Create the log directory if it doesn't exist
mkdir -p "${LOG_DIR}" || { echo "ERROR: $(date '+%Y-%m-%d %H:%M:%S') - Failed to create log directory ${LOG_DIR}. Exiting."; exit 1; }

# Function to log messages to console (stdout/stderr) and append to the log file
log_message() {
   local level="$1"
   local message="$2"
   # Use tee -a to output to console and append to the log file
   echo "$(date '+%Y-%m-%d %H:%M:%S') - ${level}: ${message}" | tee -a "${LOG_FILE}"
}

# Helper function for INFO level logs
log_info() {
   log_message "INFO" "$1"
}

# Helper function for ERROR level logs
log_error() {
   # Send error messages to stderr as well as stdout (for tee)
   log_message "ERROR" "$1" >&2
}

# --- Script Start Log ---
log_info "-------------------------------------------------------------------"
log_info "Script BQRM_ref.sh started."
log_info "Log file for this run: ${LOG_FILE}"
log_info "-------------------------------------------------------------------"

# --- Environment Variables ---
# Date variables for current and previous day
export AA=$(date +%Y)
export MM=$(date +%m)
export DD=$(date +%d)
export AAprec=$(date -d "yesterday" +%Y)
export MMprec=$(date -d "yesterday" +%m)
export DDprec=$(date -d "yesterday" +%d)
export PWD=$(pwd) # Explicitly setting PWD, though usually set by shell

log_info "Environment variables set:"
log_info "  Current Date: ${AA}-${MM}-${DD}"
log_info "  Previous Date: ${AAprec}-${MMprec}-${DDprec}"
log_info "  Current Working Directory (PWD): ${PWD}"

# --- Configuration Variables ---

# Define the root directory where BUFR input files (Synop_*.bufr) and SMAL files are located.
# This path is specifically requested to be bufr_data/observations
BUFR_INPUT_ROOT="bufr_data/observations"

# Local directory where the script is executed and temporary files are stored.
# This is set to the current working directory where the script is run.
LOCAL_DIRECTORY="${PWD}"

# Define the root directory for BQRM output data and bulletins.
# This path is relative to LOCAL_DIRECTORY, effectively one level up from script's dir.
BQRM_OUTPUT_ROOT="${LOCAL_DIRECTORY}/../"

log_info "Configuration variables loaded:"
log_info "  BUFR_INPUT_ROOT: ${BUFR_INPUT_ROOT}"
log_info "  LOCAL_DIRECTORY: ${LOCAL_DIRECTORY}"
log_info "  BQRM_OUTPUT_ROOT: ${BQRM_OUTPUT_ROOT}"

# FTP Server Information
FTP_SERVER="ftp1.meteo.dz"
FTP_USERNAME="messir"
FTP_PASSWORD="123Messir123"
REMOTE_DIRECTORY="/share/ARPEGE+01+SP1" # Directory on the FTP server

log_info "FTP Server details: Server=${FTP_SERVER}, Remote Directory=${REMOTE_DIRECTORY}"

# SFTP Server Information (commented out as in original, but variables are defined for future use)
#SFTP_SERVER="192.168.0.122"
#SFTP_USERNAME="pnt"
#SFTP_REMOTE_DIRECTORY_DD="/home/cnpm/BDO/out/SYNOP/CONV-BUFR/${AA}/${MM}/${DD}/06/alg"
#SFTP_REMOTE_DIRECTORY_DDprec="/home/cnpm/BDO/out/SYNOP/CONV-BUFR/${AA}/${MM}/${DDprec}/18/alg"

# --- FTP Connection and Arpege File Download ---
log_info "Initiating FTP connection to ${FTP_SERVER} to download Arpege files..."
# Temporarily disable -e for the ftp command as its exit code is checked explicitly
set +e
ftp -n "${FTP_SERVER}" <<END_SCRIPT
quote USER "${FTP_USERNAME}"
quote PASS "${FTP_PASSWORD}"
lcd "${LOCAL_DIRECTORY}"
cd "${REMOTE_DIRECTORY}"
binary  # Switch to binary mode
prompt off
mget YMID41_LFPW_${DD}*
quit
END_SCRIPT
FTP_EXIT_CODE=$?
set -e # Re-enable -e

if [ ${FTP_EXIT_CODE} -eq 0 ]; then
   log_info "FTP download of Arpege files successful (exit code: ${FTP_EXIT_CODE})."
   log_info "Moving downloaded Arpege files to temporary processing directories."
   mv "${LOCAL_DIRECTORY}/YMID41_LFPW_${DD}00"* "${LOCAL_DIRECTORY}/../arpege_geopotentiel_temperature" || log_error "Failed to move YMID41_LFPW_${DD}00* files. Script may fail later."
   mv "${LOCAL_DIRECTORY}/YMID41_LFPW_${DD}06"* "${LOCAL_DIRECTORY}/../arpege_mslp" || log_error "Failed to move YMID41_LFPW_${DD}06* files. Script may fail later."
else
   log_error "Failed to download files from FTP server. FTP command exited with code ${FTP_EXIT_CODE}. Exiting script."
   exit 1 # Critical error, exit
fi

# Ensure we are in the LOCAL_DIRECTORY for subsequent operations
log_info "Changing current directory to ${LOCAL_DIRECTORY}."
cd "${LOCAL_DIRECTORY}" || { log_error "Failed to change to ${LOCAL_DIRECTORY}. Exiting."; exit 1; }

# --- BUFR File Processing (Local Generation Block - Placeholder) ---
# This block processes SMAL files to generate local BUFR files.
# The SMAL files are now sourced from the flexible BUFR_INPUT_ROOT.
log_info "Placeholder: Processing SMAL files to generate local BUFR files (this section was commented out in original code)."


# --- Main Processing Logic ---
# Copy BUFR files from the specified source path (BUFR_INPUT_ROOT)
# These are the BUFR files that will be used by the Python scripts.
log_info "Copying BUFR files from source path: ${LOCAL_DIRECTORY}/../../${BUFR_INPUT_ROOT}."

# Temporarily disable -e for cp commands as their exit codes are checked explicitly
set +e
cp "${LOCAL_DIRECTORY}/../../${BUFR_INPUT_ROOT}/${AAprec}/${MMprec}/${DDprec}/Synop_${AAprec}${MMprec}${DDprec}1800.bufr"  "${LOCAL_DIRECTORY}/../synop_alg_${AAprec}${MMprec}${DDprec}1800.bufr"
CP_EXIT_CODE_1=$?
cp "${LOCAL_DIRECTORY}/../../${BUFR_INPUT_ROOT}/${AA}/${MM}/${DD}/Synop_${AA}${MM}${DD}0600.bufr" "${LOCAL_DIRECTORY}/../synop_alg_${AA}${MM}${DD}0600.bufr"
CP_EXIT_CODE_2=$?
set -e # Re-enable -e

# Check if the BUFR file copy was successful
if [ ${CP_EXIT_CODE_1} -eq 0 ] && [ ${CP_EXIT_CODE_2} -eq 0 ]; then
   log_info "BUFR files copied successfully to ${LOCAL_DIRECTORY}/../."

   # Execute Python scripts once files are downloaded/copied
   log_info "Executing Python processing scripts."

   # Python script: Arpege_geopotentiel_temperature_plot.py
   log_info "Running Arpege_geopotentiel_temperature_plot.py..."
   python3 Arpege_geopotentiel_temperature_plot.py "${LOCAL_DIRECTORY}/../arpege_geopotentiel_temperature"
   if [ $? -eq 0 ]; then
       log_info "Arpege_geopotentiel_temperature_plot.py executed successfully."
   else
       log_error "Arpege_geopotentiel_temperature_plot.py failed. Exit code: $?. This might affect output."
   fi

   # Python script: Arpege_mslp_plot.py
   log_info "Running Arpege_mslp_plot.py..."
   python3 Arpege_mslp_plot.py "${LOCAL_DIRECTORY}/../arpege_mslp"
   if [ $? -eq 0 ]; then
       log_info "Arpege_mslp_plot.py executed successfully."
   else
       log_error "Arpege_mslp_plot.py failed. Exit code: $?. This might affect output."
   fi

   # Python script: BufrToXLS_ref.py
   log_info "Running BufrToXLS_ref.py..."
   python3 BufrToXLS_ref.py
   if [ $? -eq 0 ]; then
       log_info "BufrToXLS_ref.py executed successfully."
   else
       log_error "BufrToXLS_ref.py failed. Exit code: $?. This is a critical step."
       # Decide if this is a critical failure that should stop the script
       # For now, let's continue, but consider adding 'exit 1' here if output.xlsx is essential.
   fi

   # Python script: send_MSG.py (commented out in original script)
   # log_info "Running send_MSG.py..."
   # python3 send_MSG.py
   # if [ $? -eq 0 ]; then
   #     log_info "send_MSG.py executed successfully."
   # else
   #     log_error "send_MSG.py failed. Exit code: $?."
   # fi

else
   log_error "Failed to copy one or both required BUFR files from ${BUFR_INPUT_ROOT}."
   log_error "Copy attempt 1 exit code: ${CP_EXIT_CODE_1}, Copy attempt 2 exit code: ${CP_EXIT_CODE_2}."
   log_error "Cannot proceed with Python scripts. Exiting script."
   exit 1 # Critical error, exit
fi

# --- Cleanup and Archiving ---
log_info "Starting cleanup and archiving operations."

# Remove temporary Arpege files and directories
log_info "Removing temporary Arpege directories: arpege_mslp and arpege_geopotentiel_temperature."
rm -rf "${LOCAL_DIRECTORY}/../arpege_mslp" || log_error "Failed to remove ${LOCAL_DIRECTORY}/../arpege_mslp. (Non-critical)"
rm -rf "${LOCAL_DIRECTORY}/../arpege_geopotentiel_temperature" || log_error "Failed to remove ${LOCAL_DIRECTORY}/../arpege_geopotentiel_temperature. (Non-critical)"

# Remove locally generated Synop text files and BUFR files (from the 'cat' and 'synop2bufr.exe' block, if they were generated)
log_info "Removing temporary Synop text and BUFR files."
rm -f "Synop_${AAprec}${MMprec}${DDprec}1800" || log_error "Failed to remove Synop_${AAprec}${MMprec}${DDprec}1800. (Non-critical)"
rm -f "Synop_${AAprec}${MMprec}${DDprec}1800.bufr" || log_error "Failed to remove Synop_${AAprec}${MMprec}${DDprec}1800.bufr. (Non-critical)"
rm -f "Synop_${AA}${MM}${DD}0600" || log_error "Failed to remove Synop_${AA}${MM}${DD}0600. (Non-critical)"
rm -f "Synop_${AA}${MM}${DD}0600.bufr" || log_error "Failed to remove Synop_${AA}${MM}${DD}0600.bufr. (Non-critical)"

# Remove other temporary/output files generated by Python scripts
log_info "Removing other temporary output files (xlsx, png)."
rm -f "${LOCAL_DIRECTORY}/../output.xlsx" || log_error "Failed to remove ${LOCAL_DIRECTORY}/../output.xlsx. (Non-critical)"
rm -f "${LOCAL_DIRECTORY}/../Bulletin_"*.xlsx || log_error "Failed to remove ${LOCAL_DIRECTORY}/../Bulletin_*.xlsx. (Non-critical)"
rm -f "${LOCAL_DIRECTORY}/../geopotential_and_temperature_"*.png || log_error "Failed to remove ${LOCAL_DIRECTORY}/../geopotential_and_temperature_*.png. (Non-critical)"
rm -f "${LOCAL_DIRECTORY}/../mslp_"*.png || log_error "Failed to remove ${LOCAL_DIRECTORY}/../mslp_*.png. (Non-critical)"
rm -f "${LOCAL_DIRECTORY}/YMID"* || log_error "Failed to remove ${LOCAL_DIRECTORY}/YMID*. (Original downloaded Arpege files) (Non-critical)"

# Create destination directories using the flexible BQRM_OUTPUT_ROOT
log_info "Creating final output directories under ${BQRM_OUTPUT_ROOT}."
mkdir -p "${BQRM_OUTPUT_ROOT}/bulletins/${AA}/${MM}/${DD}" || log_error "Failed to create directory ${BQRM_OUTPUT_ROOT}/bulletins/${AA}/${MM}/${DD}. Exiting."
mkdir -p "${BQRM_OUTPUT_ROOT}/data/${AAprec}/${MMprec}/${DDprec}" || log_error "Failed to create directory ${BQRM_OUTPUT_ROOT}/data/${AAprec}/${MMprec}/${DDprec}. Exiting."
mkdir -p "${BQRM_OUTPUT_ROOT}/data/${AA}/${MM}/${DD}" || log_error "Failed to create directory ${BQRM_OUTPUT_ROOT}/data/${AA}/${MM}/${DD}. Exiting."

# Move processed BUFR files and documents to their final archive locations
log_info "Moving processed BUFR files and generated documents to archive locations."
mv "${LOCAL_DIRECTORY}/../synop_alg_${AAprec}${MMprec}${DDprec}1800.bufr" "${BQRM_OUTPUT_ROOT}/data/${AAprec}/${MMprec}/${DDprec}/." || log_error "Failed to move synop_alg_${AAprec}${MMprec}${DDprec}1800.bufr. Exiting."
mv "${LOCAL_DIRECTORY}/../synop_alg_${AA}${MM}${DD}0600.bufr" "${BQRM_OUTPUT_ROOT}/data/${AA}/${MM}/${DD}/." || log_error "Failed to move synop_alg_${AA}${MM}${DD}0600.bufr. Exiting."
mv "${LOCAL_DIRECTORY}/../BQRM_${AA}${MM}${DD}0600.docx" "${BQRM_OUTPUT_ROOT}/bulletins/${AA}/${MM}/${DD}/." || log_error "Failed to move BQRM_${AA}${MM}${DD}0600.docx. Exiting."

# Backup operations (commented out as in original, adjust paths if uncommenting)
#log_info "Performing backup operations (currently commented out)."
#cd
#mkdir -p backup/${AA}${MM}${DD}
#cp SMAL*${DD}0600*  backup/${AA}${MM}${DD}/.
#mv SMAL*${DDprec}1800* backup/${AA}${MM}${DD}/.

log_info "-------------------------------------------------------------------"
log_info "Script BQRM_ref.sh finished successfully."
log_info "-------------------------------------------------------------------"
