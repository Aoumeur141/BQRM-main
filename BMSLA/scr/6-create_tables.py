import pandas as pd
# from openpyxl import Workbook # REMOVED: Handled by pytaps.data_utils
# from openpyxl.utils.dataframe import dataframe_to_rows # REMOVED: Handled by pytaps.data_utils
from pathlib import Path
from datetime import datetime, timedelta
# from modules.module import run_next_program # Not used in the provided code
import os
import logging
import argparse
import sys
import subprocess

from typing import Union, Optional, Any

# NEW: Import data utility functions
from pytaps.data_utils import load_dataframe_from_csv, save_dataframe_to_excel
from pytaps.system_utils import execute_command
from pytaps.logging_utils import setup_logger
from pytaps.date_time_utils import get_ymd_for_today_and_yesterday

# --- Dynamically Determine Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Setup Logging ---
script_name = os.path.basename(__file__)

project_root = Path(SCRIPT_DIR).parent # This is the fix for NameError


# Parse command-line arguments for a shared log file path
parser = argparse.ArgumentParser(description="6-create_tables.py script for processing BUFR observations.")
parser.add_argument('--shared-log-file', type=str,
                    help='Path to a shared log file for chained scripts. This script expects it to be provided.')
args = parser.parse_args()

# Configure the logger. This script expects a shared log file path.
# If --shared-log-file is not provided, it's an error in the chain.
if not args.shared_log_file:
    # Print to stderr because the logger might not be fully set up yet
    print(f"ERROR: Script '{script_name}' received no --shared-log-file argument. "
          "This script must be run as part of a chained workflow.", file=sys.stderr)
    sys.exit(1)

# Use the setup_logger from pytaps.logging_utils
logger, current_log_file_path = setup_logger(
    script_name=script_name,
    log_directory_base=SCRIPT_DIR, # This is used if shared_log_file_path is None, but here it's provided
    log_level=logging.INFO,       # Set the desired logging level for this script
    shared_log_file_path=args.shared_log_file # Pass the parsed argument
)


# REMOVED: The custom create_workbook_with_sheet function is no longer needed
# as save_dataframe_to_excel from pytaps.data_utils handles this internally.
# def create_workbook_with_sheet(sheet_name):
#     logger.debug(f"Creating workbook with sheet: '{sheet_name}'")
#     wb = Workbook()
#     ws = wb.active
#     ws.title = sheet_name
#     return wb, ws

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

# Define outputs_dir relative to project_root for robustness
outputs_dir = project_root / "outputs"
logger.info(f"Attempting to load data from outputs directory: {outputs_dir.resolve()}")

arpege = pd.DataFrame() # Initialize to empty DataFrame
tmin_max = pd.DataFrame() # Initialize to empty DataFrame

# --- Load arpege data using load_dataframe_from_csv ---
arpege_file_path = outputs_dir / f"arpege/station_arpege_{AA_today}{MM_today}{DD_today}.csv"
arpege = load_dataframe_from_csv(arpege_file_path, logger_instance=logger)

if arpege.empty:
    logger.error(f"Arpege data is empty or could not be loaded from {arpege_file_path}. Exiting.")
    sys.exit(1)


# Note: The original code loads tmin_max here, but then reloads the same file into obs_minmax later.
# Keeping the original redundant load for consistency with user's code, but adding a log.
# --- Load tmin_max data using load_dataframe_from_csv ---
tmin_max_file_path = outputs_dir / f"observations/tmin_tmax_{AA_today}{MM_today}{DD_today}.csv"
logger.info(f"Attempting to load tmin_max data (first instance) from: {tmin_max_file_path}")
tmin_max = load_dataframe_from_csv(tmin_max_file_path, logger_instance=logger)

if tmin_max.empty:
    logger.error(f"Tmin/Tmax data is empty or could not be loaded from {tmin_max_file_path}. Exiting.")
    sys.exit(1)


# Process arpege data
logger.info("Processing arpege data: renaming columns and rounding.")
t_demain_arp = arpege[["station", "t2m_min", "t2m_max", "t2m_max_48"]].rename(
    columns={
        "station": "Station",
        "t2m_min": "prev_min",
        "t2m_max": "prev_max",
        "t2m_max_48": "prev_max_48"
    }
).round(0)
logger.debug(f"Processed arpege data (t_demain_arp) head:\n{t_demain_arp.head()}")

# Observations
station_mapping = {
    "M'SILA": "MSILA",
    "EL BAYADH": "EL-BAYADH",
    "OULED DJELLAL": "OULED-DJELLAL",
    "EL M'GHAIR": "EL-MGHAIR",
    "EL OUED": "EL-OUED",
    "EL MENIAA": "EL-GOLEA",
    "BENI ABBES": "BENI-ABBES",
    "IN SALAH": "IN-SALAH",
    "BORDJ BADJI MOKHTARI": "B-B-MOKHTAR",
    "IN GUEZZAM": "IN-GUEZZAM"
}
logger.info(f"Defined {len(station_mapping)} station mappings for observations.")


# Observations min/max (re-loading the same file as tmin_max)
# --- Load obs_minmax data using load_dataframe_from_csv ---
obs_minmax_file_path = outputs_dir / f"observations/tmin_tmax_{AA_today}{MM_today}{DD_today}.csv"
logger.warning(f"Re-attempting to load observations min/max data from: {obs_minmax_file_path}. This might be redundant as it was loaded earlier as 'tmin_max'.")
obs_minmax = load_dataframe_from_csv(obs_minmax_file_path, logger_instance=logger)

if obs_minmax.empty:
    logger.error(f"Observations min/max data is empty or could not be loaded from {obs_minmax_file_path}. Exiting.")
    sys.exit(1)


logger.info("Applying station mapping to 'stationOrSiteName' column in observations data.")
obs_minmax["stationOrSiteName"] = obs_minmax["stationOrSiteName"].replace(station_mapping)

t_obs_minmax = obs_minmax[["stationOrSiteName", "tmin", "tmax"]].rename(
    columns={
        "stationOrSiteName": "Station",
        "tmin": "tmin_obs",
        "tmax": "tmax_obs"
    }
).round(0)
logger.debug(f"Processed observations data (t_obs_minmax) head:\n{t_obs_minmax.head()}")

# Merge all data (first instance)
logger.info("Merging arpege and observations data (first merge).")
full_table = pd.merge(t_demain_arp, t_obs_minmax, on="Station", how="outer")
logger.debug(f"Full table after first merge head:\n{full_table.head()}")

# Set column order and fill missing values (first instance)
columns_order = ["Station", "tmin_obs", "prev_min", "tmax_obs", "prev_max", "prev_max_48"]
full_table = full_table.reindex(columns=columns_order).fillna("/")
logger.debug(f"Full table after reindex and fillna (first instance) head:\n{full_table.head()}")

# List of stations to be used
stations_list = [
    "NAAMA", "EL-BAYADH", "LAGHOUAT", "DJELFA", "MSILA", "BISKRA",
    "BATNA", "KHENCHELLA", "TEBESSA", "OULED-DJELLAL", "EL-MGHAIR",
    "EL-OUED", "TOUGGOURT", "OUARGLA", "GHARDAIA", "EL-GOLEA", "TIMIMOUN",
    "BECHAR", "BENI-ABBES", "TINDOUF", "ADRAR", "IN-SALAH", "ILLIZI",
    "DJANET", "TAMANRASSET", "B-B-MOKHTAR", "IN-GUEZZAM"
]
logger.info(f"Defined {len(stations_list)} stations for the final table filtering and ordering.")

# Merge all data (second instance - this is a duplicate of the first merge block)
logger.warning("Duplicate merge operation detected. This block is identical to a previous merge and might be redundant.")
full_table = pd.merge(t_demain_arp, t_obs_minmax, on="Station", how="outer")
logger.debug(f"Full table after second merge head:\n{full_table.head()}")

# Set column order and fill missing values (second instance - also duplicate)
columns_order = ["Station", "tmin_obs", "prev_min", "tmax_obs", "prev_max",  "prev_max_48"]
full_table = full_table.reindex(columns=columns_order).fillna("/")
logger.debug(f"Full table after reindex and fillna (second instance) head:\n{full_table.head()}")


# Ensure only the stations in the list are included and fill missing ones
logger.info("Reindexing and filling missing stations based on the predefined list.")
final_table = full_table.set_index("Station").reindex(stations_list).reset_index().fillna("/")
logger.debug(f"Final table after reindex to stations_list head:\n{final_table.head()}")

# Sort by station list order
logger.info("Sorting final table by the specified station list order.")
final_table["Station"] = pd.Categorical(final_table["Station"], categories=stations_list, ordered=True)
final_table = final_table.sort_values("Station")
logger.debug(f"Final table after sorting head:\n{final_table.head()}")

# Save to Excel file (one table)
excel_output_path = outputs_dir / f"tab_reg/all_stations.xlsx"
logger.info(f"Attempting to save final table to Excel: {excel_output_path}")

try:
    # Use save_dataframe_to_excel from pytaps.data_utils
    save_dataframe_to_excel(
        df=final_table,
        file_path=excel_output_path,
        sheet_name="All Stations",
        include_header=True,
        include_index=False,
        logger_instance=logger
    )
    logger.info(f"Excel file successfully created at: {excel_output_path}")
except Exception as e:
    logger.exception(f"Error saving Excel file to {excel_output_path}: {e}")
    logger.error("Exiting due to Excel file saving failure.")
    sys.exit(1) # Use sys.exit for consistency


# --- Run Next Program ---
logger.info(f"Attempting to run next program: 7-create_word.py")
next_script_path = os.path.join(SCRIPT_DIR, "7-create_word.py")
try:
        # Pass the shared log file path to the next script
        execute_command(
            [sys.executable, next_script_path, "--shared-log-file", current_log_file_path],
            cwd=SCRIPT_DIR # Ensure the working directory is correct for the next script
        )
        logger.info("Successfully executed 7-create_word.py.")
except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.exception(f"An error occurred while running 7-create_word.py: {e}")
        sys.exit(1)

except Exception as e:
    logger.exception(f"An unexpected error occurred in the main script flow: {e}")
    sys.exit(1)

logger.info(f"--- Script '{script_name}' finished. ---") # Clear end message
