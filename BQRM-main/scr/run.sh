export AA=$(date +%Y)
export MM=$(date +%m)
export DD=$(date +%d)
export AAprec=$(date -d "yesterday" +%Y)
export MMprec=$(date -d "yesterday" +%m)
export DDprec=$(date -d "yesterday" +%d)
# export PWD=$(pwd) # This line is not needed for Path.cwd() in Python

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_DIRECTORY="${SCRIPT_DIR}"

# --- ADD THIS LINE ---
cd "${LOCAL_DIRECTORY}"
# ---------------------

python3 "BQRM_ref.py" # Now the script can be called directly, as CWD is set