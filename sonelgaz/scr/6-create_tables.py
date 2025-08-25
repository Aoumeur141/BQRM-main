# 6-create_tables.py (Refactored)

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import os
import logging
import argparse # NEW: Import argparse for command-line arguments
import sys      # NEW: Import sys for sys.exit
import subprocess

from typing import Union, Optional, Any # Added for type hints
import openpyxl # Added
from openpyxl import Workbook # Added
from openpyxl.utils.dataframe import dataframe_to_rows # Added

# Import functions from pytap
from pytaps.data_utils import load_dataframe_from_csv, save_dataframe_to_excel
from pytaps.system_utils import execute_command # NEW: Use execute_command for running next script
from pytaps.logging_utils import setup_logger # NEW: This is the key for shared logging!
from pytaps.date_time_utils import get_ymd_for_today_and_yesterday

# --- Dynamically Determine Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Setup Logging ---
script_name = os.path.basename(__file__)

project_root = Path(SCRIPT_DIR).parent # This is the fix for NameError
##return the path directory of the script folder but in object


# Parse command-line arguments for a shared log file path
parser = argparse.ArgumentParser(description="6-create_tables.py script for processing BUFR observations.")
parser.add_argument('shared_path_log_file', type=str,
                    help='Path to a shared log file for chained scripts. This script expects it to be provided.')
args = parser.parse_args()

# Configure the logger. This script expects a shared log file path.
if not args.shared_path_log_file:
    # Print to stderr because the logger might not be fully set up yet
    print(f"ERROR: Script '{script_name}' received no shared_path_log_file argument. "
          "This script must be run as part of a chained workflow.", file=sys.stderr)
    sys.exit(1)

# Use the setup_logger from pytaps.logging_utils
logger, current_log_file_path = setup_logger(
    script_name=script_name,
    log_directory_base=SCRIPT_DIR, # This is used if shared_log_file_path is None, but here it's provided
    log_level=logging.INFO,       # Set the desired logging level for this script
    shared_log_file_path=args.shared_path_log_file  # Pass the parsed argument
)

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

try:
    arpege_file = outputs_dir / "arpege" / f"station_arpege_{AA_today}{MM_today}{DD_today}.csv"
    arpege = load_dataframe_from_csv(arpege_file, logger_instance=logger) # Using pytap function
except FileNotFoundError:
    logger.critical(f"Arpege data file not found: {arpege_file}. Exiting script.")
    exit(1)
except Exception as e:
    logger.critical(f"Error loading arpege data from {arpege_file}: {e}", exc_info=True)
    exit(1)


# Process arpege data (remains in script - business logic)
logger.info("Processing arpege data for 't_demain_arp'.")
try:
    t_demain_arp = arpege[["station", "t2m_30", "t2m_36", "t2m_42", "t2m_45", "t2m_48", "t2m_min", "t2m_max"]].rename(
        columns={
            "station": "Station",
            "t2m_30": "prev_06",
            "t2m_36": "prev_12",
            "t2m_42": "prev_18",
            "t2m_45": "prev_21",
            "t2m_48": "prev_24",
            "t2m_min": "prev_min",
            "t2m_max": "prev_max"
        }
    ).round(0) ## to remove the decimale 
    
    logger.info("Arpege data processed successfully.")
except Exception as e:
    logger.critical(f"Error processing arpege data: {e}", exc_info=True)
    exit(1)
 
# Observations (remains in script - business logic and specific error handling)
station_mapping = {
    "BEJAIA-AEROPORT": "BEJAIA",
    "ORAN-SENIA": "ORAN",
    "MASCARA-GHRISS": "MASCARA",
    "TLEMCEN-ZENATA": "TLEMCEN",
    "JIJEL-ACHOUAT": "JIJEL",
    "M'SILA": "MSILA"
}
logger.info("Loading and processing observations data.")
try:
    obs_file = outputs_dir / "observations" / f"observations_{AA_today}{MM_today}{DD_today}.csv"
    obs = load_dataframe_from_csv(obs_file, logger_instance=logger) # Using pytap function 
    
    obs["stationOrSiteName"] = obs["stationOrSiteName"].replace(station_mapping)

    t_obs = obs[["stationOrSiteName", "t2m_06", "t2m_12", "t2m_18", "t2m_21", "t2m_24"]].rename(
        columns={
            "stationOrSiteName": "Station",
            "t2m_06": "obs_06",
            "t2m_12": "obs_12",
            "t2m_18": "obs_18",
            "t2m_21": "obs_21",
            "t2m_24": "obs_24"
        }
    ).round(0)
    logger.info(f"Observations data loaded and processed from: {obs_file}")
except FileNotFoundError:
    logger.warning(f"Observations data file not found: {obs_file}. Proceeding without observation data for current day by creating an empty DataFrame.")
    t_obs = pd.DataFrame(columns=["Station", "obs_06", "obs_12", "obs_18", "obs_21", "obs_24"])
except Exception as e:
    logger.error(f"Error loading or processing observations data from {obs_file}: {e}", exc_info=True)
    t_obs = pd.DataFrame(columns=["Station", "obs_06", "obs_12", "obs_18", "obs_21", "obs_24"])


# Observations min/max (remains in script - business logic and specific error handling)
logger.info("Loading and processing observations min/max data.")
try:
    obs_minmax_file = outputs_dir / "observations" / f"tmin_tmax_{AA_today}{MM_today}{DD_today}.csv"
    obs_minmax = load_dataframe_from_csv(obs_minmax_file, logger_instance=logger) # Using pytap function 
    
    obs_minmax["stationOrSiteName"] = obs_minmax["stationOrSiteName"].replace(station_mapping)

    t_obs_minmax = obs_minmax[["stationOrSiteName", "tmin", "tmax"]].rename(
        columns={
            "stationOrSiteName": "Station",
            "tmin": "tmin_obs",
            "tmax": "tmax_obs"
        }
    ).round(0)
    logger.info(f"Observations min/max data loaded and processed from: {obs_minmax_file}")
except FileNotFoundError:
    logger.warning(f"Observations min/max data file not found: {obs_minmax_file}. Proceeding without min/max observation data for current day by creating an empty DataFrame.")
    t_obs_minmax = pd.DataFrame(columns=["Station", "tmin_obs", "tmax_obs"])
except Exception as e:
    logger.error(f"Error loading or processing observations min/max data from {obs_minmax_file}: {e}", exc_info=True)
    t_obs_minmax = pd.DataFrame(columns=["Station", "tmin_obs", "tmax_obs"])

# Merge all data (remains in script - business logic)
logger.info("Merging all processed dataframes into 'full_table'.")
try:
    full_table = pd.merge(t_demain_arp, t_obs, on="Station", how="outer")
    ## how = outer Guarantees all rows from both the left and right DataFrames are in the result Rows unique to either side will have NaN for the columns that came from the non-matching side.

    full_table = pd.merge(full_table, t_obs_minmax, on="Station", how="outer")
    logger.info("Dataframes merged successfully.")
except Exception as e:
    logger.critical(f"Error merging dataframes: {e}", exc_info=True)
    exit(1)

# Set column order and fill missing values (remains in script - business logic)
logger.info("Reindexing columns and filling missing values in 'full_table'.")
try:
    columns_order = ["Station", "tmin_obs", "prev_min", "tmax_obs", "prev_max",
                     "obs_06", "obs_12", "obs_18", "obs_21", "obs_24",
                     "prev_06", "prev_12", "prev_18", "prev_21", "prev_24"]
    
    full_table = full_table.reindex(columns=columns_order).fillna("/")
 ## we use reindex to reorder the dataframe so by using columns that mean we need to reindex the columns by columsn_order after fill any note a number with "/"

    logger.info("Columns reindexed and missing values filled.")
except Exception as e:
    logger.critical(f"Error reindexing or filling missing values: {e}", exc_info=True)
    exit(1)

# Define regions (remains in script - configuration data)
regions = {
    "Ouest": ["ORAN", "TLEMCEN", "MASCARA", "SAIDA", "NAAMA", "RELIZANE",
              "SIDI-BEL-ABBES", "MECHERIA", "EL-BAYADH", "EL-KHEITER",
              "BENI-SAF", "MOSTAGANEM"],
    "Centre": ["DAR-EL-BEIDA", "CHLEF", "TIZI-OUZOU", "MEDEA", "DJELFA",
               "MSILA", "BOUIRA", "MILIANA", "TIARET"],

    "Est": ["ANNABA", "BEJAIA", "SKIKDA", "JIJEL", "CONSTANTINE", "BATNA",
            "GUELMA", "TEBESSA", "SETIF", "SOUK AHRAS", "O-EL-BOUAGHI",
            "B-B-ARRERIDJ", "KHENCHELLA"],

    "Sud": ["BECHAR", "TINDOUF", "GHARDAIA", "HASSI-RMEL", "LAGHOUAT",
            "BISKRA", "EL-OUED", "HASSI-MESSAOUD", "TOUGGOURT", "EL-GOLEA",
            "ILLIZI", "TAMANRASSET", "ADRAR", "IN-SALAH"]
}

# Process each region
logger.info("Starting processing and saving Excel files for each region.")

for region, stations in regions.items():
    logger.info(f"Processing region: {region}")
    try:
        # Ensure all stations are present, fill missing with "/" (business logic)
        tab_region = full_table.set_index("Station").reindex(stations).reset_index().fillna("/")

        # Sort according to predefined station order (business logic)
        tab_region["Station"] = pd.Categorical(tab_region["Station"], categories=stations, ordered=True)
        tab_region = tab_region.sort_values("Station")

#so you are saying that tab region will be like this :  
# start with loop that store the key and there values in station so that well be 4 temperary stations variable each for each region
# after that we well get the full table and set station colums as the new index 
# reindex stations that mean to add new station stored in stations and remove the station there is not in stations and order them base on stations 
# reset_index to convert the current index to clolumn and creat the nnumerical index 
# then use fill not a number to fill out all NAN values 

        output_excel_path = outputs_dir / "tab_reg" / f"regions_{region}.xlsx"
        
        # Using pytap's save_dataframe_to_excel
        save_dataframe_to_excel(
            tab_region,
            output_excel_path,
            sheet_name=region,
            include_index=False,
            include_header=True,
            logger_instance=logger # Pass your script's logger
        )
        logger.info(f"Successfully saved Excel file for region '{region}' to {output_excel_path}")
    except Exception as e:
        logger.error(f"Error processing or saving Excel for region '{region}': {e}", exc_info=True)
        # Decision point: If failure for one region should stop the script, uncomment 'exit(1)' here.
        # exc_info=True to include the full "traceback"
        # exit(1)

logger.info("All regional Excel files processed and created successfully.")


# --- Run Next Program ---
logger.info(f"Attempting to run next program: 7-create_word.py")
next_script_path = os.path.join(SCRIPT_DIR, "7-create_word.py")
try:
        # Pass the shared log file path to the next script
        execute_command(
            [sys.executable, next_script_path, current_log_file_path],
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