import pandas as pd
import pdbufr # Still needed for pdbufr.read_bufr
import os # Still needed for os.path.exists
from datetime import datetime, timedelta
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler # Still needed for RotatingFileHandler
import argparse # NEW: Import argparse for command-line arguments
import sys      # NEW: Import sys for sys.exit
import subprocess

# Import only the specific generic utilities from pytap
from pytaps.file_operations import check_file_exists_and_log
from pytaps.grib_processor import read_and_process_bufr_temperature
from pytaps.data_utils import select_existing_columns
from pytaps.system_utils import execute_command # NEW: Use execute_command for running next script
from pytaps.logging_utils import setup_logger # NEW: This is the key for shared logging!
from pytaps.date_time_utils import get_ymd_for_today_and_yesterday

# --- Dynamically Determine Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
##scrpt_derectory = operationsystem.path.directoryname(operationsystem.path.absolutpath(file name)) to get the full drectory absolute path and resolve it with direname to get just the folder name where is the script string format

# --- Setup Logging ---
script_name = os.path.basename(__file__)
##script_name = operationsystem.basename(file name) to get the script name

project_root = Path(SCRIPT_DIR).parent # This is the fix for NameError
##return the path directory of the script folder but in object

# Parse command-line arguments for a shared log file path
parser = argparse.ArgumentParser(description="5-traitement_obs_min_max.py script for processing BUFR observations.")
##argumentparser is module that allow you to creat variable and add argument to it.

parser.add_argument('--shared-log-file', type=str,
                    help='Path to a shared log file for chained scripts. This script expects it to be provided.')
##add to the parser variable argumment ''--shared-log-file'  type string and help in case there is no argument add the the run command line as hint for what need to be done
args = parser.parse_args()
## parse_argument allow to the code  to get the excution command lien and check if there the condidtion to run it.


# Configure the logger. This script expects a shared log file path.
# If --shared-log-file is not provided, it's an error in the chain.
if not args.shared_log_file:
    # Print to stderr because the logger might not be fully set up yet
    print(f"ERROR: Script '{script_name}' received no --shared-log-file argument. "
          "This script must be run as part of a chained workflow.", file=sys.stderr)
    sys.exit(1)
## here is conditino to check is there is the condition '--shared-log-file' after store the commend in args and check it so if there is not run system.exit that is libreries module that allow to excute command line into the system


# Use the setup_logger from pytaps.logging_utils
logger, current_log_file_path = setup_logger(
    script_name=script_name,
    log_directory_base=SCRIPT_DIR, # This is used if shared_log_file_path is None, but here it's provided
    log_level=logging.INFO,       # Set the desired logging level for this script
    shared_log_file_path=args.shared_log_file # Pass the parsed argument
)


logger.info("--- Script Start ---")
logger.info(f"Project Root: {project_root}")
logger.info(f"Script's Own Directory: {SCRIPT_DIR}")


# --- Date Preparation ---
try:

    AA_today, MM_today, DD_today, AA_yesterday, MM_yesterday, DD_yesterday = \
        get_ymd_for_today_and_yesterday(logger_instance=logger)
    # The logger.info message is now handled inside get_ymd_for_today_and_yesterday
except Exception as e:
    logger.critical(f"Error during date preparation using pytaps.date_utils: {e}")
    logger.exception("Full traceback for date preparation error:")
    logger.critical("Exiting script due to critical date preparation failure.")
    sys.exit(1)

# Définition des régions et stations
stations_list = [
    "NAAMA", "EL-BAYADH", "LAGHOUAT", "DJELFA", "MSILA", "BISKRA",
    "BATNA", "KHENCHELLA", "TEBESSA", "OULED-DJELLAL", "EL-MGHAIR",
    "EL-OUED", "TOUGGOURT", "OUARGLA", "GHARDAIA", "EL-GOLEA", "TIMIMOUN",
    "BECHAR", "BENI-ABBES", "TINDOUF", "ADRAR", "IN-SALAH", "ILLIZI",
    "DJANET", "TAMANRASSET", "B-B-MOKHTAR", "IN-GUEZZAM"
]
logger.info(f"Defined {len(stations_list)} stations.")

# Création d'un DataFrame contenant toutes les stations
stations_df = pd.DataFrame({"stationOrSiteName": stations_list})
##pd.dataframe si modules from pd libreries that allow you to creat datafrime (table like google sheet table ) from matrix array in this case it creat 2 colums stationname and the list of station.
logger.info("Initial stations DataFrame created.")

# --- Définir les chemins des fichiers BUFR (Kept in main script as per request) ---
# Note: "project_root / ".." " means going one level up from the project_root.
# So if project_root is /path/to/my_project, then bufr_data is expected at /path/to/bufr_data
f_today = project_root / ".." /  f"bufr_data/observations/{AA_today}/{MM_today}/{DD_today}/Synop_{AA_today}{MM_today}{DD_today}0600.bufr"
f_ystd = project_root / ".."  / f"bufr_data/observations/{AA_yesterday}/{MM_yesterday}/{DD_yesterday}/Synop_{AA_yesterday}{MM_yesterday}{DD_yesterday}1800.bufr"

logger.info(f"Expected BUFR file for Tmin (today's 0600Z): {f_today}")
logger.info(f"Expected BUFR file for Tmax (yesterday's 1800Z): {f_ystd}")

# --- Vérifier l'existence des fichiers (Using pytap for individual checks) ---
file_today_exists = check_file_exists_and_log(f_today, logger_instance=logger)
file_ystd_exists = check_file_exists_and_log(f_ystd, logger_instance=logger)

if not file_today_exists and not file_ystd_exists:
    logger.error(f"Neither BUFR file found. Both {f_ystd} and {f_today} are missing. Aborting processing.")
    exit(1) # Exit if no data can be processed
else:
    logger.info("Proceeding with available BUFR files.")

    # --- Lecture du fichier BUFR pour Tmin/Tmax (Using pytap for processing) ---
    if file_today_exists:
        df_tmin = read_and_process_bufr_temperature(
            bufr_file_path=f_today,
            bufr_src_column="minimumTemperatureAtHeightAndOverPeriodSpecified", # Specific BUFR column
            target_column_name="tmin",
            logger_instance=logger
        )
        if df_tmin is not None:
            stations_df = pd.merge(stations_df, df_tmin, on="stationOrSiteName", how="left")
            logger.info(f"Successfully merged Tmin data. Stations with Tmin: {len(df_tmin)}")
        else:
            logger.warning("Tmin data could not be processed, skipping merge.")
    else:
        logger.warning("Skipping Tmin data reading as the file was not found.")

    if file_ystd_exists:
        df_tmax = read_and_process_bufr_temperature(
            bufr_file_path=f_ystd,
            bufr_src_column="maximumTemperatureAtHeightAndOverPeriodSpecified", # Specific BUFR column
            target_column_name="tmax",
            logger_instance=logger
        )
        if df_tmax is not None:
            stations_df = pd.merge(stations_df, df_tmax, on="stationOrSiteName", how="left")
            logger.info(f"Successfully merged Tmax data. Stations with Tmax: {len(df_tmax)}")
        else:
            logger.warning("Tmax data could not be processed, skipping merge.")
    else:
        logger.warning("Skipping Tmax data reading as the file was not found.")

    # --- Nettoyage du DataFrame final (Using pytap for column selection, rest kept) ---
    logger.info("Starting DataFrame cleaning and filtering.")
    desired_columns = ["stationOrSiteName", "tmin", "tmax"]
    
    # Use pytap's select_existing_columns
    filtered_df = select_existing_columns(stations_df, desired_columns, logger_instance=logger)
    
    initial_rows = len(filtered_df)
    filtered_df = filtered_df.drop_duplicates()
    logger.debug(f"Removed {initial_rows - len(filtered_df)} duplicates.")

    initial_rows = len(filtered_df)
    filtered_df = filtered_df[filtered_df["stationOrSiteName"].isin(stations_list)]
    logger.debug(f"Filtered to include only predefined stations. Removed {initial_rows - len(filtered_df)} rows.")

    # Select rows where the sum of NaNs is minimal for each station (Specific logic, kept in main script)
    df_cleaned = filtered_df.loc[filtered_df.isna().sum(axis=1).groupby(filtered_df['stationOrSiteName']).idxmin()]
    logger.info(f"Final cleaned DataFrame has {len(df_cleaned)} rows.")

    logger.debug("Filtered DataFrame head:\n%s", df_cleaned.head().to_string())

    # --- Création du dossier de sortie si inexistant (Kept in main script as per request) ---
    output_dir = project_root / "outputs" / "observations"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory ensured: {output_dir}")
    except OSError as e:
        logger.error(f"Failed to create output directory {output_dir}: {e}", exc_info=True)
        logger.critical("Cannot proceed without output directory. Exiting.")
        exit(1) # Exit if output directory cannot be created

    # --- Sauvegarde du fichier CSV (Kept in main script as per request) ---
    output_file = output_dir / f"tmin_tmax_{AA_today}{MM_today}{DD_today}.csv"
    try:
        df_cleaned.to_csv(output_file, index=False)
        logger.info(f"Data successfully saved to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save data to CSV file {output_file}: {e}", exc_info=True)
        logger.critical("CSV file could not be saved. Data processing incomplete.")


# --- Run Next Program ---
logger.info(f"Attempting to run next program: 6-create_tables.py")
next_script_path = os.path.join(SCRIPT_DIR, "6-create_tables.py")
try:
        # Pass the shared log file path to the next script
        execute_command(
            [sys.executable, next_script_path, "--shared-log-file", current_log_file_path],
            cwd=SCRIPT_DIR # Ensure the working directory is correct for the next script
        )
        logger.info("Successfully executed 6-create_tables.py.")
except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.exception(f"An error occurred while running 6-create_tables.py: {e}")
        sys.exit(1)

except Exception as e:
    logger.exception(f"An unexpected error occurred in the main script flow: {e}")
    sys.exit(1)

logger.info(f"--- Script '{script_name}' finished. ---") # Clear end message