#!/usr/bin/env python3

import os
import datetime
import shutil # Still needed for shutil.copy2 as pytaps doesn't have a direct wrapper for single file copy yet
import sys
from pathlib import Path
import logging # Import logging for direct use with log_level

# Import functions from your PyTAP package
from pytaps.logging_utils import setup_logger
from pytaps.system_utils import execute_command
from pytaps.fetchdata import fetch_files # Imported as requested, but not used in this script's current logic.
from pytaps.file_operations import (
    build_time_series_filepath, # Not used in this specific script, but useful for other date-based file paths
    check_file_exists_and_log,
    move_files_by_pattern,
    delete_files, # For deleting specific files
    clean_directory, # For cleaning files by pattern within a directory
    copy_directory_recursive, # New function to copy directories recursively
    ensure_parent_directory_exists # Useful for ensuring a file's parent directory exists
)
original_cwd = os.getcwd() 
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # Get the directory of the current script
LOCAL_DIRECTORY = SCRIPT_DIR # Use SCRIPT_DIR for consistency

    # --- Logging Setup ---
log_file_base_name = "BQCP24h18"
logger = None # Initialize logger to None for error handling
shared_LOCAL_DIRECTORY_for_children = None # To store the path to pass to sub-scripts

try:
        # This call sets up the primary log file for the main script.
        # It will create the 'logs' directory and the 'BQCP24h.log' file within LOCAL_DIRECTORY.
        logger, shared_LOCAL_DIRECTORY_for_children = setup_logger(
            script_name=log_file_base_name,
            log_directory_base=LOCAL_DIRECTORY, # This tells pytaps where to put the 'logs' folder
            log_level=logging.INFO,
            shared_LOCAL_DIRECTORY=None # This is the first script, so no shared path yet
        )
        
        # CRITICAL CHECK: Ensure the shared log file path was successfully obtained
        if not shared_LOCAL_DIRECTORY_for_children:
            # If setup_logger returns None or an empty path, it's a problem with pytaps itself.
            raise RuntimeError("pytaps.logging_utils.setup_logger did not return a valid shared log file path.")
except Exception as e:
        # Fallback if logging setup fails
        print(f"CRITICAL ERROR: Failed to set up main logger. Using console fallback. Error: {e}", file=sys.stderr)
        logger = logging.getLogger("FallbackLogger")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.error("Initial logger setup failed, using fallback console logger.")

logger.info("Script started.")
logger.info(f"Log file: {LOCAL_DIRECTORY}")

# --- Set Date Variables ---
AA = datetime.datetime.now().strftime('%Y')
MM = datetime.datetime.now().strftime('%m')
DD = datetime.datetime.now().strftime('%d')

# Uncomment these lines to use fixed dates for testing, similar to bash script's commented lines:
# AA = "2025"
# MM = "07"
# DD = "16"

logger.info(f"Date variables set: AA={AA}, MM={MM}, DD={DD}")
logger.info(f"Script's current working directory: PWD={LOCAL_DIRECTORY}")

# --- Define Directories and Paths ---
# Assuming BUFR_INPUT_ROOT and TAC_INPUT are relative to the project's root directory
# and LOCAL_DIRECTORY is where this script is executed (e.g., PyTAP-main/src/pytaps)
# Adjust `parent.parent.parent` if your actual project structure differs.
PROJECT_ROOT = LOCAL_DIRECTORY.parent.parent.parent # Adjust based on where your script runs relative to the 'pytap' root
BUFR_INPUT_ROOT = PROJECT_ROOT / "bufr_data" / "observations"
TAC_INPUT = PROJECT_ROOT / "bqrm_data" / "observations"

# Local directories for processing
BUFR_TARGET_DIR = LOCAL_DIRECTORY / "Synop"
TXT_TARGET_BASE_DIR = LOCAL_DIRECTORY / "txt"
CLIMXLSX_DIR = LOCAL_DIRECTORY / "Climxlsx"
BACKUP_BASE_DIR = LOCAL_DIRECTORY / "Backup"

logger.info(f"LOCAL_DIRECTORY set to: {LOCAL_DIRECTORY}")
logger.info(f"BUFR_INPUT_ROOT set to: {BUFR_INPUT_ROOT}")
logger.info(f"TAC_INPUT set to: {TAC_INPUT}")

# --- Copy BUFR File ---
# This acts as the "download" step in the current active script logic.
# The original script performs a local file copy, not an FTP fetch.
# If FTP fetching were needed, pytaps.fetchdata.fetch_files would be used here.
bufr_source_path = BUFR_INPUT_ROOT / AA / MM / DD / f"Synop_{AA}{MM}{DD}0600.bufr"
bufr_target_path = BUFR_TARGET_DIR / f"Synop_{AA}{MM}{DD}0600.bufr"

logger.info(f"Attempting to copy BUFR file from {bufr_source_path} to {BUFR_TARGET_DIR}/")

BUFR_COPY_SUCCESS = False
try:
   # Use pytaps.file_operations.ensure_parent_directory_exists
   ensure_parent_directory_exists(bufr_target_path, logger_instance=logger)
   logger.info(f"Directory {BUFR_TARGET_DIR} created/exists.")
except OSError as e:
   logger.critical(f"ERROR: Failed to create directory {BUFR_TARGET_DIR}. Error: {e}. Exiting.")
   sys.exit(1)

# Check if source file exists using pytaps.file_operations.check_file_exists_and_log
if check_file_exists_and_log(bufr_source_path, logger_instance=logger):
    try:
        shutil.copy2(bufr_source_path, bufr_target_path) # shutil.copy2 is still used for direct file copy
        logger.info(f"BUFR file {bufr_source_path.name} copied successfully to {bufr_target_path}.")
        BUFR_COPY_SUCCESS = True
    except Exception as e:
        logger.error(f"ERROR: Failed to copy BUFR file {bufr_source_path.name}. Error: {e}")
else:
    logger.error(f"Skipping BUFR copy as source file not found: {bufr_source_path}.")


# --- Execute Python Script ---
if BUFR_COPY_SUCCESS:
    logger.info("Proceeding with Python script execution as BUFR file copy was successful.")
    python_script_name = "Synop24h18.py"
    logger.info(f"Executing python3 {python_script_name}...")
    try:
        # Use pytaps.system_utils.execute_command
        # Pass LOCAL_DIRECTORY as cwd to ensure the script runs in the correct context
        result = execute_command(
            ["python3", python_script_name],
            cwd=str(LOCAL_DIRECTORY), # execute_command expects string path for cwd
            check=True,
            capture_output=True,
            text=True,
            logger_instance=logger # Pass logger for detailed command output logging
        )
        logger.info(f"Python script {python_script_name} executed successfully.")
    except Exception as e: # execute_command re-raises specific errors, so a general catch is fine here
        logger.error(f"An error occurred during {python_script_name} execution: {e}")
else:
    logger.warning("Skipping Python script execution due to previous BUFR file copy failure.")

# --- File Operations: Cleanup and Moving ---

# Remove old agricole.xlsx from templates directory
agricole_template_dir = LOCAL_DIRECTORY / "templates"
agricole_old_path_in_templates = agricole_template_dir / "agricole.xlsx"

if agricole_old_path_in_templates.exists():
    logger.info(f"Attempting to remove existing {agricole_old_path_in_templates}.")
    # Use pytaps.file_operations.delete_files for targeted file deletion
    delete_files([agricole_old_path_in_templates], ignore_errors=True, logger_instance=logger)
    if not agricole_old_path_in_templates.exists():
        logger.info(f"Successfully removed {agricole_old_path_in_templates}.")
    else:
        logger.warning(f"Failed to remove {agricole_old_path_in_templates} despite attempt.")
else:
    logger.info(f"agricole.xlsx not found in {agricole_template_dir}. Skipping removal.")

# Move newly generated agricole.xlsx from current directory
agricole_new_name = f"agricole_{MM}{DD}0600.xlsx"
agricole_new_path_in_cwd = LOCAL_DIRECTORY / agricole_new_name
agricole_final_path = LOCAL_DIRECTORY / "templates" / "agricole.xlsx"

logger.info(f"Moving {agricole_new_path_in_cwd} to {agricole_final_path}.")
try:
    # Ensure target directory exists for the move using pytaps.file_operations.ensure_parent_directory_exists
    ensure_parent_directory_exists(agricole_final_path, logger_instance=logger)
    agricole_new_path_in_cwd.rename(agricole_final_path) # Use Path.rename for single file move
    logger.info(f"Moved {agricole_new_name} successfully.")
except FileNotFoundError:
    logger.error(f"ERROR: Source file {agricole_new_name} not found in {LOCAL_DIRECTORY}. Cannot move.")
except Exception as e:
    logger.error(f"ERROR: Failed to move {agricole_new_name}. Error: {e}")

# Create directory for text files and move them
txt_target_dir = TXT_TARGET_BASE_DIR / AA / MM
logger.info(f"Creating directory {txt_target_dir} if it doesn't exist.")
try:
   txt_target_dir.mkdir(parents=True, exist_ok=True)
   logger.info(f"Directory {txt_target_dir} created/exists.")
except OSError as e:
   logger.critical(f"ERROR: Failed to create directory {txt_target_dir}. Error: {e}")

logger.info(f"Moving all *.txt files from {LOCAL_DIRECTORY} to {txt_target_dir}.")
# Use pytaps.file_operations.move_files_by_pattern
moved_txt_files = move_files_by_pattern(
    source_dir=LOCAL_DIRECTORY,
    filename_pattern="*.txt",
    destination_dir=txt_target_dir,
    logger_instance=logger
)
if not moved_txt_files:
   logger.warning("No *.txt files found to move.")
else:
   logger.info(f"Finished moving {len(moved_txt_files)} *.txt files.")


# Remove remaining .xlsx and .docx files in LOCAL_DIRECTORY
logger.info(f"Removing all *.xlsx files in {LOCAL_DIRECTORY}.")
# Use pytaps.file_operations.clean_directory
cleaned_xlsx_local = clean_directory(
    directory_path=LOCAL_DIRECTORY,
    file_pattern="*.xlsx",
    ignore_errors=True,
    logger_instance=logger
)
if not cleaned_xlsx_local:
   logger.info(f"No *.xlsx files found in {LOCAL_DIRECTORY} to remove.")

logger.info(f"Removing all *.docx files in {LOCAL_DIRECTORY}.")
cleaned_docx_local = clean_directory(
    directory_path=LOCAL_DIRECTORY,
    file_pattern="*.docx",
    ignore_errors=True,
    logger_instance=logger
)
if not cleaned_docx_local:
   logger.info(f"No *.docx files found in {LOCAL_DIRECTORY} to remove.")


# Remove .xlsx files from Climxlsx directory
logger.info(f"Removing all *.xlsx files in {CLIMXLSX_DIR}.")
cleaned_xlsx_clim = clean_directory(
    directory_path=CLIMXLSX_DIR,
    file_pattern="*.xlsx",
    ignore_errors=True,
    logger_instance=logger
)
if not cleaned_xlsx_clim:
   logger.info(f"No *.xlsx files found in {CLIMXLSX_DIR} to remove.")

# Create backup directories
backup_daily_dir = BACKUP_BASE_DIR / AA / MM / DD

logger.info(f"Creating backup directories: {backup_daily_dir}.")
try:
   backup_daily_dir.mkdir(parents=True, exist_ok=True)
   logger.info("Backup directories created/exist.")
except OSError as e:
   logger.critical(f"ERROR: Failed to create one or more backup directories. Error: {e}")

# Copy SMAL* files to backup using pytaps.file_operations.copy_directory_recursive
smal_source_dir = TAC_INPUT / AA / MM / DD
final_smal_copy_dest = backup_daily_dir # This is where the DD directory will be copied to

logger.info(f"Copying contents from {smal_source_dir} to {final_smal_copy_dest}.")
copied_smal_dir = copy_directory_recursive(
    source_dir=smal_source_dir,
    destination_dir=final_smal_copy_dest,
    overwrite_existing=True, # Mimics 'cp -r' behavior, which overwrites if destination exists
    ignore_errors=False, # Set to False to re-raise errors, consistent with critical operations
    logger_instance=logger
)
if copied_smal_dir:
    logger.info(f"Successfully backed up SMAL* files to {copied_smal_dir}.")
else:
    logger.error(f"Failed to copy SMAL* files to backup. Check logs for details.")


logger.info("Script finished.")

