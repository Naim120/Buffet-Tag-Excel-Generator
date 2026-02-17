import logging
import requests
import os
import json
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, constants
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from dotenv import load_dotenv

load_dotenv()

import sys

# Add parent directory to sys.path to import excel_utils
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from excel_utils import extract_names_from_excel

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Constants
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE_URL = "http://localhost:5000/api"
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
ALLOWED_USERS_FILE = os.path.join(os.path.dirname(__file__), 'allowed_users.json')


VALID_ALLERGENS = [
    'Celery', 'Gluten', 'Crustaceans', 'Eggs', 'Fish', 'Lupin', 'Milk', 
    'Molluscs', 'Mustard', 'Nuts', 'Peanuts', 'Sesame', 'Soy', 'Sulphite'
]
VALID_ALLERGENS_LOWER = {a.lower(): a for a in VALID_ALLERGENS}

# Conversation States
# Missing Item Flow
ASK_CALORIES, ASK_ALLERGENS, VERIFY_ALLERGENS, EXTRACT_UPLOAD = range(4) # New state

# Add Single Item Flow (Admin)
ADD_SINGLE_NAME = 3
ADD_SINGLE_CALORIES = 4
ADD_SINGLE_ALLERGENS = 5

# Add Multiple items Flow (Admin)
ADD_MULTIPLE_FILE = 6

# Global dictionary to store temporary user data
user_data_store = {}

# --- Helper Functions ---

def validate_allergens(text):
    """
    Parses and validates a comma-separated string of allergens.
    Returns: (valid_list, error_message)
    """
    if not text or text.lower() == 'none':
        return [], None
    
    inputs = [x.strip() for x in text.split(',') if x.strip()]
    valid_list = []
    invalid_inputs = []
    
    for item in inputs:
        # Check against valid list (case-insensitive)
        if item.lower() in VALID_ALLERGENS_LOWER:
            valid_list.append(VALID_ALLERGENS_LOWER[item.lower()])
        else:
            invalid_inputs.append(item)
            
    if invalid_inputs:
        error_msg = (
            f"Invalid allergen(s): **{', '.join(invalid_inputs)}**.\n"
            f"Valid options are:\n`{', '.join(VALID_ALLERGENS)}`\n"
            "Please try again."
        )
        return None, error_msg
    
    return valid_list, None

# --- User Management ---

def load_allowed_users():
    if not os.path.exists(ALLOWED_USERS_FILE):
        return []
    try:
        with open(ALLOWED_USERS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_allowed_users(users):
    with open(ALLOWED_USERS_FILE, 'w') as f:
        json.dump(users, f)

def is_allowed(user_id):
    if user_id == ADMIN_USER_ID:
        return True
    allowed = load_allowed_users()
    return user_id in allowed

async def add_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Unauthorized.")
        return
        
    try:
        # Command: /add_user 123456789
        new_user_id = int(context.args[0])
        allowed = load_allowed_users()
        if new_user_id not in allowed:
            allowed.append(new_user_id)
            save_allowed_users(allowed)
            await update.message.reply_text(f"User {new_user_id} added just now.")
        else:
            await update.message.reply_text(f"User {new_user_id} is already allowed.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /add_user <user_id>")

# --- Bot Commands ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_allowed(user_id):
        await update.message.reply_text("Unauthorized access. Contact admin.")
        return

    msg = (
        "Welcome to the Buffet Tag Bot!\n\n"
        "Send me a list of food items (one per line) to generate tags.\n"
        "If an item is missing, I'll ask you for details."
    )
    if user_id == ADMIN_USER_ID:
        msg += "\n\nAdmin Commands:\n/add_single - Add new item\n/add_multiple - Bulk upload\n/add_user <id> - Allow user"
    
    await update.message.reply_text(msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
        
    await update.message.reply_text(
        "Usage:\n"
        "1. Send a list of food names.\n"
        "2. I will check if they exist in the database.\n"
        "3. If all exist, I'll send you the Excel file.\n"
        "4. If any are missing, I'll guide you to add them.\n\n"
        "Valid Allergens:\n" + ", ".join(VALID_ALLERGENS)
    )

async def show_verification_list(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, food_list):
    """
    Fetches details from API and shows verification message.
    """
    try:
        response = requests.post(f"{API_BASE_URL}/get_details", json={'foods': food_list})
        data = response.json()
        
        if response.status_code == 200 and data.get('status') == 'success':
            items = data['data']
            # Store full objects in user_data for editing
            # We use a dict for user session: {'verification_items': [obj1, obj2...]}
            user_data_store[user_id]['verification_items'] = items
            
            # Format message
            msg_lines = ["**Review Allergens** (Session only):"]
            for idx, item in enumerate(items):
                # item['allergens'] is string from DB usually
                algs = item['allergens']
                if not algs:
                    algs = "None"
                msg_lines.append(f"{idx+1}. {item['name']} [{algs}]")
                
            msg_lines.append("\nCommands:")
            msg_lines.append("• `change <N> <New Allergens>` (e.g., `change 1 Soy, Gluten`)")
            msg_lines.append("• `ok` or `generate` to Finish")
            
            await update.message.reply_text("\n".join(msg_lines), parse_mode='Markdown')
            return VERIFY_ALLERGENS
        else:
            await update.message.reply_text("Error fetching details for verification.")
            return ConversationHandler.END
    except Exception as e:
        logging.error(f"Verification Error: {e}")
        await update.message.reply_text(f"Error: {e}")
        return ConversationHandler.END

async def verify_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data_store or 'verification_items' not in user_data_store[user_id]:
        await update.message.reply_text("Session expired.")
        return ConversationHandler.END
        
    text = update.message.text.strip()
    items = user_data_store[user_id]['verification_items']
    
    if text.lower() in ['ok', 'generate', 'yes', 'done']:
        # Finalize
        await update.message.reply_text("Generating file...")
        try:
            # Send custom data to generate API
            payload = {'foods': items}
            response = requests.post(f"{API_BASE_URL}/generate_custom", json=payload)
            data = response.json()
            
            if response.status_code == 200 and data.get('status') == 'complete':
                download_url = data['download_url'].replace('0.0.0.0', 'localhost')
                file_res = requests.get(download_url)
                if file_res.status_code == 200:
                    await update.message.reply_document(document=file_res.content, filename=os.path.basename(download_url))
                else:
                    await update.message.reply_text("Error downloading file.")
            else:
                await update.message.reply_text(f"Error generating file: {data.get('error')}")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")
            
        del user_data_store[user_id]
        return ConversationHandler.END
        
    elif text.lower().startswith('change '):
        # Parse change command
        parts = text.split(' ', 2)
        if len(parts) < 3:
            await update.message.reply_text("Usage: `change <number> <allergens>`")
            return VERIFY_ALLERGENS
            
        try:
            idx = int(parts[1]) - 1
            new_allergens_text = parts[2]
            
            if idx < 0 or idx >= len(items):
                await update.message.reply_text("Invalid item number.")
                return VERIFY_ALLERGENS
                
            # Validate allergens
            valid_list, error_msg = validate_allergens(new_allergens_text)
            if error_msg:
                await update.message.reply_text(error_msg, parse_mode='Markdown')
                return VERIFY_ALLERGENS
                
            # Update local session data
            items[idx]['allergens'] = ", ".join(valid_list)
            
            await update.message.reply_text(f"Updated **{items[idx]['name']}** to: [{items[idx]['allergens']}]\nType `ok` to finish or modify another.", parse_mode='Markdown')
            return VERIFY_ALLERGENS
            
        except ValueError:
             await update.message.reply_text("Invalid number.")
             return VERIFY_ALLERGENS
    else:
        await update.message.reply_text("Unknown command. Type `ok` to generate or `change <n> <allergens>` to edit.")
        return VERIFY_ALLERGENS

async def extract_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the extraction process."""
    user = update.effective_user
    # No admin check needed as requested
    
    await update.message.reply_text(
        "Please upload the Excel file you want to extract food names from (Column D, Rows 2-60).\n"
        "/cancel - Cancel the current operation\n"
        "/extract_names - Extract food names from an Excel file (D2:D60)"
    )
    return EXTRACT_UPLOAD

async def handle_extract_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the Excel file upload for extraction."""
    user = update.effective_user
    document = update.message.document
    
    if not document.file_name.endswith('.xlsx'):
        await update.message.reply_text("Please upload a valid .xlsx file.")
        return EXTRACT_UPLOAD
        
    file = await document.get_file()
    temp_path = f"temp_extract_{user.id}.xlsx"
    await file.download_to_drive(temp_path)
    
    try:
        names = extract_names_from_excel(temp_path)
        
        if names:
            # Wrap whole list in triple backticks for one-click copy
            names_text = "\n".join(names)
            response_text = f"Extracted Names:\n\n```\n{names_text}\n```"
            # Split if too long (Telegram limit 4096)
            if len(response_text) > 4000:
                 # Simple chunking
                 chunks = [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]
                 for chunk in chunks:
                     await update.message.reply_text(chunk, parse_mode=constants.ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(response_text, parse_mode=constants.ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("No valid food names found in D2:D60.")
            
    except Exception as e:
        await update.message.reply_text(f"Error processing file: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_data_store:
        del user_data_store[user_id]
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

# --- Normal User Flow (List Processing) ---

async def process_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("Unauthorized access.")
        return

    text = update.message.text
    food_list = [line.strip() for line in text.splitlines() if line.strip()]
    
    if not food_list:
        await update.message.reply_text("Please send a valid list of food items.")
        return

    try:
        response = requests.post(f"{API_BASE_URL}/process", json={'foods': food_list})
        data = response.json()
        
        if response.status_code == 200:
            if data.get('status') == 'complete':
                # Instead of downloading immediately, go to Verification
                if user_id := update.effective_user.id:
                    user_data_store[user_id] = {'food_list': food_list} # Init store if not exists
                    return await show_verification_list(update, context, user_id, food_list)

            elif data.get('status') == 'missing_data':
                missing = data['missing_items']
                user_id = update.effective_user.id
                user_data_store[user_id] = {
                    'missing_items': missing,
                    'current_index': 0,
                    'food_list': food_list
                }
                
                first_missing = missing[0]
                await update.message.reply_text(
                    f"I found some missing items.\n\n"
                    f"1. **{first_missing}**\n"
                    f"Please enter the **Calories** (number) for {first_missing}:",
                    parse_mode='Markdown'
                )
                return ASK_CALORIES
        else:
             await update.message.reply_text(f"API Error: {data}")

    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("An error occurred.")
        return ConversationHandler.END

async def ask_calories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Authorization check implicit as state requires prior step
    user_id = update.effective_user.id
    if user_id not in user_data_store:
        await update.message.reply_text("Session expired. Please send list again.")
        return ConversationHandler.END
        
    calories_text = update.message.text
    if not calories_text.isdigit():
        await update.message.reply_text("Please enter a valid number.")
        return ASK_CALORIES

    user_data_store[user_id]['current_calories'] = int(calories_text)
    await update.message.reply_text("Enter **Allergens** (comma separated) or type 'None':", parse_mode='Markdown')
    return ASK_ALLERGENS

async def ask_allergens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data_store = user_data_store.get(user_id)
    if not data_store:
        return ConversationHandler.END
        
    allergens_text = update.message.text
    
    # Validate Allergens
    valid_allergens, error_msg = validate_allergens(allergens_text)
    if error_msg:
        await update.message.reply_text(error_msg, parse_mode='Markdown')
        return ASK_ALLERGENS
        
    current_idx = data_store['current_index']
    current_food = data_store['missing_items'][current_idx]
    
    # Add to DB
    payload = {'name': current_food, 'calories': data_store['current_calories'], 'allergens': valid_allergens}
    try:
        requests.post(f"{API_BASE_URL}/add_food", json=payload)
    except Exception as e:
        logging.error(f"Add Error: {e}")

    data_store['current_index'] += 1
    
    if data_store['current_index'] < len(data_store['missing_items']):
        next_food = data_store['missing_items'][data_store['current_index']]
        await update.message.reply_text(f"Next item: **{next_food}**\nEnter **Calories**:", parse_mode='Markdown')
        return ASK_CALORIES
    else:
        await update.message.reply_text("All items added! Proceeding to verification...")
        # Get Original List and go to Verification
        original_list = data_store['food_list']
        # User store kept for verification items
        return await show_verification_list(update, context, user_id, original_list)

# --- Admin Flow: Add Single Item ---

async def add_single_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Unauthorized.")
        return ConversationHandler.END
    await update.message.reply_text("Enter the **Food Name** to add:", parse_mode='Markdown')
    return ADD_SINGLE_NAME

async def add_single_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_store[update.effective_user.id] = {'new_food_name': update.message.text.strip()}
    await update.message.reply_text("Enter **Calories**:", parse_mode='Markdown')
    return ADD_SINGLE_CALORIES

async def add_single_calories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.isdigit():
        await update.message.reply_text("Invalid number. Enter **Calories**:", parse_mode='Markdown')
        return ADD_SINGLE_CALORIES
    
    user_data_store[update.effective_user.id]['new_food_calories'] = int(text)
    await update.message.reply_text("Enter **Allergens** (comma separated) or 'None':", parse_mode='Markdown')
    return ADD_SINGLE_ALLERGENS

async def add_single_allergens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data_store.get(user_id)
    if not data:
        return ConversationHandler.END
        
    text = update.message.text
    
    # Validate Allergens
    valid_allergens, error_msg = validate_allergens(text)
    if error_msg:
        await update.message.reply_text(error_msg, parse_mode='Markdown')
        return ADD_SINGLE_ALLERGENS
    
    payload = {
        'name': data['new_food_name'],
        'calories': data['new_food_calories'],
        'allergens': valid_allergens
    }
    
    try:
        res = requests.post(f"{API_BASE_URL}/add_food", json=payload)
        if res.status_code == 200:
            await update.message.reply_text(f"Success! Added **{data['new_food_name']}**.", parse_mode='Markdown')
        elif res.status_code == 409:
            await update.message.reply_text(f"Duplicate! **{data['new_food_name']}** already exists.", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"Error: API returned {res.status_code}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
        
    if user_id in user_data_store:
        del user_data_store[user_id]
    return ConversationHandler.END

# --- Admin Flow: Add Multiple (File) ---

async def add_multiple_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Unauthorized.")
        return ConversationHandler.END
    await update.message.reply_text("Please upload the **.xlsx file** for bulk upload:", parse_mode='Markdown')
    return ADD_MULTIPLE_FILE

async def add_multiple_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document or not document.file_name.endswith('.xlsx'):
        await update.message.reply_text("Please upload a valid .xlsx file.")
        return ADD_MULTIPLE_FILE
        
    file = await document.get_file()
    file_path = f"temp_{document.file_name}"
    await file.download_to_drive(file_path)
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (document.file_name, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            res = requests.post(f"{API_BASE_URL}/bulk_upload", files=files)
            
        if res.status_code == 200:
            data = res.json()
            msg = f"Done!\nAdded: {data['added_count']}\nSkipped: {data['skipped_count']}"
            if data['skipped_duplicates']:
                msg += f"\nDuplicates: {', '.join(data['skipped_duplicates'][:5])}..."
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text(f"Upload failed: {res.text}")
            
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            
    return ConversationHandler.END

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    # 1. Normal List Processing Handler
    list_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & (~filters.COMMAND), process_list)],
        states={
            ASK_CALORIES: [MessageHandler(filters.TEXT & (~filters.COMMAND), ask_calories)],
            ASK_ALLERGENS: [MessageHandler(filters.TEXT & (~filters.COMMAND), ask_allergens)],
            VERIFY_ALLERGENS: [MessageHandler(filters.TEXT & (~filters.COMMAND), verify_loop)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # 2. Admin Add Single Handler
    add_single_conv = ConversationHandler(
        entry_points=[CommandHandler("add_single", add_single_start)],
        states={
            ADD_SINGLE_NAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_single_name)],
            ADD_SINGLE_CALORIES: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_single_calories)],
            ADD_SINGLE_ALLERGENS: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_single_allergens)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # 3. Admin Add Multiple Handler
    add_multiple_conv = ConversationHandler(
        entry_points=[CommandHandler("add_multiple", add_multiple_start)],
        states={
            ADD_MULTIPLE_FILE: [MessageHandler(filters.Document.ALL, add_multiple_file)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('add_user', add_user_command))
    
    # Register conversation handlers
    # Order matters? Specific commands usually first.
    application.add_handler(add_single_conv)
    application.add_handler(add_multiple_conv)
    # Handler for Extraction
    extract_conv = ConversationHandler(
        entry_points=[CommandHandler("extract_names", extract_command)],
        states={
            EXTRACT_UPLOAD: [MessageHandler(filters.Document.FileExtension("xlsx"), handle_extract_upload)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(list_conv)
    application.add_handler(extract_conv) # Catches text, so put last
    
    print("Bot is running...")
    application.run_polling()
