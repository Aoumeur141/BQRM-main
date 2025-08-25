import os
from pathlib import Path
import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
import sys
import argparse
import subprocess

# Import utilities from your pytap package
from pytaps.data_utils import load_dataframe_from_csv, save_dataframe_to_csv
from pytaps.grib_processor import open_epygram_grib_resource, extract_field_for_stations
from pytaps.numpy_utils import calculate_nan_min_max
from pytaps.logging_utils import setup_logger
from pytaps.system_utils import execute_command
from pytaps.date_time_utils import get_ymd_for_today_and_yesterday


# --- Dynamically Determine Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Setup Logging ---
script_name = os.path.basename(__file__)

# Define the project root directory.
project_root = Path(SCRIPT_DIR).parent

# Parse command-line arguments for a shared log file path
parser = argparse.ArgumentParser(description="3-create_forecast_table.py script for processing BUFR observations.")
parser.add_argument('shared_path_log_file', type=str,
                    help='Path to a shared log file for chained scripts. This script expects it to be provided.')
args = parser.parse_args()


# Use the setup_logger from pytaps.logging_utils
logger, current_log_file_path = setup_logger(
    script_name=script_name,
    log_directory_base=SCRIPT_DIR,
    log_level=logging.INFO,       # Set the desired logging level for this script
    shared_log_file_path=args.shared_path_log_file  # Pass the parsed argument
)

logger.info(f"--- Script '{script_name}' execution started. ---")
logger.info(f"Logger configured. Logs will be saved to: {current_log_file_path}")
logger.info(f"Current script directory: {SCRIPT_DIR}")
logger.info(f"Determined project root directory: {project_root}")
logger.info(f"Current working directory (before change): {os.getcwd()}")

try:
    # Change current working directory to the project root for consistent pathing
    os.chdir(project_root)
    logger.info(f"Changed current working directory to: {os.getcwd()}")
except OSError as e:
    logger.critical(f"Failed to change directory to {project_root}: {e}")
    logger.critical("Exiting script due to critical directory change failure.")
    sys.exit(1)

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


# --- Station Data Loading ---
stations_file_path = project_root / 'template' / 'station_onm_officielle.csv'
stations = pd.DataFrame() # Initialize to empty DataFrame

logger.info(f"Attempting to load station data from: {stations_file_path}")
try:
    stations = load_dataframe_from_csv(stations_file_path, logger_instance=logger)
    if stations.empty:
        logger.critical("No station data loaded (DataFrame is empty). This might indicate a missing or empty file, or a parsing error.")
        sys.exit(1)
    logger.info(f"Successfully loaded {len(stations)} stations.")
    logger.debug(f"Stations data head:\n{stations.head()}")
except Exception as e:
    logger.critical(f"An error occurred while attempting to load stations data from: {stations_file_path}")
    logger.exception("Full traceback for stations data loading error:")
    logger.critical(f"Exiting script due to error during stations data loading.")
    sys.exit(1)

# --- GRIB File Reading ---
grib_file_name = f"tmp/2t_{AA_today}{MM_today}{DD_today}.grib"
grib_file_path = project_root / grib_file_name
arp = None # Initialize GRIB resource variable

logger.info(f"Attempting to open GRIB file: {grib_file_path}")
try:
    arp = open_epygram_grib_resource(grib_file_path, logger_instance=logger)
    logger.info("GRIB file resource successfully opened.")
except Exception as e:
    logger.critical(f"An error occurred while attempting to open GRIB file: {grib_file_path}")
    logger.exception("Full traceback for GRIB file opening error:")
    logger.critical(f"Exiting script due to GRIB file opening error.")
    sys.exit(1)

# --- GRIB Data Extraction ---
# Initialize results dictionary with station metadata
results = {
    'station': stations['station'].tolist(),
    'SID': stations['SID'].tolist(),
    'lon': stations['lon'].tolist(),
    'lat': stations['lat'].tolist()
}
t2m_all_times_for_minmax = [] # This list will be populated by the pytap function for min/max calculation

logger.info("Starting GRIB data extraction for 2m temperature.")
try:
    extracted_data_dict, t2m_all_times_for_minmax = extract_field_for_stations(
        epygram_resource=arp,
        stations_df=stations,
        field_short_name='2t',
        time_steps=list(range(24, 49)), # Corresponds to range(24, 49, 1) in old script
        kelvin_offset=272.15, # Explicitly use the old script's offset
        logger_instance=logger,
        output_column_prefix='t2m'
    )
    results.update(extracted_data_dict)
    logger.info("Finished extraction of 2m temperature data from GRIB file and populated 't2m_XX' columns.")
except Exception as e:
    logger.critical(f"Error during GRIB data extraction (via pytaps.grib_processor.extract_field_for_stations): {e}")
    logger.exception("Full traceback for GRIB data extraction error:")
    logger.critical("Exiting script due to critical GRIB data extraction failure.")
    # If extraction fails, populate relevant columns with NaNs to allow subsequent steps to proceed
    num_stations = len(stations)
    num_timesteps = len(list(range(24, 49)))
    for time_step in list(range(24, 49)):
        results[f't2m_{time_step}'] = [np.nan] * num_stations
    t2m_all_times_for_minmax = [[np.nan] * num_stations for _ in range(num_timesteps)]
    sys.exit(1)

finally:
    if arp:
        try:
            arp.close()
            logger.info("GRIB file resource closed successfully.")
        except Exception as e:
            logger.error(f"Error closing GRIB file resource: {e}")
            logger.exception("Traceback for GRIB file closing error:")

# --- Calculation of Min/Max ---
logger.info("Calculating min and max temperatures across all time steps for each station.")
try:
    t2m_min_np, t2m_max_np = calculate_nan_min_max(t2m_all_times_for_minmax, logger_instance=logger)
    results['t2m_min'] = t2m_min_np.tolist()
    results['t2m_max'] = t2m_max_np.tolist()
    logger.info("Min/Max temperatures calculated successfully.")
except Exception as e:
    logger.error(f"Error calculating min/max temperatures (via pytaps.numpy_utils.calculate_nan_min_max): {e}. Populating min/max columns with NaNs.")
    logger.exception("Full traceback for min/max calculation error:")
    results['t2m_min'] = [np.nan] * len(stations)
    results['t2m_max'] = [np.nan] * len(stations)

# --- Conversion to DataFrame ---
logger.info("Converting results dictionary to pandas DataFrame.")
final_table = pd.DataFrame() # Initialize to empty DataFrame
try:
    final_table = pd.DataFrame(results)
    logger.info("DataFrame created successfully.")
    logger.debug(f"Final table head:\n{final_table.head()}")
except Exception as e:
    logger.critical(f"Error creating final DataFrame: {e}")
    logger.exception("Full traceback for DataFrame creation error:")
    logger.critical("Exiting script due to critical DataFrame creation failure.")
    sys.exit(1)

# --- Saving Final Table ---
output_dir = project_root / "outputs" / "arpege"
output_file_name = f"station_arpege_{AA_today}{MM_today}{DD_today}.csv"
output_file_path = output_dir / output_file_name

logger.info(f"Attempting to save final table to: {output_file_path}")
try:
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured output directory exists: {output_dir}")
    save_dataframe_to_csv(final_table, output_file_path, logger_instance=logger)
    logger.info(f"Final table successfully saved to: {output_file_path}")
except Exception as e:
    logger.critical(f"Exiting script due to critical CSV saving failure: {e}")
    logger.exception("Full traceback for CSV saving error:")
    sys.exit(1)

# --- Run Next Program ---
logger.info(f"Attempting to run next program: 4-traitement_obs.py")
next_script_path = os.path.join(SCRIPT_DIR, "4-traitement_obs.py")
try:
    execute_command(
        [sys.executable, next_script_path, current_log_file_path],
        cwd=SCRIPT_DIR # Ensure the working directory is correct for the next script
    )
    logger.info("Successfully executed 4-traitement_obs.py.")
except (subprocess.CalledProcessError, FileNotFoundError) as e:
    logger.exception(f"An error occurred while running 4-traitement_obs.py: {e}")
    sys.exit(1)
except Exception as e:
    logger.exception(f"An unexpected error occurred in the main script flow: {e}")
    sys.exit(1)

logger.info(f"--- Script '{script_name}' finished. ---")
