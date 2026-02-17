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
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

### 1. Web API (Flask Server)
The Flask server handles the core logic and database interactions.

```bash
python3 app.py
```
*Runs on `http://localhost:5000` by default.*

### 2. Telegram Bot
The bot authenticates users and communicates with the Flask API.

```bash
chmod +x run_bot.sh
./run_bot.sh
```
*This script automatically sets up a virtual environment (`buffet_tag_env`) if needed.*

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
