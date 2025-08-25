import pandas as pd
import pdbufr # Still needed for pdbufr.read_bufr implicitly through grib_processor
import os
from datetime import datetime, timedelta
import logging # Import the logging module
import argparse # NEW: Import argparse for command-line arguments
import sys      # NEW: Import sys for sys.exit
import subprocess

from pytaps.file_operations import build_time_series_filepath, check_file_exists_and_log
from pytaps.grib_processor import read_and_process_bufr_temperature
from pytaps.data_utils import select_existing_columns # New module
from pytaps.logging_utils import setup_logger # NEW: This is the key for shared logging!
from pytaps.system_utils import execute_command # NEW: Use execute_command for running next script
from pytaps.date_time_utils import get_ymd_for_today_and_yesterday

# --- Dynamically Determine Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Setup Logging ---
script_name = os.path.basename(__file__)

# Parse command-line arguments for a shared log file path
parser = argparse.ArgumentParser(description="3-create_forecast_table.py script for processing BUFR observations.")
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

# --- Original Script with Logging ---

# Get the directory where the current script is located (Kept as per instruction)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
logger.info(f"Script directory: {SCRIPT_DIR}")

# Define the base directory for BUFR observation files. (Kept as per instruction)
BUFR_BASE_DIR = os.path.join(SCRIPT_DIR, '../../','bufr_data', 'observations')
logger.info(f"BUFR base directory: {BUFR_BASE_DIR}")

# Define the output directory for CSV files. (Kept as per instruction)
OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..', 'outputs', 'observations')
try:
    os.makedirs(OUTPUT_DIR, exist_ok=True) # Ensure the output directory exists
    logger.info(f"Output directory: {OUTPUT_DIR}")
except OSError as e:
    logger.error(f"Failed to create output directory {OUTPUT_DIR}: {e}")
    logger.error("Exiting due to critical directory creation failure.")
    exit(1) # Exit if output directory cannot be created

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


# Initialize an empty DataFrame to store all results
final_df = None

regions = {
    "Ouest": ["ORAN-SENIA", "TLEMCEN-ZENATA", "MASCARA-GHRISS", "SAIDA", "NAAMA", "RELIZANE",
              "SIDI-BEL-ABBES", "MECHERIA", "EL-BAYADH", "BENI-SAF", "MOSTAGANEM"],

    "Centre": ["DAR-EL-BEIDA", "CHLEF", "TIZI-OUZOU", "MEDEA", "DJELFA",
               "MSILA", "BOUIRA", "MILIANA", "TIARET"],

    "Est": ["ANNABA", "BEJAIA-AEROPORT", "SKIKDA", "JIJEL-ACHOUAT", "CONSTANTINE", "BATNA",
            "GUELMA", "TEBESSA", "SETIF", "SOUK AHRAS", "O-EL-BOUAGHI",
            "B-B-ARRERIDJ", "KHENCHELLA"],

    "Sud": ["BECHAR", "TINDOUF", "GHARDAIA", "HASSI-RMEL", "LAGHOUAT",
            "BISKRA", "EL-OUED", "HASSI-MESSAOUD", "TOUGGOURT", "EL-GOLEA",
            "ILLIZI", "TAMANRASSET", "ADRAR", "IN-SALAH"]
}

stations_list = sorted(set(station for region in regions.values() for station in region))

##start inside the loop we have region in region in regions.values() that mean the region = regions.values() ===> region = keys values only (not the keys names {ouest,est,centre,sud}) and station for .... for station in region that will be the second loop that go from region = [],[],[] to station = [all in one] and we have set(station) to remove any duplicated values and sorted to put them on alphabic order.

# Create a DataFrame containing all stations
stations_df = pd.DataFrame({"stationOrSiteName": stations_list})
logger.info(f"Initialized DataFrame with {len(stations_list)} unique stations.")
logger.debug(f"Stations list: {stations_list}")
## creat data frime (table) that it have 2 colum stationsitenames and the station_list 

# Define the list of times to process with their corresponding date info and target column names
times_to_process = []
##creat empty array 

# Yesterday's observations (06, 12, 18, 21 UTC)
for hour in [6, 12, 18, 21]:
    times_to_process.append({
        'year': AA_yesterday,
        'month': MM_yesterday,
        'day': DD_yesterday,
        'hour': hour,
        'column_name': f't2m_{hour:02d}'
    })
## loop to get hour from [6,12,18,21] so and add it with other keys and values with append methode.

# Today's 00:00 UTC observation (which is named 't2m_24' in your desired output)
times_to_process.append({
    'year': AA_today,
    'month': MM_today,
    'day': DD_today,
    'hour': 0, # This refers to 00:00 UTC
    'column_name': 't2m_24' # This is the target column name
})

logger.info(f"Configured to process {len(times_to_process)} time steps for observations.")

# Loop over each time step defined in times_to_process
for time_info in times_to_process:
    year = time_info['year']
    month = time_info['month']
    day = time_info['day']
    hour = time_info['hour']
    col_name = time_info['column_name']

    # --- REPLACED: File Path Construction using pytap.file_utils ---
    bufr_file_path = build_time_series_filepath(
        BUFR_BASE_DIR, year, month, day, hour, "Synop_", ".bufr"
    )
    logger.debug(f"Attempting to process file: {bufr_file_path}")

    # --- REPLACED: File Existence Check using pytap.file_utils ---
    if not check_file_exists_and_log(bufr_file_path, logger_instance=logger):
        continue  # Skip if the file doesn't exist


    # --- REPLACED: BUFR File Reading and Domain-Specific Processing using pytap.grib_processor ---
    df_hourly = read_and_process_bufr_temperature(bufr_file_path, col_name, logger_instance=logger)
## read_and_process_bufr_temperature it returne df[["stationOrSiteName", target_column_name]] 

    if df_hourly is not None: # Only merge if data was successfully read and processed
        # Merge the data into the stations_df
        stations_df = pd.merge(stations_df, df_hourly, on="stationOrSiteName", how="left")
        logger.info(f"Merged data for {col_name} into the main DataFrame.")
    else:
        logger.warning(f"No data merged for {col_name} due to previous errors or missing file.")


final_df = stations_df

# List of columns you want to select
selected_columns = ["stationOrSiteName",
                    "t2m_00", "t2m_03", "t2m_06", "t2m_09", "t2m_12", "t2m_15", "t2m_18", "t2m_21", "t2m_24"]

# --- REPLACED: Robust Column Selection using pytap.data_utils ---
filtered_df = select_existing_columns(final_df, selected_columns, logger_instance=logger)

# Simplify the final cleaning step. (This line is still redundant, but kept as it was in original)
df_cleaned = filtered_df

# Display the final DataFrame head
logger.info("Final DataFrame head:")
# Using .to_string() for better multi-line logging of DataFrame
logger.info(df_cleaned.head().to_string())
## head() is methode from pandas that show first 5 rows 

# Save the final DataFrame to CSV (Kept as per instruction)
output_filepath = os.path.join(OUTPUT_DIR, f'observations_{AA_today}{MM_today}{DD_today}.csv')
## store the output csv by using operationsystem.path.join 


try:
    df_cleaned.to_csv(output_filepath, index=False)
    ## method from pandas libreries that allow to save data frime as csv file 

    logger.info(f"DataFrame successfully saved to: {output_filepath}")
except Exception as e:
    logger.error(f"Failed to save DataFrame to CSV at {output_filepath}: {e}", exc_info=True)


# --- Run Next Program ---
logger.info(f"Attempting to run next program: 5-traitement_obs_min_max.py")
next_script_path = os.path.join(SCRIPT_DIR, "5-traitement_obs_min_max.py")
try:
        # Pass the shared log file path to the next script
        execute_command(
            [sys.executable, next_script_path, current_log_file_path],
            cwd=SCRIPT_DIR # Ensure the working directory is correct for the next script
        )
        logger.info("Successfully executed 5-traitement_obs_min_max.py.")
except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.exception(f"An error occurred while running 5-traitement_obs_min_max.py: {e}")
        sys.exit(1)

except Exception as e:
    logger.exception(f"An unexpected error occurred in the main script flow: {e}")
    sys.exit(1)

logger.info(f"--- Script '{script_name}' finished. ---") # Clear end message