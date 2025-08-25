import os
import sys
from pathlib import Path
import logging
import argparse
from datetime import datetime, timedelta # Keep for reference if needed, though pytaps handles most date needs

# Import PyTAP utilities
# Make sure you have PyTAP installed: pip install pytaps
try:
    from pytaps.logging_utils import setup_logger
    from pytaps.email_utils import send_email
    from pytaps.date_time_utils import get_ymd_for_today_and_yesterday
    from pytaps.file_operations import check_file_exists_and_log, clean_directory # <--- ADDED clean_directory
except ImportError:
    print("Error: PyTAP library not found. Please install it using 'pip install pytaps'.")
    sys.exit(1)

# --- Configuration ---
# SCRIPT_NAME: Automatically gets the script's name without extension
SCRIPT_NAME = Path(__file__).stem

# LOG_DIRECTORY_BASE: Where log files will be stored.
# This creates a 'logs' subdirectory in the same directory as the script.
# You can change this to an absolute path like Path("/var/log/my_app") if preferred.
LOG_DIRECTORY_BASE = Path(__file__).parent / "logs"

# LOG_LEVEL: Set the minimum level of messages to log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = logging.INFO # INFO is a good default for operational scripts

# Email details
SENDER_EMAIL = "pnt@meteo.dz"
RECEIVER_EMAILS = ['aoumeurmohamed2404@gmail.com'] # List of recipient emails
EMAIL_PASSWORD = "Prev-052025" # Your email password
SMTP_SERVER = "smtp.meteo.dz"
SMTP_PORT = 587

# Define the base directory where your attachment files are located.
# The original script used `os.chdir(os.path.dirname(os.getcwd()))` and then looked for 'bulletins'.
# This implies the 'bulletins' folder is one level up from where the script is run,
# assuming the script is in a subdirectory (e.g., 'scripts').
# Example: If script is in 'my_project/scripts/send_email.py' and 'bulletins' is in 'my_project/bulletins',
# then DATA_FILES_BASE_PATH should point to 'my_project'.
# Path(__file__).resolve().parent.parent gets the parent of the script's directory.
DATA_FILES_BASE_PATH = Path(__file__).resolve().parent.parent

# Define the subfolder within DATA_FILES_BASE_PATH where the bulletins are located
BULLETINS_SUBFOLDER = "bulletins"
TMP_FOLDER_NAME = '../tmp'

# --- End Configuration ---

def main():
    """
    Main function to prepare and send the daily weather bulletin email.
    """
    # --- Argument Parsing for shared log file ---
    # This allows you to specify a shared log file when running the script, e.g.:
    # python your_script_name.py --shared-log-file /var/log/my_app/shared.log
    parser = argparse.ArgumentParser(description="Send Daily Weather Bulletin Email.")
    parser.add_argument('--shared-log-file', type=str,
                        help='Path to a shared log file for centralized logging.')
    args = parser.parse_args()
    # --------------------------------------------

    # Setup logging for the main script using PyTAP's setup_logger
    # This will create a dedicated log file for this script and can also write to a shared log.
    logger, log_file_path = setup_logger(
        script_name=SCRIPT_NAME,
        log_directory_base=LOG_DIRECTORY_BASE,
        log_level=LOG_LEVEL,
        shared_log_file_path=args.shared_log_file # Pass the parsed argument here
    )
    logger.info(f"Logger initialized for {SCRIPT_NAME}. Log file: {log_file_path}")
    logger.info("Starting daily antiacridienne bulletin sending script.")

    # Prepare dates using PyTAP utility
    # get_ymd_for_today_and_yesterday returns today's and yesterday's year, month, day.
    # We only need today's for this script.
    AA_today, MM_today, DD_today, _, _, _ = \
        get_ymd_for_today_and_yesterday(logger_instance=logger)
    logger.debug(f"Today's date components: Year={AA_today}, Month={MM_today}, Day={DD_today}")

    # Construct the full path for the attachment file
    bulletin_filename = f"Bulletin_antiacridienne_{DD_today}-{MM_today}-{AA_today}.docx"
    
    # Combine base path, subfolder, and filename to get the absolute path to the bulletin
    full_bulletin_path = DATA_FILES_BASE_PATH / BULLETINS_SUBFOLDER / bulletin_filename
    tmp_folder_path = DATA_FILES_BASE_PATH / TMP_FOLDER_NAME

    attachment_file_paths = []
    # Use PyTAP's check_file_exists_and_log to verify the file
    if check_file_exists_and_log(full_bulletin_path, logger_instance=logger):
        attachment_file_paths.append(full_bulletin_path)
        logger.info(f"File found and added for attachment: {full_bulletin_path}")
    else:
        logger.critical(f"Required bulletin file not found: {full_bulletin_path}. Aborting email sending.")
        sys.exit(1) # Exit the script if the main attachment is missing

    # Email details (using the date variables from PyTAP)
    subject = f"Tableau de Températures antiacridienne du {DD_today}/{MM_today}/{AA_today}" # Based on original body content
    body = (
        f"Bonjour,\n"
        f"Veuillez trouver ci-Joint le Tableau de Températures automatisé de antiacridienne pour la journée du {DD_today}/{MM_today}/{AA_today}\n"
        f"Cordialement, \n"
        f"(Cet émail a été généré automatiquement avec python3)"
    )

    logger.info(f"Attempting to send email with subject: '{subject}' to {', '.join(map(str, RECEIVER_EMAILS))}")

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
        sys.exit(1) # Indicate failure with exit code

 # --- Add cleanup for tmp folder ---
    try:
        logger.info(f"Attempting to clean up temporary directory: {tmp_folder_path}")
        # Clean all files in the tmp folder
        deleted_files = clean_directory(
            directory_path=tmp_folder_path,
            file_pattern=None, # Clean all files (or specify a pattern like '*.grib2' if you only want to delete grib files)
            ignore_errors=True, # Continue even if some files fail to delete
            logger_instance=logger
        )
        if deleted_files:
            logger.info(f"Successfully cleaned {len(deleted_files)} files from {tmp_folder_path}.")
        else:
            logger.info(f"No files found to clean in {tmp_folder_path} or all files were already gone.")
    except Exception as e:
        logger.error(f"An error occurred during temporary directory cleanup: {e}", exc_info=True)


    logger.info("Script execution finished.")

if __name__ == "__main__":
    main()