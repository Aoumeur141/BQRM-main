import epygram
import numpy as np
import pandas as pd
import os
from pathlib import Path
from datetime import datetime, timedelta
#from modules.module import run_next_program

# Set source directory (assuming the current directory is the root)
source_dir = "/home/ibousri/AROME_DUST/Projet_Nationale/Sonelgaz/sonelgaz_oper/"

# Allow the user to define custom dates (manually set date or comment/uncomment lines below)
# Example: AA_today, MM_today, DD_today = '2025', '04', '09'  (modify manually)
def prepare_date():
    #today = datetime.now()  # You can comment out the next line to use a fixed date
    today = datetime(2025, 4, 10)  # Example of manually setting a date
    yesterday = today - timedelta(days=1)

    return today.strftime('%Y'), today.strftime('%m'), today.strftime('%d'), \
           yesterday.strftime('%Y'), yesterday.strftime('%m'), yesterday.strftime('%d')

# Get today's and yesterday's dates
AA_today, MM_today, DD_today, AA_yesterday, MM_yesterday, DD_yesterday = prepare_date()

# Set the paths manually
stations_path = os.path.join(source_dir, 'template/station_onm_sud.csv')  # Modify this path if needed
grib_file_path = f"/home/ibousri/AROME_DUST/Projet_Nationale/Sonelgaz/sonelgaz_oper/Arpg/2t_{AA_today}{MM_today}{DD_today}.grib"  # Modify the GRIB file path if needed
output_path = f"/home/ibousri/AROME_DUST/Projet_Nationale/Sonelgaz/sonelgaz_oper/Arpg/station_arpege_{AA_today}{MM_today}{DD_today}.csv"  # Modify the output file path

# Load station data
stations = pd.read_csv(stations_path)

# Read the GRIB file
arp = epygram.formats.resource(grib_file_path, "r")

# Initialize dictionary to store temperature values
results = {'station': stations['station'], 'SID': stations['SID'], 'lon': stations['lon'], 'lat': stations['lat']}
results_48 = {'station': stations['station'], 'SID': stations['SID'], 'lon': stations['lon'], 'lat': stations['lat']}

# List to store temperature values for each station
t2m_all_times = []
t2m_all_times_48 = []
# Manually set the time range (you can modify this as needed)
time_start = 0  # Start of the time range
time_end = 25    # End of the time range
time_step = 1    # Time step (interval)

# Loop over the time range (you can adjust these variables as needed)
for time in range(time_start, time_end, time_step):
    fld = arp.readfield({'shortName': '2t', 'stepRange': time})
    t2m_values = []

    # Extract temperature data for each station
    for index, row in stations.iterrows():
        t2m = fld.extract_point(row['lon'], row['lat']).data - 272.15  # Convert Kelvin to Celsius
        t2m_values.append(t2m)

    # Add temperature values to the results dictionary
    results[f't2m_{time}'] = t2m_values
    t2m_all_times.append(t2m_values)

# Calculate the min and max temperatures for each station
t2m_all_times = np.array(t2m_all_times).T  # Transpose to align with stations
results['t2m_min'] = t2m_all_times.min(axis=1)
results['t2m_max'] = t2m_all_times.max(axis=1)

# Manually set the time range (you can modify this as needed)
time_start_48 = 24 # Start of the time range
time_end_48 = 49    # End of the time range
time_step_48 = 1    # Time step (interval)

# Loop over the time range (you can adjust these variables as needed)
for time_48 in range(time_start_48, time_end_48, time_step_48):
    fld_48 = arp.readfield({'shortName': '2t', 'stepRange': time_48})
    t2m_values_48 = []

    # Extract temperature data for each station
    for index, row in stations.iterrows():
        t2m_48 = fld_48.extract_point(row['lon'], row['lat']).data - 272.15  # Convert Kelvin to Celsius
        t2m_values_48.append(t2m_48)

    # Add temperature values to the results dictionary
    results_48[f't2m_{time}'] = t2m_values_48
    t2m_all_times_48.append(t2m_values_48)

# Calculate the min and max temperatures for each station
t2m_all_times_48 = np.array(t2m_all_times_48).T  # Transpose to align with stations
results_48['t2m_max'] = t2m_all_times_48.max(axis=1)

# Create the final DataFrame with only the required columns
final_table = pd.DataFrame({
    'station': results['station'],
    'SID': results['SID'],
    'lon': results['lon'],
    'lat': results['lat'],
    't2m_min': results['t2m_min'],
    't2m_max': results['t2m_max'],
    't2m_max_48': results_48['t2m_max'],
})

# Save the final table to a CSV file
print("Saving the final table...")
final_table.to_csv(output_path, index=False, encoding="utf-8")

# Change directory back to the script folder and run the next program
#os.chdir(os.path.join(source_dir, "scr"))
#run_next_program("4-traitement_obs.py")