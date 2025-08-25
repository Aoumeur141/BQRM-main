# ~/bqrm/BMSLA/scr/1-get_arpege.py
import argparse
import os
import datetime
import logging
import subprocess
import sys
import fnmatch
from pathlib import Path
from typing import Optional
import re # Added for regular expressions

# Import functions from your pytaps package
from pytaps.fetchdata import list_remote_files, fetch_remote_files
from pytaps.file_operations import generate_met_filename
from pytaps.system_utils import execute_command
from pytaps.logging_utils import setup_logger

# --- Configuration ---
FTP_SERVER_HOST = "ftp1.meteo.dz"
FTP_USERNAME = "messir"
FTP_PASSWORD = "123Messir123"
REMOTE_BASE_DIRECTORY = "/share/meteofrance/Arpege_Orig"

# --- ARPEGE Specific Configuration ---
# Define the expected forecast steps for ARPEGE files
ARPEGE_EXPECTED_FORECAST_STEPS = [
    "00H12H", "13H24H", "25H36H", "37H48H", "49H60H",
    "61H72H", "73H84H", "85H96H", "97H102H",
]

def extract_forecast_step(filename: str) -> Optional[str]:
    """
    Extracts the forecast step (e.g., "00H12H") from an ARPEGE filename.
    Example filename: W_fr-meteofrance,MODEL,ARPEGE+01+SP1+00H12H_C_LFPW_202508240000--.grib2
    """
    # Regex to find the pattern like "+SP1+XXHXXH_C_LFPW"
    match = re.search(r'\+SP1\+(\w+H\w+H)_C_LFPW', filename)
    if match:
        return match.group(1)
    return None

# --- Dynamically Determine Paths for DATA/TEMP files ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
TMP_DIR = os.path.join(PARENT_DIR, "tmp")

# --- Setup Logging ---
script_name = os.path.basename(__file__)
log_file_base_name = "sonelgaz"
shared_log_file_path_from_env = os.getenv('SHARED_LOG_FILE_PATH')

logger, current_log_file_path = setup_logger(
    script_name=log_file_base_name,
    log_directory_base=SCRIPT_DIR,
    log_level=logging.INFO,
    shared_log_file_path=None
)

# --- Script Start ---
logger.info(f"--- Script '{script_name}' started ---")
logger.info(f"Logger configured. All logs for this workflow will be saved to: {current_log_file_path}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Script directory: {SCRIPT_DIR}")
logger.info(f"Parent directory dynamically set to: {PARENT_DIR}")
logger.info(f"Temporary directory for FTP download: {TMP_DIR}")
logger.info(f"Remote FTP directory: {REMOTE_BASE_DIRECTORY}")

os.makedirs(TMP_DIR, exist_ok=True)
logger.info(f"Ensured temporary directory exists: {TMP_DIR}")

try:
    # --- Get Date and File Pattern ---
    current_date_obj = datetime.date.today()
    FILE_DATE_STR = current_date_obj.strftime("%Y%m%d")

    FULL_FILE_PATTERN = generate_met_filename(current_date_obj)
    logger.info(f"Fetching files for date: {FILE_DATE_STR} with pattern: {FULL_FILE_PATTERN}")

    # --- Check if files exist on the FTP server ---
    logger.info("Checking if ARPEGE files exist on FTP server and verifying completeness...")

    matching_remote_files = list_remote_files(
        host=FTP_SERVER_HOST,
        username=FTP_USERNAME,
        password=FTP_PASSWORD,
        remote_dir=REMOTE_BASE_DIRECTORY,
        filename_pattern=FULL_FILE_PATTERN
    )

    # --- New: Detailed check for expected forecast steps ---
    found_forecast_steps = set()
    for filename in matching_remote_files:
        step = extract_forecast_step(filename)
        if step:
            found_forecast_steps.add(step)
        else:
            logger.warning(f"Could not extract forecast step from remote file: {filename}. This file will be ignored in completeness check.")

    expected_forecast_steps_set = set(ARPEGE_EXPECTED_FORECAST_STEPS)
    missing_forecast_steps = expected_forecast_steps_set - found_forecast_steps
    extra_found_steps = found_forecast_steps - expected_forecast_steps_set # Files found that were not in our expected list

    # Determine if we should proceed with ARPEGE or switch to ALADIN
    if not matching_remote_files:
        logger.info(f"No ARPEGE files found on FTP server for date {FILE_DATE_STR} with pattern '{FULL_FILE_PATTERN}'.")
        should_run_aladin = True
    elif missing_forecast_steps:
        logger.error(f"ERROR: Incomplete ARPEGE dataset on FTP server for date {FILE_DATE_STR}.")
        logger.error(f"Missing forecast steps: {', '.join(sorted(missing_forecast_steps))}")
        logger.info("Due to missing ARPEGE files, launching 1-get-aladin.py instead.")
        should_run_aladin = True
    else:
        logger.info(f"All {len(ARPEGE_EXPECTED_FORECAST_STEPS)} expected ARPEGE forecast steps found on FTP server for date {FILE_DATE_STR}.")
        should_run_aladin = False

    if extra_found_steps:
        logger.warning(f"WARNING: Found unexpected ARPEGE forecast steps on FTP server: {', '.join(sorted(extra_found_steps))}. These will be downloaded.")

    if should_run_aladin:
        aladin_script_path = os.path.join(SCRIPT_DIR, "1-get-aladin.py")
        try:
            logger.info(f"Executing: {sys.executable} {aladin_script_path} --shared-log-file {current_log_file_path}")
            execute_command(
                [sys.executable, aladin_script_path, "--shared-log-file", current_log_file_path],
                cwd=SCRIPT_DIR
            )
            logger.info("Python script '1-get-aladin.py' completed successfully.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Failed to execute 1-get-aladin.py: {e}")
            sys.exit(1)
    else:
        logger.info(f"Found {len(matching_remote_files)} matching ARPEGE files on FTP server:")
        for f in matching_remote_files:
            logger.info(f"  - {f}")

        # --- Prepare files for fetch_remote_files ---
        files_to_download = []
        for remote_filename in matching_remote_files:
            remote_full_path = os.path.join(REMOTE_BASE_DIRECTORY, remote_filename)
            local_full_path = os.path.join(TMP_DIR, remote_filename)
            files_to_download.append({
                'remote_path': remote_full_path,
                'local_path': Path(local_full_path)
            })

        # --- FTP File Transfer using fetch_remote_files ---
        logger.info("Proceeding with FTP download using fetch_remote_files.")
        logger.info(f"Attempting to download {len(files_to_download)} files to {TMP_DIR}.")

        fetch_remote_files(
            protocol='ftp',
            host=FTP_SERVER_HOST,
            port=None,
            username=FTP_USERNAME,
            password=FTP_PASSWORD,
            files_to_process=files_to_download,
            logger_instance=logger
        )
        logger.info(f"FTP transfer process initiated by fetch_remote_files completed.")

        # Optional: Verify if files were actually downloaded to TMP_DIR
        successful_downloads = 0
        for file_info in files_to_download:
            local_path = file_info['local_path']
            if local_path.exists() and local_path.stat().st_size > 0:
                logger.info(f"Verified: {local_path.name} exists and is not empty.")
                successful_downloads += 1
            else:
                logger.error(f"Verification failed: {local_path.name} is missing or empty after download attempt.")

        if successful_downloads == 0 and len(files_to_download) > 0:
            logger.error(f"ERROR: No files were successfully downloaded to '{TMP_DIR}', despite being listed on FTP.")
            sys.exit(1)
        elif successful_downloads < len(files_to_download):
            logger.error(f"ERROR: Incomplete download. Only {successful_downloads} out of {len(files_to_download)} files were successfully downloaded. Exiting.")
            sys.exit(1)
        else:
            logger.info(f"Successfully verified all {successful_downloads} files downloaded to '{TMP_DIR}'.")

        # --- Run Next Program (only if ARPEGE download was successful) ---
        logger.info(f"Attempting to run next program: 2-conv.py")
        try:
            execute_command(
                [sys.executable, os.path.join(SCRIPT_DIR, "2-conv.py"), current_log_file_path],
                cwd=SCRIPT_DIR
            )
            logger.info("Successfully executed 2-conv.py.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.exception(f"An error occurred while running 2-conv.py: {e}")
            sys.exit(1)

except Exception as e:
    logger.exception(f"An unexpected error occurred in the main script flow: {e}")
    sys.exit(1)

logger.info(f"--- Script '{script_name}' finished. ---")
