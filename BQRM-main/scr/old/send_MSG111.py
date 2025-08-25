########################################################################
#   Send Messages using SMTP protocol                                  #
#                                                                      #
#   This script is used to send files to email adresses                #
#                                                                      #
#   AUTHOR:                                                            #
#   - Issam LAGHA (Original)                                           #
#   - Refactored by AI (for PyTAP, logging, and shared log)            #
#                                                                      #
#   LAST MODIFICATION:                                                 #
#   - Date: 02nd April 2024 (Original)                                 #
#   - Date: August 17th 2025 (Refactored)                              #
#                                                                      #
########################################################################

import os
import sys
from pathlib import Path
import logging
import argparse # Import argparse for robust argument parsing

# Import PyTAP utilities
from pytaps.logging_utils import setup_logger
from pytaps.email_utils import send_email
from pytaps.date_utils import get_ymd_for_today_and_yesterday
from pytaps.file_operations import check_file_exists_and_log

# --- Configuration (can be moved to a config file or env vars for production) ---
SCRIPT_NAME = Path(__file__).stem # Gets the script name without extension
LOG_DIRECTORY_BASE = Path(__file__).parent # Log files will be in the same directory as the script
LOG_LEVEL = logging.DEBUG # <--- CHANGE THIS LINE (e.g., logging.INFO, logging.WARNING)

SENDER_EMAIL = "pnt@meteo.dz"
RECEIVER_EMAILS = ['aoumeurmohamed2404@gmail.com'] # Uncommented and moved to config
EMAIL_PASSWORD = "Prev-052025" # Original password from the script
SMTP_SERVER = "smtp.meteo.dz"
SMTP_PORT = 587

# Define the folder where BQRM documents are expected, relative to the script
# Based on your original path: f'{PWD}/../BQRM_{AA}{MM}{DD}0600.docx'
# This implies BQRM docs are in a sibling directory named 'BQRM' relative to where the script's parent folder is.
# Let's assume the script is in 'scripts/send_messages.py' and BQRM docs are in 'BQRM/'.
# So, if script is in 'project/scripts/', BQRM docs are in 'project/BQRM/'
BQRM_DOCS_FOLDER_NAME = './home/aoumeur/bqrm/BQRM-main' # Adjust this path if your BQRM folder is elsewhere

# Pattern for the BQRM document filename
BQRM_DOCX_PATTERN = 'BQRM_{}{}{}0600.docx'
# ---------------------------------------------------------------------------------

def main():
    """
    Main function to prepare and send the BQRM bulletin email.
    """
    # --- Argument Parsing for shared log file ---
    parser = argparse.ArgumentParser(description="Send BQRM Bulletin Email.")
    parser.add_argument('--shared-log-file', type=str,
                        help='Path to a shared log file for centralized logging.')
    args = parser.parse_args()
    # --------------------------------------------

    # Setup logging for the main script
    # Use the shared_log_file if provided, otherwise default behavior of setup_logger
    logger, log_file_path = setup_logger(
        script_name=SCRIPT_NAME,
        log_directory_base=LOG_DIRECTORY_BASE,
        log_level=LOG_LEVEL,
        shared_log_file_path=args.shared_log_file # <--- Pass the parsed argument here!
    )
    logger.info(f"Logger initialized for {SCRIPT_NAME}. Log file: {log_file_path}")
    logger.info("Starting BQRM bulletin sending script.")

    # Prepare dates using PyTAP utility (replaces os.environ.get for AA, MM, DD)
    AA_today, MM_today, DD_today, _, _, _ = \
        get_ymd_for_today_and_yesterday(logger_instance=logger)
    logger.debug(f"Today's date components: Year={AA_today}, Month={MM_today}, Day={DD_today}")

    # Determine base path for documents (relative to script location)
    base_data_path = Path(__file__).parent # This gets the directory where the script is located
    bqrm_folder_path = base_data_path / BQRM_DOCS_FOLDER_NAME
    logger.debug(f"BQRM documents path determined as: {bqrm_folder_path}")

    # Construct the expected BQRM document path
    bqrm_docx_file = bqrm_folder_path / BQRM_DOCX_PATTERN.format(AA_today, MM_today, DD_today)
    logger.info(f"Expected BQRM document file path: {bqrm_docx_file}")

    # Email details (now using the date variables from PyTAP)
    subject = f'BQRM du {DD_today}/{MM_today}/{AA_today}'
    body = f"Bonjour,\nVoici le bulletin quotidien des renseignements météorologiques de l'Algérie du {DD_today}/{MM_today}/{AA_today}\nNB: Vueillez remplir les cases vides des stations.\nCordialement"

    # Check if the BQRM file exists before attempting to send
    if check_file_exists_and_log(bqrm_docx_file, logger_instance=logger):
        logger.info(f"Attempting to send email with BQRM document: {bqrm_docx_file}")
        email_sent_successfully = send_email(
            sender_email=SENDER_EMAIL,
            receiver_emails=RECEIVER_EMAILS,
            subject=subject,
            body=body,
            password=EMAIL_PASSWORD,
            smtp_server=SMTP_SERVER,
            smtp_port=SMTP_PORT,
            attachments=[bqrm_docx_file], # Pass the Path object directly
            logger_instance=logger # Pass the logger instance for PyTAP's internal logging
        )
        if email_sent_successfully:
            logger.info("BQRM email process completed successfully.")
        else:
            logger.error("Failed to send BQRM email.")
    else:
        logger.critical(f"BQRM document file '{bqrm_docx_file}' not found. Email not sent.")
        # Optionally, send an email notifying about the missing file if critical
        # send_email(SENDER_EMAIL, RECEIVER_EMAILS, f"ALERT: BQRM File Missing for {DD_today}/{MM_today}/{AA_today}",
        #            f"The BQRM document '{bqrm_docx_file}' was not found. Email not sent.",
        #            EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT, logger_instance=logger)

    logger.info("Script execution finished.")

if __name__ == "__main__":
    main()
