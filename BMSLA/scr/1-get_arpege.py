# ~/bqrm/BMSLA/scr/1-get_arpepe.py
import argparse
import os
import datetime
import logging
import subprocess
import sys
import fnmatch
from pathlib import Path # Added for Path objects

# Import functions from your pytaps package
from pytaps.fetchdata import list_remote_files, fetch_remote_files

from pytaps.file_operations import generate_met_filename
from pytaps.system_utils import execute_command # Assuming this correctly uses subprocess.run
from pytaps.logging_utils import setup_logger # This is the key!

# --- Configuration ---
FTP_SERVER_HOST = "ftp1.meteo.dz"
FTP_USERNAME = "messir"
FTP_PASSWORD = "123Messir123"
REMOTE_BASE_DIRECTORY = "/share/meteofrance/Arpege_Orig"

# --- Dynamically Determine Paths for DATA/TEMP files ---
# SCRIPT_DIR is the directory where 1-get_arpege.py resides.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# PARENT_DIR is the directory above SCRIPT_DIR (e.g., ~/bqrm/BMSLA/ if script is in ~/bqrm/BMSLA/scr/)
PARENT_DIR = os.path.dirname(SCRIPT_DIR)

# Define temporary directory for FTP download (this is NOT managed by the logger_config)
TMP_DIR = os.path.join(PARENT_DIR, "tmp")

# --- Setup Logging ---
script_name = os.path.basename(__file__)

log_file_base_name = "BMSLA"

# Parse command-line arguments for a shared log file path
parser = argparse.ArgumentParser(description="1-get_arpege.py script for fetching ARPEGE data.")
parser.add_argument('--shared-log-file', type=str,
                   help='Path to a shared log file for chained scripts. If not provided, a new log file will be created.')
args = parser.parse_args()

# Configure the logger.
# The first script in the chain (1-get_arpege.py) will typically not receive --shared-log-file,
# so it will generate its own log file. This path will then be passed to subsequent scripts.
logger, current_log_file_path = setup_logger(
   script_name=log_file_base_name,
   log_directory_base=SCRIPT_DIR, # This is used if shared_log_file_path is None
   log_level=logging.INFO,
   shared_log_file_path=args.shared_log_file # Pass the parsed argument (will be None initially)
)


# --- Script Start ---
logger.info(f"--- Script '{script_name}' started ---") # Clear start message for separation
logger.info(f"Logger configured. All logs for this workflow will be saved to: {current_log_file_path}")
logger.info(f"Current working directory: {os.getcwd()}") # Log current working directory for context
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

   # This template string is needed by fetch_files in pytaps/fetchdata.py
   FILENAME_PATTERN_TEMPLATE = "*SP1*{date}000*"

   # Use generate_met_filename to get the fully formed pattern for filtering and logging
   FULL_FILE_PATTERN = generate_met_filename(current_date_obj)
   logger.info(f"Fetching files for date: {FILE_DATE_STR} with pattern: {FULL_FILE_PATTERN}")

   # --- Check if files exist on the FTP server ---
   logger.info("Checking if files exist on FTP server...")

   # Call list_remote_files, passing all connection details and the pattern
   matching_remote_files = list_remote_files(
       host=FTP_SERVER_HOST,
       username=FTP_USERNAME,
       password=FTP_PASSWORD,
       remote_dir=REMOTE_BASE_DIRECTORY,
       filename_pattern=FULL_FILE_PATTERN
   )

   if not matching_remote_files:
       logger.error(f"No matching ARPEGE files found on FTP server for date {FILE_DATE_STR} with pattern '{FULL_FILE_PATTERN}'. Exiting.")
       sys.exit(1) # Exit if no ARPEGE files are found, as per the request to remove Aladin fallback
   else:
       logger.info(f"Found {len(matching_remote_files)} matching files on FTP server:")
       for f in matching_remote_files:
           logger.info(f"  - {f}")

       # --- Prepare files for fetch_remote_files ---
       files_to_download = []
       for remote_filename in matching_remote_files:
           remote_full_path = os.path.join(REMOTE_BASE_DIRECTORY, remote_filename)
           local_full_path = os.path.join(TMP_DIR, remote_filename)
           files_to_download.append({
               'remote_path': remote_full_path,
               'local_path': Path(local_full_path) # Ensure local_path is a Path object
           })

       # --- FTP File Transfer using fetch_remote_files ---
       logger.info("Proceeding with FTP download using fetch_remote_files.")
       logger.info(f"Attempting to download {len(files_to_download)} files to {TMP_DIR}.")

       fetch_remote_files(
           protocol='ftp', # Specify the protocol (can be 'sftp' if needed)
           host=FTP_SERVER_HOST,
           port=None, # Let the function use the default FTP port (21)
           username=FTP_USERNAME,
           password=FTP_PASSWORD,
           files_to_process=files_to_download,
           logger_instance=logger # Pass the logger instance for detailed logging within pytaps
       )
       logger.info(f"FTP transfer process initiated by fetch_remote_files completed.")


       # Optional: Verify if files were actually downloaded to TMP_DIR
       downloaded_files_count = 0
       if os.path.exists(TMP_DIR):
           for filename in os.listdir(TMP_DIR):
               # Check if the downloaded file matches any of the remote files we expected to download
               if fnmatch.fnmatch(filename, FULL_FILE_PATTERN):
                   downloaded_files_count += 1

       if downloaded_files_count == 0:
           logger.error(f"ERROR: No files were found in '{TMP_DIR}' after FTP download, despite being listed on FTP.")
           sys.exit(1)
       else:
           logger.info(f"Successfully verified {downloaded_files_count} files downloaded to '{TMP_DIR}'.")

   # --- Run Next Program ---
   logger.info(f"Attempting to run next program: 2-conv.py")
   try:
       # Pass the shared log file path to the next script
       execute_command(
           [sys.executable, os.path.join(SCRIPT_DIR, "2-conv.py"), "--shared-log-file", current_log_file_path],
           cwd=SCRIPT_DIR # Ensure the working directory is correct for the next script
       )
       logger.info("Successfully executed 2-conv.py.")
   except (subprocess.CalledProcessError, FileNotFoundError) as e:
       logger.exception(f"An error occurred while running 2-conv.py: {e}")
       sys.exit(1)

except Exception as e:
   logger.exception(f"An unexpected error occurred in the main script flow: {e}")
   sys.exit(1)

logger.info(f"--- Script '{script_name}' finished. ---") # Clear end message
