# Buffet Tag Generator & Telegram Bot

This project allows users to generate Buffet Tag Excel files for Taj Hotels (specifically formatted for standard 14 allergens). It includes a Web Interface (Flask) and a Telegram Bot for mobile access.

## Features
- **Web Interface**: Manual entry, Bulk Excel Upload, and Single Item Add.
- **Telegram Bot**: Send food lists, handle missing items, add new items (Admin only), and User Allowlist.
- **Excel Generation**: clean, formatted output based on `Mastersheet_TAJ_CAL27.xlsx`.
- **Strict Validation**: Enforces standard item names and valid allergens (e.g., "Soy", "Sesame").

## Prerequisites
- Python 3.8+
- pip

## Installation

1.  **Clone/Download** the repository.
2.  **Install Dependencies**:
### 1. Setup & Run Web App
The project includes a helper script to set up the environment automatically.

```bash
# Make script executable (first time only)
chmod +x run_app.sh

# Run the app
./run_app.sh
```
This script will:
1. Create a virtual environment (`venv`).
2. Install all dependencies.
3. Start the Flask server on `http://localhost:5000`.

### 2. Run Telegram Bot (Optional)
Open a new terminal window:
```bash
# Make script executable
chmod +x run_bot.sh

# Run the bot
./run_bot.sh
```

### Manual Setup (If scripts fail)
If you prefer creating the environment manually:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```
*This script automatically sets up a virtual environment (`buffet_tag_env`) if needed.*

### 3. Run in Background (Persistent)
If you close the terminal, the app usually stops. To keep it running:

```bash
chmod +x start_background.sh stop_background.sh

# Start both App and Bot in background
./start_background.sh

# Stop them later
./stop_background.sh
```

## Configuration
1.  **Environment Variables**:
    - Copy `.env.example` to `.env`:
      ```bash
      cp .env.example .env
      ```
    - Open `.env` and fill in your details:
      ```ini
      FLASK_SECRET_KEY=your_secure_key
      TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
      ADMIN_USER_ID=your_telegram_user_id
      ```

2.  **Dataset**:
    - `database.db` (SQLite) stores food items.
    - `data/Mastersheet_TAJ_CAL27.xlsx` is used as the base for generation.
    - `telegram_bot/allowed_users.json` stores authorized Telegram User IDs.

## Admin Usage (Telegram)
**Admin User ID**: Configured in `.env` (Variable: `ADMIN_USER_ID`)

- `/add_single`: Start a conversation to add a new food item.
- `/add_multiple`: Upload an- `/start`: Start the bot and check permission.
- `/add_user <user_id>`: (Admin only) Authorize a new user.
- `/extract_names`: Extract food names from column D (rows 2-60) of an uploaded Excel file. Values are returned as a text list for easy copying.
- `/cancel`: Cancel the current operation.

## Valid Allergens
The system strictly validates against these 14 allergens:
`Celery`, `Gluten`, `Crustaceans`, `Eggs`, `Fish`, `Lupin`, `Milk`, `Molluscs`, `Mustard`, `Nuts`, `Peanuts`, `Sesame`, `Soy`, `Sulphites`.

## Troubleshooting
- **Bot not responding?** Ensure `app.py` is running first, as the bot relies on the API.
- **"Unauthorized"?** You must be added to the allowlist by the Admin.
- **Excel format issues?** Ensure the template `Mastersheet_TAJ_CAL27.xlsx` is present in `data/` or the root folder as configured.
