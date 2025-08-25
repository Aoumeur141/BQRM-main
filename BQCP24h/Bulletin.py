import os
import sys
import datetime
import shutil
import logging

# Import functions from your pytaps package
from pytaps.logging_utils import setup_logger
from pytaps.system_utils import execute_command
from pytaps.fetchdata import fetch_remote_files
from pytaps.file_operations import (
    build_time_series_filepath,
    check_file_exists_and_log,
    move_files_by_pattern,
    clean_directory,
    copy_directory_recursive
)

# --- Main Script Logic ---
def main():
    # Store original CWD at the very beginning for general script operations
    original_cwd = os.getcwd() 

    # --- Variable Definitions ---
    today = datetime.date.today()
    AA = today.strftime("%Y")
    MM = today.strftime("%m")
    DD = today.strftime("%d")
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # Get the directory of the current script
    LOCAL_DIRECTORY = SCRIPT_DIR # Use SCRIPT_DIR for consistency

    # --- Logging Setup ---
    log_file_base_name = "BQCP24h"
    logger = None # Initialize logger to None for error handling
    shared_log_file_path_for_children = None # To store the path to pass to sub-scripts

    try:
        # This call sets up the primary log file for the main script.
        # It will create the 'logs' directory and the 'BQCP24h.log' file within LOCAL_DIRECTORY.
        logger, shared_log_file_path_for_children = setup_logger(
            script_name=log_file_base_name,
            log_directory_base=LOCAL_DIRECTORY, # This tells pytaps where to put the 'logs' folder
            log_level=logging.INFO,
            shared_log_file_path=None # This is the first script, so no shared path yet
        )
        
        # CRITICAL CHECK: Ensure the shared log file path was successfully obtained
        if not shared_log_file_path_for_children:
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
    
    logger.info("Script started: Bufr and Arpege Data Retrieval and Processing.")
    # The log file path is now correctly stored in shared_log_file_path_for_children
    logger.info(f"All logs will be written to: {shared_log_file_path_for_children}")

    # --- NEW: Set the shared log file path as an environment variable ---
    # This is the key change for passing the log path to child processes
    os.environ['PYTAPS_SHARED_LOG_FILE'] = shared_log_file_path_for_children
    logger.info(f"Set environment variable PYTAPS_SHARED_LOG_FILE to: {os.environ['PYTAPS_SHARED_LOG_FILE']}")
    # --- END NEW BLOCK ---

    # --- Rest of Variable Definitions ---
    logger.info(f"Current Year (AA): {AA}")
    logger.info(f"Current Month (MM): {MM}")
    logger.info(f"Current Day (DD): {DD}")
    logger.info(f"Script Directory (SCRIPT_DIR): {SCRIPT_DIR}")

    BUFR_INPUT_ROOT = "bufr_data/observations"
    TAC_INPUT = "bqrm_data/observations"

    # FTP Server Information
    FTP_SERVER = "10.16.80.222"
    FTP_USERNAME = "admin"
    FTP_PASSWORD = "pluie_ims_data"
    REMOTE_DIRECTORY = "/"
    # LOCAL_DIRECTORY is already defined above

    logger.info(f"BUFR Input Root: {BUFR_INPUT_ROOT}")
    logger.info(f"TAC Input Root: {TAC_INPUT}")
    logger.info(f"FTP Server: {FTP_SERVER}")
    logger.info(f"Local Directory for downloads: {LOCAL_DIRECTORY}")

    # --- FTP Connection and File Download ---
    ftp_download_successful = False
    bufr_copy_successful = False

    csv_filename = f"exported_data_{AA}-{MM}-{DD}.csv"
    csv_local_download_dir = LOCAL_DIRECTORY # fetch_files downloads to this directory
    csv_local_path = os.path.join(csv_local_download_dir, csv_filename)
    csv_dest_dir = os.path.join(LOCAL_DIRECTORY, "Clim")
    csv_dest_path = os.path.join(csv_dest_dir, csv_filename)

    logger.info(f"Attempting to connect to FTP server {FTP_SERVER} and download {csv_filename}.")

  # 1. Prepare the files_to_process list as expected by fetch_remote_files
    files_to_download = [
        {
            'remote_path': os.path.join(REMOTE_DIRECTORY, csv_filename),
            'local_path': csv_local_path
        }
    ]

    try:
        # 2. Call fetch_remote_files with the correct arguments
        fetch_remote_files(
            protocol="ftp", # Specify the protocol (e.g., "ftp" or "sftp")
            host=FTP_SERVER,
            port=None, # Use default FTP port (21). Can be specified if needed.
            username=FTP_USERNAME,
            password=FTP_PASSWORD,
            files_to_process=files_to_download, # Pass the prepared list
            logger_instance=logger # Pass the logger instance for detailed logging
        )
        
        # check_file_exists_and_log *does* accept logger_instance, keep it.
        if check_file_exists_and_log(csv_local_path, logger_instance=logger):
            ftp_download_successful = True
            logger.info(f"FTP download of {csv_filename} successful.")
            
            # Move the downloaded file to the Clim directory
            os.makedirs(csv_dest_dir, exist_ok=True) # Ensure destination directory exists
            shutil.move(csv_local_path, csv_dest_path)
            logger.info(f"Moved {csv_filename} to {csv_dest_dir}.")
        else:
            logger.error(f"FTP download of {csv_filename} failed: File not found after fetch attempt.")
            ftp_download_successful = False

    except Exception as e:
        logger.error(f"An error occurred during FTP operations: {e}", exc_info=True)
        ftp_download_successful = False

    # --- BUFR File Copy ---
    # Construct the BUFR source path using pytaps.file_operations.build_time_series_filepath
    bufr_source_path = build_time_series_filepath(
        base_dir=os.path.abspath(os.path.join(SCRIPT_DIR, "..", BUFR_INPUT_ROOT)),
        year=AA, month=MM, day=DD, hour=6, # Assuming 0600 is fixed
        filename_prefix="Synop_", filename_suffix=".bufr"
    )
    bufr_dest_path = os.path.join(LOCAL_DIRECTORY, "Synop")
    bufr_dest_file = os.path.join(bufr_dest_path, os.path.basename(bufr_source_path))

    logger.info(f"Attempting to copy BUFR Synop file from {bufr_source_path} to {bufr_dest_path}.")

    try:
        os.makedirs(bufr_dest_path, exist_ok=True)
        # check_file_exists_and_log *does* accept logger_instance, keep it.
        if check_file_exists_and_log(bufr_source_path, logger_instance=logger):
            shutil.copy2(bufr_source_path, bufr_dest_file)
            logger.info("BUFR Synop file copy successful.")
            bufr_copy_successful = True
        else:
            logger.error(f"BUFR Synop file not found at source: {bufr_source_path}. Skipping copy.")
            bufr_copy_successful = False
    except Exception as e:
        logger.error(f"Failed to copy BUFR Synop file. Error: {e}", exc_info=True)
        bufr_copy_successful = False

    # --- Python Script Execution based on previous operations ---
    # Store original CWD for this section to restore it afterwards
    script_execution_original_cwd = os.getcwd() 
    try:
        os.chdir(LOCAL_DIRECTORY)
        logger.info(f"Changed directory to {LOCAL_DIRECTORY} for Python script execution.")
    except OSError as e:
        logger.critical(f"Failed to change directory to {LOCAL_DIRECTORY}. Exiting. Error: {e}")
        sys.exit(1)

    if ftp_download_successful and bufr_copy_successful:
        logger.info("Both FTP download and BUFR file copy were successful. Proceeding with Python script execution.")
        
        python_scripts = ["csvtoxlsx.py", "Synop24h.py", "SynoClim.py","send_MSG.py"] # "send_MSG.py" if needed

        for script in python_scripts:
            logger.info(f"Executing python3 {script}...")
            try:
                # --- MODIFIED: Remove --shared-log-file argument ---
                command_to_execute = [
                    "python3", 
                    script,
                    AA, MM, DD, LOCAL_DIRECTORY # Pass common arguments
                ]
                
                # Use pytaps.system_utils.execute_command
                # The sub-scripts will now read the log file path from the environment.
                execute_command(command_to_execute, cwd=LOCAL_DIRECTORY)
                logger.info(f"{script} executed successfully.")
            except Exception as e:
                logger.error(f"Error executing {script}: {e}", exc_info=True)
    else:
        logger.error("Skipping Python script execution due to previous failures (FTP download or BUFR file copy).")

    # Restore CWD after script execution block
    if os.getcwd() != script_execution_original_cwd:
        try:
            os.chdir(script_execution_original_cwd)
            logger.info(f"Restored CWD after script execution to {script_execution_original_cwd}.")
        except OSError as e:
            logger.error(f"Failed to restore CWD after script execution. Error: {e}")

    # --- Post-Processing and Cleanup ---
    logger.info("Starting post-processing and cleanup operations.")

    # Move *.txt files using pytaps.file_operations.move_files_by_pattern
    txt_dest_dir = os.path.join(LOCAL_DIRECTORY, "txt", AA, MM)
    logger.info(f"Moving *.txt files to {txt_dest_dir}.")
    moved_txt_files = move_files_by_pattern(LOCAL_DIRECTORY, "*.txt", txt_dest_dir, logger_instance=logger)
    if not moved_txt_files:
        logger.info("No *.txt files found to move or all failed.")

    # Remove *.xlsx files from LOCAL_DIRECTORY using pytaps.file_operations.clean_directory
    #logger.info(f"Removing *.xlsx files from {LOCAL_DIRECTORY}.")
    #clean_directory(LOCAL_DIRECTORY, file_pattern="*.xlsx", logger_instance=logger)
## desactivet it because the script 18h need it 

    # Remove *.docx files from LOCAL_DIRECTORY using pytaps.file_operations.clean_directory
    logger.info(f"Removing *.docx files from {LOCAL_DIRECTORY}.")
    clean_directory(LOCAL_DIRECTORY, file_pattern="*.docx", logger_instance=logger)

    # Remove *.xlsx files from LOCAL_DIRECTORY/Climxlsx/ using pytaps.file_operations.clean_directory
    climxlsx_dir = os.path.join(LOCAL_DIRECTORY, "Climxlsx")
    logger.info(f"Removing *.xlsx files from {climxlsx_dir}.")
    clean_directory(climxlsx_dir, file_pattern="*.xlsx", logger_instance=logger)

    # Create backup directories
    backup_base_dir = os.path.join(LOCAL_DIRECTORY, "Backup", AA, MM)
    backup_daily_dir = os.path.join(backup_base_dir, DD)
    logger.info(f"Creating backup directories: {backup_base_dir} and {backup_daily_dir}.")
    try:
        os.makedirs(backup_base_dir, exist_ok=True)
        os.makedirs(backup_daily_dir, exist_ok=True)
        logger.info("Backup directories created successfully.")
    except OSError as e:
        logger.error(f"Failed to create one or more backup directories. Error: {e}")

    # Copy TAC_INPUT data to backup using the new pytaps.file_operations.copy_directory_recursive
    tac_source_dir = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../../", TAC_INPUT, AA, MM, DD))
    tac_dest_full_path = os.path.join(LOCAL_DIRECTORY, "Backup", AA, MM, DD) 

    logger.info(f"Copying SMAL* data from {tac_source_dir} to {tac_dest_full_path}.")
    try:
        copy_directory_recursive(
            source_dir=tac_source_dir,
            destination_dir=tac_dest_full_path, # Corrected parameter name and value
            overwrite_existing=True,
            logger_instance=logger
        )
        logger.info("TAC data copy to backup successful.")
    except (FileNotFoundError, NotADirectoryError) as e:
        logger.warning(f"Skipping TAC data copy to backup: {e}")
    except Exception as e:
        logger.error(f"Failed to copy TAC data to backup. Error: {e}", exc_info=True)

    logger.info("Script finished.")

    # Restore original working directory at the very end if it was changed
    if os.getcwd() != original_cwd:
        try:
            os.chdir(original_cwd)
            logger.info(f"Restored original working directory to {original_cwd}.")
        except OSError as e:
            logger.error(f"Failed to restore original working directory. Error: {e}")

    # --- NEW: Clean up the environment variable ---
    # It's good practice to remove environment variables when they are no longer needed
    if 'PYTAPS_SHARED_LOG_FILE' in os.environ:
        del os.environ['PYTAPS_SHARED_LOG_FILE']
        logger.info("Cleaned up PYTAPS_SHARED_LOG_FILE environment variable.")
    # --- END NEW BLOCK ---

if __name__ == "__main__":
    main()
