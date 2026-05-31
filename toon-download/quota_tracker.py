import os
import json
from datetime import datetime

LOG_FILE = "api_usage.json"
DAILY_LIMIT = 500

def _get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

def get_remaining_quota():
    """Reads the ledger to calculate how many API calls are left today."""
    today = _get_today_str()
    
    if not os.path.exists(LOG_FILE):
        return DAILY_LIMIT
        
    try:
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
            
        # If the log is from today, subtract what we used. If it's a new day, return 500.
        if data.get("date") == today:
            used = data.get("used", 0)
            return max(0, DAILY_LIMIT - used)
        else:
            return DAILY_LIMIT
    except Exception:
        return DAILY_LIMIT

def log_api_call(calls_made=1):
    """Adds a successful API call to the daily ledger."""
    today = _get_today_str()
    
    # Load existing data
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            data = {"date": today, "used": 0}
    else:
        data = {"date": today, "used": 0}
        
    # Update the tally
    if data.get("date") == today:
        data["used"] += calls_made
    else:
        data = {"date": today, "used": calls_made} # Reset for a new day
        
    # Save back to file
    with open(LOG_FILE, "w") as f:
        json.dump(data, f)