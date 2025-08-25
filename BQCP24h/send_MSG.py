import os
import sys
from pathlib import Path
import logging
import argparse # Keep this import if other args are added in future, or remove if no args are parsed

# Import PyTAP utilities
# Make sure you have PyTAP installed: pip install pytaps
try:
    from pytaps.logging_utils import setup_logger
    from pytaps.email_utils import send_email
    from pytaps.date_time_utils import get_ymd_for_today_and_yesterday
    from pytaps.file_operations import check_file_exists_and_log
except ImportError:
    print("Error: PyTAP library not found. Please install it using 'pip install pytaps'.")
    sys.exit(1)

# --- Configuration ---
# SCRIPT_NAME: Automatically gets the script's name without extension
SCRIPT_NAME = Path(__file__).stem

# LOG_DIRECTORY_BASE: Where log files will be stored.
# This creates a 'logs' subdirectory in the same directory as the script.

# LOG_LEVEL: Set the minimum level of messages to log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = logging.INFO # INFO is a good default for operational scripts

# Email details - these were hardcoded in your original script
SENDER_EMAIL = "pnt@meteo.dz"
RECEIVER_EMAILS = ['aoumeurmohamed2404@gmail.com'] # List of recipient emails
EMAIL_PASSWORD = "Prev-052025" # Your email password
SMTP_SERVER = "smtp.meteo.dz"
SMTP_PORT = 587

# Define the base directory where your attachment files are located.
# Your original code used `PWD = os.environ.get('PWD')`.
# `os.environ.get('PWD')` typically refers to the current working directory of the shell.
# Please choose the most appropriate option below based on your file structure:

# Option 1 (Recommended if files are in the directory where you run the script):
DATA_FILES_BASE_PATH = Path.cwd() 

# Option 2 (If files are in the same directory as this Python script):
# DATA_FILES_BASE_PATH = Path(__file__).parent

# Option 3 (If files are in a specific absolute path, e.g., '/home/user/my_data'):
# DATA_FILES_BASE_PATH = Path("/path/to/your/data/directory") 

# Option 4 (If PWD environment variable is reliably set to the data directory):
# PWD_ENV = os.environ.get('PWD')
# if PWD_ENV:
#     DATA_FILES_BASE_PATH = Path(PWD_ENV)
# else:
#     # Fallback if PWD env var is not set
#     print("Warning: PWD environment variable not set. Falling back to current working directory.")
#     DATA_FILES_BASE_PATH = Path.cwd()

# --- End Configuration ---

def main():
    """
    Main function to prepare and send the daily weather bulletin email.
    """
    # Get shared log file path from environment variable
    shared_log_file_from_env = os.environ.get('PYTAPS_SHARED_LOG_FILE')

    
    if shared_log_file_from_env:
        # This print is for debugging, you can remove it later
        print(f"DEBUG ({os.path.basename(__file__)}): Shared log file path from environment: {shared_log_file_from_env}", file=sys.stderr)
        logger_setup_message = f"Shared log file path from environment: {shared_log_file_from_env}"
    else:
        # Fallback if the environment variable isn't set (e.g., if you run this script directly)
        print(f"WARNING ({os.path.basename(__file__)}): PYTAPS_SHARED_LOG_FILE environment variable not set. This script will create its own log file.", file=sys.stderr)
        logger_setup_message = "PYTAPS_SHARED_LOG_FILE environment variable not set. This script will create its own log file."
    # --- END NEW BLOCK ---

    # Setup logging for the main script using PyTAP's setup_logger
    logger, log_file_path = setup_logger(
        script_name=SCRIPT_NAME,
        log_directory_base=os.path.dirname(os.path.abspath(__file__)),
        log_level=LOG_LEVEL,
        shared_log_file_path=shared_log_file_from_env # Use the path from the environment variable
    )
    logger.info(logger_setup_message) # Log the message about source of log path
    logger.info(f"Logger initialized for {SCRIPT_NAME}. Log file: {log_file_path}")
    logger.info("Starting daily weather bulletin sending script.")

    # Prepare dates using PyTAP utility (replaces os.environ.get for AA, MM, DD)
    # get_ymd_for_today_and_yesterday returns today's and yesterday's year, month, day.
    # We only need today's for this script.
    AA_today, MM_today, DD_today, _, _, _ = \
        get_ymd_for_today_and_yesterday(logger_instance=logger)
    logger.debug(f"Today's date components: Year={AA_today}, Month={MM_today}, Day={DD_today}")

    # Construct the full paths for the attachment files
    # The original filenames were like 'Cumul_table{MM}{DD}0600.docx'
    cumul_table_filename = f'Cumul_table{MM_today}{DD_today}0600.docx'
    synopclim_precip_table_filename = f'SynopClim_precip_table{MM_today}{DD_today}0600.docx'

    # List of expected files to check and potentially attach
    expected_files = [
        DATA_FILES_BASE_PATH / cumul_table_filename,
        DATA_FILES_BASE_PATH / synopclim_precip_table_filename,
        # Add other file paths here if needed, e.g.:
        # DATA_FILES_BASE_PATH / f'AnotherReport_{AA_today}{MM_today}{DD_today}.pdf',
    ]

    attachment_file_paths = []
    for file_path in expected_files:
        # Use PyTAP's check_file_exists_and_log to verify each file
        if check_file_exists_and_log(file_path, logger_instance=logger):
            attachment_file_paths.append(file_path)
            logger.info(f"File found and added for attachment: {file_path}")
        else:
            logger.warning(f"File not found, will not be attached: {file_path}")

    if not attachment_file_paths:
        logger.critical("No attachment files were found. Aborting email sending.")
        sys.exit(1) # Exit the script if there are no files to send

    # Email details (now using the date variables from PyTAP)
    subject = f'Bulletin du {DD_today}/{MM_today}/{AA_today}'
    body = (
        f"Bonjour,\n"
        f"Voici le bulletin quotidien des Cumuls de pluie enregistrés du {DD_today}/{MM_today}/{AA_today}\n"
        f"NB: Vueillez remplir les cases vides des stations.\n"
        f"Cordialement"
    )

    logger.info(f"Attempting to send email with subject: '{subject}' to {', '.join(RECEIVER_EMAILS)}")

    # Use PyTAP's send_email function
    email_sent_successfully = send_email(
        sender_email=SENDER_EMAIL,
        receiver_emails=RECEIVER_EMAILS,
        subject=subject,
        body=body,
        password=EMAIL_PASSWORD,
        smtp_server=SMTP_SERVER,
        smtp_port=SMTP_PORT,
        attachments=attachment_file_paths, # Pass the list of Path objects directly
        logger_instance=logger # Pass the logger instance for PyTAP's internal logging
    )

    if email_sent_successfully:
        logger.info("Email process completed successfully.")
    else:
        logger.error("Failed to send email.")

    logger.info("Script execution finished.")

if __name__ == "__main__":
    # If this script is run directly, it won't have the env var set by the main script.
    # The setup_logger will then create its own log. This is expected fallback behavior.
    main()
