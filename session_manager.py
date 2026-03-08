import os
import json
import time
from datetime import datetime

# Define the base directory for sessions relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_DIR = os.path.join(BASE_DIR, 'data', 'sessions')

# 1.5 hours in seconds
SESSION_EXPIRY_SECONDS = 1.5 * 60 * 60 

def _ensure_session_dir():
    """Ensure the session directory exists."""
    if not os.path.exists(SESSION_DIR):
        os.makedirs(SESSION_DIR)

def _get_current_date_suffix():
    """Returns the current date in ddmmyyyy format."""
    return datetime.now().strftime("%d%m%Y")

def _cleanup_expired_sessions():
    """Deletes session files older than the expiry time."""
    _ensure_session_dir()
    current_time = time.time()
    
    for filename in os.listdir(SESSION_DIR):
        if not filename.endswith('.json'):
            continue
            
        filepath = os.path.join(SESSION_DIR, filename)
        try:
            # Check file modification time
            mtime = os.path.getmtime(filepath)
            if (current_time - mtime) > SESSION_EXPIRY_SECONDS:
                os.remove(filepath)
        except Exception as e:
            print(f"Error cleaning up session {filename}: {e}")

def save_session(base_name, food_list_text):
    """
    Saves or updates a session.
    Automatically appends -ddmmyyyy to the base name.
    """
    _cleanup_expired_sessions()
    
    if not base_name or not base_name.strip():
        # Default name if none provided
        base_name = f"Session-{int(time.time())}"
    else:
        # Prevent path traversal characters in name
        base_name = base_name.replace("/", "").replace("\\", "").strip()
        
    full_session_name = f"{base_name}-{_get_current_date_suffix()}"
    filename = f"{full_session_name}.json"
    filepath = os.path.join(SESSION_DIR, filename)
    
    data = {
        'session_name': full_session_name,
        'base_name': base_name,
        'created_at': time.time(),
        'food_list': food_list_text,
        'size_bytes': len(food_list_text.encode('utf-8')) if food_list_text else 0
    }
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True, full_session_name
    except Exception as e:
        print(f"Error saving session: {e}")
        return False, str(e)

def load_session(base_name):
    """
    Attempts to load a session by its base name for the current date.
    """
    _cleanup_expired_sessions()
    
    if not base_name:
        return None, "No session name provided."
        
    base_name = base_name.replace("/", "").replace("\\", "").strip()
    full_session_name = f"{base_name}-{_get_current_date_suffix()}"
    filename = f"{full_session_name}.json"
    filepath = os.path.join(SESSION_DIR, filename)
    
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data, None
        except Exception as e:
            return None, f"Error reading session: {e}"
            
    return None, f"Session '{full_session_name}' not found or has expired."

def get_active_sessions():
    """
    Returns a list of dictionaries detailing all active, unexpired sessions.
    Used mainly by the Telegram bot admin command.
    """
    _cleanup_expired_sessions()
    
    sessions = []
    current_time = time.time()
    
    if not os.path.exists(SESSION_DIR):
         return sessions
         
    for filename in os.listdir(SESSION_DIR):
        if not filename.endswith('.json'):
            continue
            
        filepath = os.path.join(SESSION_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Calculate remaining time in minutes
            mtime = os.path.getmtime(filepath)
            age_seconds = current_time - mtime
            remaining_mins = max(0, int((SESSION_EXPIRY_SECONDS - age_seconds) / 60))
            
            sessions.append({
                'session_name': data.get('session_name', 'Unknown'),
                'size_bytes': data.get('size_bytes', 0),
                'remaining_mins': remaining_mins,
                'last_updated': datetime.fromtimestamp(mtime).strftime('%H:%M:%S')
            })
        except Exception:
            pass # Ignore corrupted files
            
    sessions.sort(key=lambda x: x['remaining_mins'])
    return sessions

def get_session_content(full_session_name):
    """
    Attempts to read the food_list directly using the exact session name.
    Useful for bot commands where the exact name is provided.
    """
    _cleanup_expired_sessions()
    
    if not full_session_name:
        return None, "No session name provided."
        
    full_session_name = full_session_name.replace("/", "").replace("\\", "").strip()
    # Strip .json if the user accidentally included it
    if full_session_name.endswith('.json'):
        full_session_name = full_session_name[:-5]
        
    filename = f"{full_session_name}.json"
    filepath = os.path.join(SESSION_DIR, filename)
    
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('food_list', ''), None
        except Exception as e:
            return None, f"Error reading session: {e}"
            
    return None, f"Session '{full_session_name}' not found or has expired."
