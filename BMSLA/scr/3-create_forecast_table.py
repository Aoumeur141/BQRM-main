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

# Removed: print("--- DEBUG: 3-create_forecast_table.py script execution started. (Initial print) ---")
# This initial print is now handled by the setup_logger and initial info messages.

# --- Dynamically Determine Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Setup Logging ---
script_name = os.path.basename(__file__)

# Define the project root directory.
project_root = Path(SCRIPT_DIR).parent

# Parse command-line arguments for a shared log file path
parser = argparse.ArgumentParser(description="3-create_forecast_table.py script for processing BUFR observations.")
parser.add_argument('--shared-log-file', type=str,
                    help='Path to a shared log file for chained scripts. This script expects it to be provided.')
args = parser.parse_args()

# Configure the logger. This script expects a shared log file path.
if not args.shared_log_file:
    # Print to stderr because the logger might not be fully set up yet
    print(f"ERROR: Script '{script_name}' received no --shared-log-file argument. "
          "This script must be run as part of a chained workflow.", file=sys.stderr)
    sys.exit(1)

# Use the setup_logger from pytaps.logging_utils
logger, current_log_file_path = setup_logger(
    script_name=script_name,
    log_directory_base=SCRIPT_DIR,
    log_level=logging.INFO,       # Set the desired logging level for this script
    shared_log_file_path=args.shared_log_file # Pass the parsed argument
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

# --- GRIB Data Extraction for 0-24h period ---
logger.info("Starting GRIB data extraction for 2m temperature (0-24h period).")
t2m_all_times_0_24h = [] # This will store data for 0-24h min/max calculation

try:
    # We only care about the t2m_all_times_for_minmax for this range, not the individual columns for the final output
    _, t2m_all_times_0_24h = extract_field_for_stations(
        epygram_resource=arp,
        stations_df=stations,
        field_short_name='2t',
        time_steps=list(range(0, 25)), # Steps 0 to 24
        kelvin_offset=272.15,
        logger_instance=logger,
        output_column_prefix='t2m' # This prefix is still needed internally by the function, but its output_dict won't be used directly for final table columns
    )
    logger.info("Finished extraction of 2m temperature data for 0-24h period.")
except Exception as e:
    logger.critical(f"Error during GRIB data extraction for 0-24h period: {e}")
    logger.exception("Full traceback for 0-24h GRIB data extraction error:")
    logger.critical("Exiting script due to critical GRIB data extraction failure.")
    sys.exit(1)

# --- GRIB Data Extraction for 24-48h period ---
logger.info("Starting GRIB data extraction for 2m temperature (24-48h period).")
t2m_all_times_24_48h = [] # This will store data for 24-48h max calculation

try:
    # Again, we only care about the t2m_all_times_for_minmax for this range
    _, t2m_all_times_24_48h = extract_field_for_stations(
        epygram_resource=arp,
        stations_df=stations,
        field_short_name='2t',
        time_steps=list(range(24, 49)), # Steps 24 to 48
        kelvin_offset=272.15,
        logger_instance=logger,
        output_column_prefix='t2m'
    )
    logger.info("Finished extraction of 2m temperature data for 24-48h period.")
except Exception as e:
    logger.critical(f"Error during GRIB data extraction for 24-48h period: {e}")
    logger.exception("Full traceback for 24-48h GRIB data extraction error:")
    logger.critical("Exiting script due to critical GRIB data extraction failure.")
    sys.exit(1)

finally:
    if arp:
        try:
            arp.close()
            logger.info("GRIB file resource closed successfully.")
        except Exception as e:
            logger.error(f"Error closing GRIB file resource: {e}")
            logger.exception("Traceback for GRIB file closing error:")

# --- Calculation of Min/Max for 0-24h period ---
logger.info("Calculating min and max temperatures across 0-24h time steps for each station.")
t2m_min_0_24h = [np.nan] * len(stations)
t2m_max_0_24h = [np.nan] * len(stations)
try:
    # Transpose t2m_all_times_0_24h to be (num_stations, num_timesteps) for row-wise min/max
    t2m_min_np_0_24h, t2m_max_np_0_24h = calculate_nan_min_max(t2m_all_times_0_24h, logger_instance=logger)
    t2m_min_0_24h = t2m_min_np_0_24h.tolist()
    t2m_max_0_24h = t2m_max_np_0_24h.tolist()
    logger.info("Min/Max temperatures (0-24h) calculated successfully.")
except Exception as e:
    logger.error(f"Error calculating min/max temperatures (0-24h): {e}. Populating min/max columns with NaNs.")
    logger.exception("Full traceback for 0-24h min/max calculation error:")

# --- Calculation of Max for 24-48h period ---
logger.info("Calculating max temperature across 24-48h time steps for each station.")
t2m_max_24_48h = [np.nan] * len(stations)
try:
    # We only need the max from this range
    _, t2m_max_np_24_48h = calculate_nan_min_max(t2m_all_times_24_48h, logger_instance=logger)
    t2m_max_24_48h = t2m_max_np_24_48h.tolist()
    logger.info("Max temperature (24-48h) calculated successfully.")
except Exception as e:
    logger.error(f"Error calculating max temperature (24-48h): {e}. Populating max column with NaNs.")
    logger.exception("Full traceback for 24-48h max calculation error:")


# --- Conversion to DataFrame with desired columns ---
logger.info("Creating final DataFrame with specific columns as per Version 1.")
final_table = pd.DataFrame() # Initialize to empty DataFrame
try:
    # Explicitly create the DataFrame with only the desired columns from the calculated values
    final_table = pd.DataFrame({
        'station': stations['station'].tolist(), # Use stations DataFrame directly for metadata
        'SID': stations['SID'].tolist(),
        'lon': stations['lon'].tolist(),
        'lat': stations['lat'].tolist(),
        't2m_min': t2m_min_0_24h,
        't2m_max': t2m_max_0_24h,
        't2m_max_48': t2m_max_24_48h,
    })
    logger.info("DataFrame created successfully with Version 1 column structure.")
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
logger.info(f"Attempting to run next program: 5-traitement_obs_min_max.py")
next_script_path = os.path.join(SCRIPT_DIR, "5-traitement_obs_min_max.py")
try:
    execute_command(
        [sys.executable, next_script_path, "--shared-log-file", current_log_file_path],
        cwd=SCRIPT_DIR # Ensure the working directory is correct for the next script
    )
    logger.info("Successfully executed 5-traitement_obs_min_max.py.")
except (subprocess.CalledProcessError, FileNotFoundError) as e:
    logger.exception(f"An error occurred while running 5-traitement_obs_min_max.py: {e}")
    sys.exit(1)
except Exception as e:
    logger.exception(f"An unexpected error occurred in the main script flow: {e}")
    sys.exit(1)

logger.info(f"--- Script '{script_name}' finished. ---")
