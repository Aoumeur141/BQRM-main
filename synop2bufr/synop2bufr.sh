#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e
# Treat unset variables as an error when substituting.
set -u
# Exit if any command in a pipeline fails.
set -o pipefail

# --- Directory Setup ---
# Get the script's absolute directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_DIRECTORY="${SCRIPT_DIR}"
BASE_DIR="$(dirname "${LOCAL_DIRECTORY}")"

# DATA_DIR: Location of raw TAC observation files.
# IMPORTANT: Verify this path. It's currently set relative to the script's parent's parent,
# assuming 'bqrm_data' is a sibling to 'onm' (e.g., /home/user/bqrm_data/observations).
DATA_DIR="../../../../bqrm_data/observations" 

TMP_DIR="${LOCAL_DIRECTORY}/tmp"
BUFR_OUTPUT_BASE_DIR="${LOCAL_DIRECTORY}/../bufr_data/observations"

# External executable and its data directory
SYNOP2BUFR_EXE="${LOCAL_DIRECTORY}/synop2bufr.exe"
SYNOP2BUFR_DAT_DIR="${LOCAL_DIRECTORY}/dat"

# --- Logging Setup ---
LOG_DIR="${LOCAL_DIRECTORY}/logs"
LOG_FILE="${LOG_DIR}/synop2bufr_script.log"

# Ensure the log directory exists
mkdir -p "$(dirname "${LOG_FILE}")" || { echo "FATAL: $(date '+%Y-%m-%d %H:%M:%S') - Could not create log directory $(dirname "${LOG_FILE}")" >&2; exit 1; }

# Redirect all stdout and stderr to the log file and console
exec > >(tee -a "${LOG_FILE}") 2>&1

# --- Logging Functions ---
log_info() {
   echo "INFO: $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
   echo "WARNING: $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

log_error() {
   echo "ERROR: $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
   exit 1
}


log_info "Script started. Log file: ${LOG_FILE}"
log_info "Configured paths: SCRIPT_DIR=${SCRIPT_DIR}, DATA_DIR=${DATA_DIR}, TMP_DIR=${TMP_DIR}, BUFR_OUTPUT_BASE_DIR=${BUFR_OUTPUT_BASE_DIR}"

# --- Initial Directory and File Checks ---
log_info "Performing initial directory and file checks."
mkdir -p "${TMP_DIR}" || log_error "Failed to create temporary directory: ${TMP_DIR}. Check permissions or path."

if [ ! -d "${DATA_DIR}" ]; then
   log_error "Input data directory not found: ${DATA_DIR}. Please check DATA_DIR variable."
fi
if [ ! -f "${SYNOP2BUFR_EXE}" ]; then
   log_error "synop2bufr executable not found: ${SYNOP2BUFR_EXE}. Ensure it's compiled and placed in ${LOCAL_DIRECTORY}."
fi
if [ ! -d "${SYNOP2BUFR_DAT_DIR}" ]; then
   log_error "synop2bufr 'dat' directory not found: ${SYNOP2BUFR_DAT_DIR}. Ensure it's placed in ${LOCAL_DIRECTORY}."
fi
log_info "All required directories and files exist."

# --- Date Variable Setup ---
YESTERDAY_DATE=$(date -d yesterday +"%Y%m%d")
Y_AA=$(echo "${YESTERDAY_DATE}" | cut -c1-4)
Y_MM=$(echo "${YESTERDAY_DATE}" | cut -c5-6)
Y_DD=$(echo "${YESTERDAY_DATE}" | cut -c7-8)

TODAY_DATE=$(date +"%Y%m%d")
T_AA=$(echo "${TODAY_DATE}" | cut -c1-4)
T_MM=$(echo "${TODAY_DATE}" | cut -c5-6)
T_DD=$(echo "${TODAY_DATE}" | cut -c7-8)

log_info "Processing data for ${Y_AA}/${Y_MM}/${Y_DD} (yesterday) and ${T_AA}/${T_MM}/${T_DD} (today)."

# --- Data Availability Check Parameters ---
# Maximum number of times to retry checking for data.
# For example, 6 retries * 10 minutes/retry = 60 minutes (1 hour) total wait.
MAX_DATA_RETRIES=6
# Time in seconds to wait between data availability checks.
DATA_RETRY_INTERVAL_SEC=600 # 10 minutes

# --- File Copy Operations (with Retry Loop) ---
log_info "Attempting to copy files from ${DATA_DIR} to ${TMP_DIR}. Will retry if data is not immediately available."

retries=0
data_found=false

# Function to safely copy files
# Arguments: $1 = source_pattern, $2 = destination_directory
copy_files() {
   local source_pattern="$1"
   local dest_dir="$2"
   # Enable nullglob temporarily for this function to handle no-match cases gracefully
   shopt -s nullglob
   local files_to_copy=(${source_pattern})
   shopt -u nullglob # Disable it immediately after expansion

   if [ ${#files_to_copy[@]} -eq 0 ]; then
       log_warn "No files found matching pattern: '${source_pattern}'. Skipping copy."
       # Return 1 to indicate no files were found for this pattern.
       # This return value will be handled by '|| true' in the calling loop.
       return 1
   else
       for file in "${files_to_copy[@]}"; do
           # If 'cp' fails here, 'log_error' will be called, which exits the script.
           # This ensures genuine copy errors still stop the script.
           cp "${file}" "${dest_dir}/" || log_error "Failed to copy: '$(basename "${file}")' to '${dest_dir}/'. Check permissions or disk space."
           log_info "Copied: '$(basename "${file}")' to '${dest_dir}/'"
       done
       return 0 # Return 0 for success (at least one file copied or no error)
   fi
}


# This loop will keep trying to copy files until data is found or max retries are exhausted.
while [ "${retries}" -lt "${MAX_DATA_RETRIES}" ]; do
    log_info "--- Data Check Attempt $((retries + 1))/${MAX_DATA_RETRIES} ---"

    # Clear TMP_DIR contents before each retry to ensure we're checking for fresh data.
    if [ -d "${TMP_DIR}" ]; then
        if [ -n "$(ls -A "${TMP_DIR}")" ]; then
            log_info "Clearing contents of ${TMP_DIR} for a fresh check..."
            rm -rf "${TMP_DIR}"/* || log_warn "Failed to clear contents of ${TMP_DIR}. This might lead to processing stale data."
        else
            log_info "Temporary directory ${TMP_DIR} is already empty for a fresh check."
        fi
    fi
    
    # Attempt to copy files for yesterday and today.
    # IMPORTANT: We add '|| true' after each 'copy_files' call.
    # This ensures that if 'copy_files' returns 1 (meaning "no files found for this pattern"),
    # 'set -e' does NOT immediately exit the script. Instead, the '|| true' makes the
    # command succeed from 'set -e' perspective, allowing the loop to continue.
    # If 'cp' inside 'copy_files' fails, 'log_error' will still cause an exit.
    log_info "Attempting to copy yesterday's SMAL files..."
    copy_files "${DATA_DIR}/${Y_AA}/${Y_MM}/${Y_DD}/SMAL*${Y_DD}0000*" "${TMP_DIR}" || true
    copy_files "${DATA_DIR}/${Y_AA}/${Y_MM}/${Y_DD}/SMAL*${Y_DD}0600*" "${TMP_DIR}" || true
    copy_files "${DATA_DIR}/${Y_AA}/${Y_MM}/${Y_DD}/SMAL*${Y_DD}1200*" "${TMP_DIR}" || true
    copy_files "${DATA_DIR}/${Y_AA}/${Y_MM}/${Y_DD}/SMAL*${Y_DD}1800*" "${TMP_DIR}" || true
    
    log_info "Attempting to copy yesterday's SIAL files..."
    copy_files "${DATA_DIR}/${Y_AA}/${Y_MM}/${Y_DD}/SIAL*${Y_DD}0300*" "${TMP_DIR}" || true
    copy_files "${DATA_DIR}/${Y_AA}/${Y_MM}/${Y_DD}/SIAL*${Y_DD}0900*" "${TMP_DIR}" || true
    copy_files "${DATA_DIR}/${Y_AA}/${Y_MM}/${Y_DD}/SIAL*${Y_DD}1500*" "${TMP_DIR}" || true
    copy_files "${DATA_DIR}/${Y_AA}/${Y_MM}/${Y_DD}/SIAL*${Y_DD}2100*" "${TMP_DIR}" || true

    log_info "Attempting to copy today's SMAL files..."
    copy_files "${DATA_DIR}/${T_AA}/${T_MM}/${T_DD}/SMAL*${T_DD}0000*" "${TMP_DIR}" || true
    copy_files "${DATA_DIR}/${T_AA}/${T_MM}/${T_DD}/SMAL*${T_DD}0600*" "${TMP_DIR}" || true

    # Check if any files were successfully copied into TMP_DIR in this attempt.
    # 'ls -A "${TMP_DIR}"' lists all files/directories including hidden ones (but not . or ..).
    # 'wc -l' counts the lines (i.e., number of items).
    # If the count is greater than 0, it means some data files were found and copied.
    if [ "$(ls -A "${TMP_DIR}" | wc -l)" -gt 0 ]; then
        log_info "SUCCESS: Data files found and copied to temporary directory. Proceeding with processing."
        data_found=true
        break # Exit the retry loop as data is now available.
    else
        log_warn "No data files found in ${DATA_DIR} for the required periods after this attempt."
        retries=$((retries + 1))
        if [ "${retries}" -lt "${MAX_DATA_RETRIES}" ]; then
            log_info "Sleeping for ${DATA_RETRY_INTERVAL_SEC} seconds before next attempt... (Attempt ${retries} of ${MAX_DATA_RETRIES})"
            sleep "${DATA_RETRY_INTERVAL_SEC}"
            log_info "Waking up for next data check attempt."
        fi
    fi
done

# After the loop, check if data was ever found. If not, exit with an error.
if [ "${data_found}" == "false" ]; then
    log_error "FATAL: Exceeded maximum retries (${MAX_DATA_RETRIES}) to find data files. No data processed. Please check data source: ${DATA_DIR}"
fi

log_info "Finished initial data collection and copying to temporary directory."

# --- File Concatenation and Filtering ---
log_info "Changing directory to ${TMP_DIR} for file processing."
cd "${TMP_DIR}" || log_error "Failed to change directory to ${TMP_DIR}. Script cannot proceed."

# Function to safely concatenate and filter files
# Arguments: $1 = input_pattern, $2 = output_file_name
concatenate_and_filter() {
   local input_pattern="$1"
   local output_file="$2"
   local temp_output="${output_file}.tmp"
   
   shopt -s nullglob # Re-enable nullglob for pattern expansion
   local files_to_cat=(${input_pattern})
   shopt -u nullglob

   if [ ${#files_to_cat[@]} -eq 0 ]; then
       log_warn "No source files found for pattern: '${input_pattern}'. Creating empty output file: '${output_file}'."
       touch "${output_file}"
       return 1
   fi

   cat "${files_to_cat[@]}" 2>/dev/null | sed '/^60.*NIL=/d' > "${temp_output}"
   local cat_status=$?

   if [ ${cat_status} -eq 0 ]; then
       if [ -s "${temp_output}" ]; then
           mv "${temp_output}" "${output_file}" || log_error "Failed to move temporary file '${temp_output}' to '${output_file}'. Check permissions."
           log_info "Created '${output_file}' from '${input_pattern}'."
       else
           log_warn "Output file '${output_file}' is empty after filtering from '${input_pattern}'. No valid data produced. Moving empty temp file to destination."
           mv "${temp_output}" "${output_file}" # Move empty file so subsequent steps don't fail on missing file
       fi
   else
       log_error "Failed to concatenate and filter files for '${output_file}' from '${input_pattern}'. Cat/sed command failed with status ${cat_status}."
   fi
}


# Concatenate and filter SIAL files (yesterday)
concatenate_and_filter "SIAL*${Y_DD}0300*" "Synop_${Y_AA}${Y_MM}${Y_DD}0300"
concatenate_and_filter "SIAL*${Y_DD}0900*" "Synop_${Y_AA}${Y_MM}${Y_DD}0900"
concatenate_and_filter "SIAL*${Y_DD}1500*" "Synop_${Y_AA}${Y_MM}${Y_DD}1500"
concatenate_and_filter "SIAL*${Y_DD}2100*" "Synop_${Y_AA}${Y_MM}${Y_DD}2100"

# Concatenate and filter SMAL files (yesterday)
concatenate_and_filter "SMAL*${Y_DD}0000*" "Synop_${Y_AA}${Y_MM}${Y_DD}0000"
concatenate_and_filter "SMAL*${Y_DD}0600*" "Synop_${Y_AA}${Y_MM}${Y_DD}0600"
concatenate_and_filter "SMAL*${Y_DD}1200*" "Synop_${Y_AA}${Y_MM}${Y_DD}1200"
concatenate_and_filter "SMAL*${Y_DD}1800*" "Synop_${Y_AA}${Y_MM}${Y_DD}1800"

# Concatenate and filter SMAL files (today)
concatenate_and_filter "SMAL*${T_DD}0000*" "Synop_${T_AA}${T_MM}${T_DD}0000"
concatenate_and_filter "SMAL*${T_DD}0600*" "Synop_${T_AA}${T_MM}${T_DD}0600"
log_info "Finished concatenating TAC files."

# --- Conversion to BUFR Format ---
log_info "Copying synop2bufr.exe and dat directory to ${TMP_DIR}."
cp -f "${SYNOP2BUFR_EXE}" . || log_error "Failed to copy synop2bufr.exe to ${TMP_DIR}. Check source path and permissions."
cp -rf "${SYNOP2BUFR_DAT_DIR}" . || log_error "Failed to copy synop2bufr 'dat' directory to ${TMP_DIR}. Check source path and permissions."

log_info "Starting conversion of TAC files to BUFR format."

# Function to safely convert files using synop2bufr.exe
# Arguments: $1 = input_file, $2 = output_file, $3 = channel
convert_to_bufr() {
   local input_file="$1"
   local output_file="$2"
   local channel="$3"

   if [ ! -f "${input_file}" ]; then
       log_warn "Input file for conversion not found: '${input_file}'. Skipping conversion."
       return 1
   fi

   # Check if the input file is empty before attempting conversion
   if [ ! -s "${input_file}" ]; then
       log_warn "Input file '${input_file}' is empty. Skipping conversion to avoid creating empty BUFR file."
       return 1 # Indicate that conversion was skipped, not failed.
   fi

   ./synop2bufr.exe -i "${input_file}" -o "${output_file}" -c "${channel}" || \
       log_error "Failed to convert '${input_file}' to '${output_file}'. Check synop2bufr.exe output."
   
   # After conversion, check if the output BUFR file was actually created and is not empty.
   if [ ! -s "${output_file}" ]; then
       log_warn "Conversion of '${input_file}' completed, but output BUFR file '${output_file}' is empty or not created. This might indicate an issue with the input data or synop2bufr.exe."
       # Optionally, remove the empty BUFR file if it was created, to prevent downstream issues.
        rm -f "${output_file}"
       return 1 # Indicate a problem with the output, even if synop2bufr.exe returned 0.
   fi

   log_info "Converted '${input_file}' to '${output_file}'."
}

# Convert files for yesterday
convert_to_bufr "Synop_${Y_AA}${Y_MM}${Y_DD}0000" "Synop_${Y_AA}${Y_MM}${Y_DD}0000.bufr" 96
convert_to_bufr "Synop_${Y_AA}${Y_MM}${Y_DD}0600" "Synop_${Y_AA}${Y_MM}${Y_DD}0600.bufr" 96
convert_to_bufr "Synop_${Y_AA}${Y_MM}${Y_DD}1200" "Synop_${Y_AA}${Y_MM}${Y_DD}1200.bufr" 96
convert_to_bufr "Synop_${Y_AA}${Y_MM}${Y_DD}1800" "Synop_${Y_AA}${Y_MM}${Y_DD}1800.bufr" 96
convert_to_bufr "Synop_${Y_AA}${Y_MM}${Y_DD}0300" "Synop_${Y_AA}${Y_MM}${Y_DD}0300.bufr" 96
convert_to_bufr "Synop_${Y_AA}${Y_MM}${Y_DD}0900" "Synop_${Y_AA}${Y_MM}${Y_DD}0900.bufr" 96
convert_to_bufr "Synop_${Y_AA}${Y_MM}${Y_DD}1500" "Synop_${Y_AA}${Y_MM}${Y_DD}1500.bufr" 96
convert_to_bufr "Synop_${Y_AA}${Y_MM}${Y_DD}2100" "Synop_${Y_AA}${Y_MM}${Y_DD}2100.bufr" 96

# Convert files for today
convert_to_bufr "Synop_${T_AA}${T_MM}${T_DD}0000" "Synop_${T_AA}${T_MM}${T_DD}0000.bufr" 96
convert_to_bufr "Synop_${T_AA}${T_MM}${T_DD}0600" "Synop_${T_AA}${T_MM}${T_DD}0600.bufr" 96

log_info "Finished converting TAC files to BUFR format."

# --- Move BUFR Files to Destination ---
log_info "Creating destination directories for BUFR output."
mkdir -p "${BUFR_OUTPUT_BASE_DIR}/${Y_AA}/${Y_MM}/${Y_DD}" || log_error "Failed to create output directory: ${BUFR_OUTPUT_BASE_DIR}/${Y_AA}/${Y_MM}/${Y_DD}. Check permissions or path."
mkdir -p "${BUFR_OUTPUT_BASE_DIR}/${T_AA}/${T_MM}/${T_DD}" || log_error "Failed to create output directory: ${BUFR_OUTPUT_BASE_DIR}/${T_AA}/${T_MM}/${T_DD}. Check permissions or path."

log_info "Moving BUFR files from ${TMP_DIR} to their final destinations."

# Function to safely move BUFR files
# Arguments: $1 = source_file, $2 = destination_directory
move_bufr_file() {
   local source_file="$1"
   local dest_dir="$2"

   if [ ! -f "${source_file}" ]; then
       log_warn "Source BUFR file not found: '${source_file}'. Skipping move."
       return 1
   fi

   # Added check: Ensure the BUFR file is not empty before moving it.
   if [ ! -s "${source_file}" ]; then
       log_warn "BUFR file '${source_file}' is empty. Not moving it to destination to avoid corrupted data."
       rm -f "${source_file}" # Remove the empty file from TMP_DIR
       return 1
   fi

   mv "${source_file}" "${dest_dir}/" || log_error "Failed to move '${source_file}' to '${dest_dir}/'. Check permissions or disk space."
   log_info "Moved '${source_file}' to '${dest_dir}/'."
}



# Move files for yesterday
move_bufr_file "Synop_${Y_AA}${Y_MM}${Y_DD}0000.bufr" "${BUFR_OUTPUT_BASE_DIR}/${Y_AA}/${Y_MM}/${Y_DD}"
move_bufr_file "Synop_${Y_AA}${Y_MM}${Y_DD}0600.bufr" "${BUFR_OUTPUT_BASE_DIR}/${Y_AA}/${Y_MM}/${Y_DD}"
move_bufr_file "Synop_${Y_AA}${Y_MM}${Y_DD}1200.bufr" "${BUFR_OUTPUT_BASE_DIR}/${Y_AA}/${Y_MM}/${Y_DD}"
move_bufr_file "Synop_${Y_AA}${Y_MM}${Y_DD}1800.bufr" "${BUFR_OUTPUT_BASE_DIR}/${Y_AA}/${Y_MM}/${Y_DD}"
move_bufr_file "Synop_${Y_AA}${Y_MM}${Y_DD}0300.bufr" "${BUFR_OUTPUT_BASE_DIR}/${Y_AA}/${Y_MM}/${Y_DD}"
move_bufr_file "Synop_${Y_AA}${Y_MM}${Y_DD}0900.bufr" "${BUFR_OUTPUT_BASE_DIR}/${Y_AA}/${Y_MM}/${Y_DD}"
move_bufr_file "Synop_${Y_AA}${Y_MM}${Y_DD}1500.bufr" "${BUFR_OUTPUT_BASE_DIR}/${Y_AA}/${Y_MM}/${Y_DD}"
move_bufr_file "Synop_${Y_AA}${Y_MM}${Y_DD}2100.bufr" "${BUFR_OUTPUT_BASE_DIR}/${Y_AA}/${Y_MM}/${Y_DD}"

# Move files for today
move_bufr_file "Synop_${T_AA}${T_MM}${T_DD}0000.bufr" "${BUFR_OUTPUT_BASE_DIR}/${T_AA}/${T_MM}/${T_DD}"
move_bufr_file "Synop_${T_AA}${T_MM}${T_DD}0600.bufr" "${BUFR_OUTPUT_BASE_DIR}/${T_AA}/${T_MM}/${T_DD}"

log_info "Finished moving BUFR files."

# --- Cleanup Function ---
# This function will be executed automatically when the script exits (normally or abnormally).
cleanup() {
    log_info "Starting cleanup operations."
    if [ -d "${TMP_DIR}" ]; then
        log_info "Removing temporary directory: ${TMP_DIR}"
        rm -rf "${TMP_DIR}"
        if [ $? -eq 0 ]; then
            log_info "Temporary directory '${TMP_DIR}' successfully removed."
        else
            log_warn "Failed to remove temporary directory '${TMP_DIR}'. Manual cleanup may be required."
        fi
    else
        log_info "Temporary directory '${TMP_DIR}' does not exist or was already removed. No cleanup needed."
    fi
    log_info "Script finished."
}

# Register the cleanup function to be called on script exit.
# This ensures that TMP_DIR is removed even if the script fails.
trap cleanup EXIT