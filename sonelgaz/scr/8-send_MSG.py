# Inside 8-send_MSG.py (or whatever your main script for sending is)

import os
import sys
from pathlib import Path
import logging
import argparse # Import argparse for robust argument parsing

# Import PyTAP utilities
from pytaps.logging_utils import setup_logger
from pytaps.email_utils import send_email
from pytaps.file_operations import check_file_exists_and_log, clean_directory # <--- ADDED clean_directory
from pytaps.date_time_utils import get_ymd_for_today_and_yesterday

# --- Configuration (can be moved to a config file or env vars for production) ---
SCRIPT_NAME = Path(__file__).stem
LOG_DIRECTORY_BASE = Path(__file__).parent
LOG_LEVEL = logging.DEBUG # <--- CHANGE THIS LINE

SENDER_EMAIL = "pnt@meteo.dz"
RECEIVER_EMAILS = ['aoumeurmohamed2404@gmail.com']
EMAIL_PASSWORD = "Prev-052025"
SMTP_SERVER = "smtp.meteo.dz"
SMTP_PORT = 587
BULLETIN_FOLDER_NAME = '../bulletins'
TMP_FOLDER_NAME = '../tmp'

ARPEGE_GRIB_PATTERN = 'W_fr-meteofrance,MODEL,ARPEGE+01+SP1+00H12H_C_LFPW_{}{}{}0000--.grib2'
ALADIN_GRIB_PATTERN = 'grib_{}{}{}00_0000'

    # --- Argument Parsing for shared log file ---
parser = argparse.ArgumentParser(description="Send Sonelgaz Bulletin Email.")
parser.add_argument('shared_path_log_file', type=str,
                    help='Path to a shared log file for chained scripts. This script expects it to be provided.')
args = parser.parse_args()

script_name = os.path.basename(__file__)

# Configure the logger. This script expects a shared log file path.
if not args.shared_path_log_file:
    # Print to stderr because the logger might not be fully set up yet
    print(f"ERROR: Script '{script_name}' received no shared_path_log_file argument. "
          "This script must be run as part of a chained workflow.", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------------

def main():
    """
    Main function to prepare and send the Sonelgaz bulletin email.
    """


    # Setup logging for the main script
    # Use the shared_log_file if provided, otherwise default behavior of setup_logger
    logger, log_file_path = setup_logger(
        script_name=SCRIPT_NAME,
        log_directory_base=LOG_DIRECTORY_BASE,
        log_level=LOG_LEVEL,
        shared_log_file_path=args.shared_path_log_file  # <--- Pass the parsed argument here!
    )
    logger.info(f"Logger initialized for {SCRIPT_NAME}. Log file: {log_file_path}")
    logger.info("Starting Sonelgaz bulletin sending script.")


    try:
        # We only need today's parts, so we can unpack and ignore yesterday's
        AA_today, MM_today, DD_today, _, _, _ = get_ymd_for_today_and_yesterday(logger_instance=logger)
        logger.debug(f"Today's date components: Year={AA_today}, Month={MM_today}, Day={DD_today}")
    except Exception as e:
        logger.critical(f"Error getting date components using pytaps.date_utils: {e}")
        logger.exception("Full traceback for date component error:")
        sys.exit(1)


    logger.debug(f"Today's date components: Year={AA_today}, Month={MM_today}, Day={DD_today}")

    base_data_path = Path(os.getcwd())
    logger.debug(f"Base data path determined as: {base_data_path}")

    bulletin_folder_path = base_data_path / BULLETIN_FOLDER_NAME
    tmp_folder_path = base_data_path / TMP_FOLDER_NAME

    bulletin_name = bulletin_folder_path / f"Bulletin_Sonelgaz_{DD_today}-{MM_today}-{AA_today}.docx"
    logger.info(f"Expected bulletin file path: {bulletin_name}")

    subject = ""
    body = ""

    arpege_grib_file = tmp_folder_path / ARPEGE_GRIB_PATTERN.format(AA_today, MM_today, DD_today)
    aladin_grib_file = tmp_folder_path / ALADIN_GRIB_PATTERN.format(AA_today, MM_today, DD_today)

    arpege_exists = check_file_exists_and_log(arpege_grib_file, logger_instance=logger)
    aladin_exists = check_file_exists_and_log(aladin_grib_file, logger_instance=logger)

    if arpege_exists:
        subject = f'Bulletin Sonelgaz Du {DD_today}/{MM_today}/{AA_today} Généré avec ARPEGE'
        body = f"Bonjour,\nVeuillez trouver ci-Joint le bulletin automatisé de SONELGAZ pour la journée du {DD_today}/{MM_today}/{AA_today} généré avec le modéle ARPEGE 0.1° \nCordialement, \n(Cet émail a été généré automatiquement avec python3)"
        logger.info("ARPEGE GRIB file found. Setting email subject/body for ARPEGE model.")
    elif aladin_exists:
        subject = f'Bulletin Sonelgaz Du {DD_today}/{MM_today}/{AA_today} Généré avec ALADIN'
        body = f"Bonjour,\nVeuillez trouver ci-Joint le bulletin automatisé de SONELGAZ pour la journée du {DD_today}/{MM_today}/{AA_today} généré avec le modéle ALADIN \nCordialement, \n(Cet émail a été généré automatiquement avec python3)"
        logger.info("ALADIN GRIB file found. Setting email subject/body for ALADIN model.")
    else:
        logger.warning("Neither ARPEGE nor ALADIN GRIB files found. Setting default email subject/body.")
        subject = f'Bulletin Sonelgaz Du {DD_today}/{MM_today}/{AA_today} - No Model Data Found'
        body = "Bonjour,\nLe bulletin Sonelgaz n'a pas pu être généré car les données du modèle ARPEGE ou ALADIN n'ont pas été trouvées.\nCordialement, \n(Cet émail a été généré automatiquement avec python3)"

    if check_file_exists_and_log(bulletin_name, logger_instance=logger):
        logger.info(f"Attempting to send email with bulletin: {bulletin_name}")
        email_sent_successfully = send_email(
            sender_email=SENDER_EMAIL,
            receiver_emails=RECEIVER_EMAILS,
            subject=subject,
            body=body,
            password=EMAIL_PASSWORD,
            smtp_server=SMTP_SERVER,
            smtp_port=SMTP_PORT,
            attachments=[bulletin_name],
            logger_instance=logger
        )
        if email_sent_successfully:
            logger.info("Bulletin email process completed successfully.")
        else:
            logger.error("Failed to send bulletin email.")
    else:
        logger.critical(f"Bulletin file '{bulletin_name}' not found. Email not sent.")

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
