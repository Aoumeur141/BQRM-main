import json
import os
import subprocess
import logging
import sys
import argparse # Import argparse for command-line arguments
from pathlib import Path

# --- PyTaps Imports ---
from pytaps.logging_utils import setup_logger
from pytaps.date_time_utils import get_ymd_for_today_and_yesterday
from pytaps.system_utils import execute_command
from pytaps.fetchdata import fetch_remote_files as pytaps_fetch_remote_files

# --- Dynamically Determine Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = Path(SCRIPT_DIR).parent

# --- Argument Parsing ---
# Create an argument parser to handle command-line arguments
parser = argparse.ArgumentParser(description="Fetch ALADIN data from SFTP server.")
parser.add_argument(
    "--shared-log-file",
    type=str,
    default=None, # Default to None if not provided (for standalone execution)
    help="Path to a shared log file for the entire workflow. If not provided, a new log file will be created."
)
args = parser.parse_args() # Parse the arguments

# --- Logger Setup (using PyTaps) ---
log_file_base_name = "sonelgaz"

# Use the parsed shared_log_file argument for setup_logger
logger, current_log_file_path = setup_logger(
    script_name=log_file_base_name,
    log_directory_base=SCRIPT_DIR,
    log_level=logging.INFO, # Can be changed to logging.DEBUG for troubleshooting if needed
    shared_log_file_path=args.shared_log_file # <-- CRITICAL FIX: Pass the parsed argument here
)

# --- Script Start Logging ---
logger.info(f"--- Script '{os.path.basename(__file__)}' execution started. ---")
logger.info(f"Logger configured. Logs will be saved to: {current_log_file_path}")
logger.info(f"Current script directory: {SCRIPT_DIR}")
logger.info(f"Determined project root directory: {PROJECT_ROOT}")
logger.info(f"Current working directory (before change): {os.getcwd()}")
if args.shared_log_file:
    logger.info(f"Using shared log file path: {args.shared_log_file}")
else:
    logger.info("No shared log file path provided. Using script-specific log file.")

try:
    os.chdir(PROJECT_ROOT)
    logger.info(f"Changed current working directory to: {os.getcwd()}")
except OSError as e:
    logger.critical(f"Failed to change directory to {PROJECT_ROOT}: {e}")
    logger.critical("Exiting script due to critical directory change failure.")
    sys.exit(1)


# --- Configuration (Hardcoded) ---
config = {
  "host": "login2.fennec.meteo.dz",
  "username": "wchikhi",
  "password": "3112!Akila",
  "remote_path": "/fennecData/data/chprod/ALADIN/GRIB/{AAAA}/{MM}/{DD}/r00/",
  "local_path": "tmp",
  "filename_pattern": "grib_{AAAA}{MM}{DD}{RES}_00{ech}",
  "ech_ranges": [0, 48, 1], # Start, End (inclusive), Step
  "protocol": "sftp",
  "port": 22
}
logger.info("Configuration loaded directly from script variables (for ALADIN data).")
# --- End Configuration ---


# --- Date Preparation ---
try:
    AA_today, MM_today, DD_today, AA_yesterday, MM_yesterday, DD_yesterday = \
        get_ymd_for_today_and_yesterday(logger_instance=logger)
except Exception as e:
    logger.critical(f"Error during date preparation using pytaps.date_utils: {e}")
    logger.exception("Full traceback for date preparation error:")
    logger.critical("Exiting script due to critical date preparation failure.")
    sys.exit(1)

def fetch_aladin_files(config, AA, MM, DD, RES="00"):
    """
    Prepares the list of ALADIN files to fetch and then calls the unified
    pytaps_fetch_remote_files function to perform the actual download.
    """
    logger.info(f"Preparing ALADIN file list for date {AA}-{MM}-{DD} with resolution {RES}.")

    local_base_dir = PROJECT_ROOT / config['local_path']
    os.makedirs(local_base_dir, exist_ok=True)
    logger.debug(f"Ensured local base directory exists: {local_base_dir}")

    expected_echs = range(config['ech_ranges'][0], config['ech_ranges'][1] + 1, config['ech_ranges'][2])

    files_to_download_info = []

    for ech in expected_echs:
        ech_formatted = f"{ech:02d}"

        # Format remote_path and filename_pattern
        remote_file_path = (
            config['remote_path'].format(AAAA=AA, MM=MM, DD=DD) +
            config['filename_pattern'].format(AAAA=AA, MM=MM, DD=DD, RES=RES, ech=ech_formatted)
        )
        local_file_path = local_base_dir / config['filename_pattern'].format(AAAA=AA, MM=MM, DD=DD, RES=RES, ech=ech_formatted)

        files_to_download_info.append({
            'remote_path': remote_file_path,
            'local_path': local_file_path
        })

    logger.info(f"Prepared {len(files_to_download_info)} files for download.")

    try:
        pytaps_fetch_remote_files(
            protocol=config['protocol'],
            host=config['host'],
            port=config['port'],
            username=config['username'],
            password=config['password'],
            files_to_process=files_to_download_info,
            logger_instance=logger
        )
        logger.info(f"ALADIN file fetching process completed for {AA}-{MM}-{DD}.")
    except Exception as e:
        logger.error(f"Failed to fetch ALADIN files for {AA}-{MM}-{DD}: {e}")
        raise


if __name__ == "__main__":
    logger.info("--- Main script execution started ---")

    try:
        # Call the function to fetch ALADIN files
        fetch_aladin_files(config, AA_today, MM_today, DD_today, RES="00")

        # --- Run Next Program ---
        logger.info(f"Attempting to run next program: 2-conv.py")
        try:
            # Pass the current_log_file_path (which is now correctly shared if provided)
            execute_command(
                [sys.executable, os.path.join(SCRIPT_DIR, "2-conv.py"), current_log_file_path],
                cwd=SCRIPT_DIR
            )
            logger.info("Successfully executed 2-conv.py.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.exception(f"An error occurred while running 2-conv.py: {e}")
            sys.exit(1)

    except Exception as e:
       logger.critical(f"An unexpected error occurred in the main script flow: {e}")
       logger.exception("Full traceback for main script flow error:")
       sys.exit(1)

    logger.info(f"--- Script '{os.path.basename(__file__)}' finished. ---")
