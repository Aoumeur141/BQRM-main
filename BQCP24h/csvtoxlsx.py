import pandas as pd
from openpyxl.worksheet.table import Table, TableStyleInfo
import numpy as np
import os # Import os for environment variables
import argparse
import sys
import logging

# Import setup_logger from pytaps
from pytaps.logging_utils import setup_logger

# --- Setup Logging for Chain Scripts ---
# Create an ArgumentParser for THIS script
parser = argparse.ArgumentParser(description=f"{os.path.basename(__file__)} script.")
# REMOVED: parser.add_argument('--shared-log-file', type=str,
#                     help='Path to a shared log file for chained scripts. If provided, logs will append to this file.')

# Add positional arguments specific to csvtoxlsx.py
# These must match the order and type of arguments passed from Bulletin.py
parser.add_argument('year', type=str, help='Year (YYYY) for data processing.')
parser.add_argument('month', type=str, help='Month (MM) for data processing.')
parser.add_argument('day', type=str, help='Day (DD) for data processing.')
parser.add_argument('local_directory', type=str, help='Local base directory for file operations.')

# --- Debugging Prints for Argument Parsing ---
# print(f"DEBUG ({os.path.basename(__file__)}): sys.argv at start: {sys.argv}", file=sys.stderr) # Keep for initial debugging, remove later
try:
    # Now parse_args() should work directly as --shared-log-file is no longer expected
    args = parser.parse_args()
    # print(f"DEBUG ({os.path.basename(__file__)}): Parsed args: {args}", file=sys.stderr) # Keep for initial debugging, remove later
    # print(f"DEBUG ({os.path.basename(__file__)}): args.shared_log_file: {args.shared_log_file}", file=sys.stderr) # Keep for initial debugging, remove later
except SystemExit as e:
    print(f"ERROR ({os.path.basename(__file__)}): Argument parsing failed. Exit code: {e.code}", file=sys.stderr)
    sys.exit(e.code)

# --- NEW BLOCK: Get shared log file path from environment variable ---
shared_log_file_from_env = os.environ.get('PYTAPS_SHARED_LOG_FILE')
if shared_log_file_from_env:
    logger_setup_message = f"Shared log file path from environment: {shared_log_file_from_env}"
    # print(f"DEBUG ({os.path.basename(__file__)}): {logger_setup_message}", file=sys.stderr) # Keep for initial debugging, remove later
else:
    logger_setup_message = "PYTAPS_SHARED_LOG_FILE environment variable not set. This script will create its own log file."
    # print(f"WARNING ({os.path.basename(__file__)}): {logger_setup_message}", file=sys.stderr) # Keep for initial debugging, remove later
# --- END NEW BLOCK ---

# Configure the logger using pytaps.logging_utils.setup_logger.
script_name_for_log = os.path.basename(__file__).replace(".py", "") # e.g., "csvtoxlsx"
logger, actual_log_path_from_pytaps = setup_logger(
    script_name=script_name_for_log,
    log_directory_base=os.path.dirname(os.path.abspath(__file__)), # Provide a base dir, though it might be ignored
    log_level=logging.INFO,
    shared_log_file_path=shared_log_file_from_env # Pass the environment variable value!
)
logger.info(logger_setup_message) # Log the message about source of log path

# --- Debugging Prints for Logger Setup ---
# print(f"DEBUG ({os.path.basename(__file__)}): Logger configured. Actual log path from pytaps: {actual_log_path_from_pytaps}", file=sys.stderr) # Keep for initial debugging, remove later
# print(f"DEBUG ({os.path.basename(__file__)}): Root logger handlers: {logging.getLogger().handlers}", file=sys.stderr) # Keep for initial debugging, remove later
# print(f"DEBUG ({os.path.basename(__file__)}): Module logger handlers: {logger.handlers}", file=sys.stderr) # Keep for initial debugging, remove later
# print(f"DEBUG ({os.path.basename(__file__)}): Module logger propagation: {logger.propagate}", file=sys.stderr) # Keep for initial debugging, remove later

# Get values from command-line arguments using args object
AA = args.year
MM = args.month
DD = args.day
LOCAL_DIR = args.local_directory

logger.info(f"Script {os.path.basename(__file__)} started with args: Year={AA}, Month={MM}, Day={DD}, LocalDir={LOCAL_DIR}")

# Step 1: Read the CSV file
csv_file = f'{LOCAL_DIR}/Clim/exported_data_{AA}-{MM}-{DD}.csv'  # Replace with your file path
try:
    df = pd.read_csv(csv_file)
    logger.info(f"Successfully read CSV file: {csv_file}")
except FileNotFoundError:
    logger.critical(f"CSV file not found: {csv_file}. Exiting.")
    sys.exit(1)
except Exception as e:
    logger.critical(f"Error reading CSV file {csv_file}: {e}. Exiting.", exc_info=True)
    sys.exit(1)

# Step 2: Replace empty values with NaN
df.replace("", np.nan, inplace=True)  # Replace empty strings with NaN
logger.debug("Replaced empty strings with NaN in DataFrame.")

# Step 2: Drop the 'meastime' column
if 'meastime' in df.columns:
    df = df.drop(columns=['meastime'])
    logger.debug("Dropped 'meastime' column.")
else:
    logger.warning("Column 'meastime' not found in CSV data. Skipping drop.")

# Step 3: Reshape the data
reshaped_df = df.melt(var_name='Station', value_name='Precipitation')
logger.info("Data reshaped successfully.")

# Step 4: Save to Excel
excel_output_dir = os.path.join(LOCAL_DIR, "Climxlsx")
os.makedirs(excel_output_dir, exist_ok=True) # Ensure directory exists
excel_file = os.path.join(excel_output_dir, f'data_{AA}-{MM}-{DD}.xlsx')
try:
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        reshaped_df.to_excel(writer, sheet_name='Sheet1', index=False)
        
        # Get the workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        
        # Create a table object
        table = Table(displayName="PrecipitationData", ref=worksheet.dimensions)
        
        # Add table style (optional)
        style = TableStyleInfo(showFirstColumn=False, showLastColumn=False,
                                showRowStripes=True, showColumnStripes=True)
        table.tableStyleInfo = style
        
        # Add the table to the worksheet
        worksheet.add_table(table)
    logger.info(f"Data has been reshaped and saved to {excel_file}")
except Exception as e:
    logger.critical(f"Error saving reshaped data to Excel file {excel_file}: {e}. Exiting.", exc_info=True)
    sys.exit(1)

logger.info(f"Script {os.path.basename(__file__)} finished.")
