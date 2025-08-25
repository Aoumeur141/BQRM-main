#!/bin/bash 
date=$(date -d yesterday +"%Y%m%d")
export AA=$(echo $date | cut -c1-4)
export MM=$(echo $date | cut -c5-6)
export DD=$(echo $date | cut -c7-8)
export DD1=$((10#$DD + 1))

# Get yesterday's date
AA=$(date -d yesterday +"%Y")   # Extract year from yesterday's date
MM=$(date -d yesterday +"%m")   # Extract month from yesterday's date
DD=$(date -d yesterday +"%d")   # Extract day from yesterday's date

# Get tomorrow's date
AA1=$(date +"%Y")   # Extract year from tomorrow's date
MM1=$(date +"%m")   # Extract month from tomorrow's date
DD1=$(date +"%d")   # Extract day from tomorrow's date

echo " traitement de la date du $AA $MM $DD et la journée du $DD1 " 


echo $((date)) 


echo "Lancement du produit Sonelgaz de la journée du $((date))" 

# --- Directory Setup ---
# Get the directory where the script is located, resolving symlinks and getting absolute path.
# This makes the script portable regardless of where it's called from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# LOCAL_DIRECTORY is where this script resides (e.g., /home/aoumeur/onm/synop2bufr)
LOCAL_DIRECTORY="${SCRIPT_DIR}"


python3 "${LOCAL_DIRECTORY}/1-get_arpege.py"