from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from database import get_food, add_food, get_db_connection
from excel_utils import generate_excel, process_bulk_upload_excel, extract_names_from_excel
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev_key') # Fallback for dev if env missing


# Constants
VALID_ALLERGENS = [
    'Celery', 'Gluten', 'Crustaceans', 'Eggs', 'Fish', 'Lupin', 'Milk', 
    'Molluscs', 'Mustard', 'Nuts', 'Peanuts', 'Sesame', 'Soy', 'Sulphite'
]

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        food_list_text = request.form.get('food_list')
        if not food_list_text:
            flash('Please enter some food names.')
            return redirect(url_for('index'))
        
        food_names = [line.strip().upper() for line in food_list_text.splitlines() if line.strip()]
        
        # Check for missing items
        missing_items = []
        for name in food_names:
            if not get_food(name):
                # Avoid duplicates in missing list
                if name not in missing_items:
                    missing_items.append(name)
        
        if missing_items:
            return render_template('missing_info.html', missing_items=missing_items, original_list=food_names)
        
        # If no missing items, proceed to verification
        # Fetch details for verification
        items_data = []
        for name in food_names:
            item = get_food(name)
            if item:
                # Parse allergens string into list for easy checking in template
                algs_str = item['allergens'] if item['allergens'] else ""
                # Normalize to Title Case just in case
                current_allergens = [a.strip().title() for a in algs_str.split(',') if a.strip()]
                
                items_data.append({
                    'name': item['name'],
                    'calories': item['calories'],
                    'allergens_list': current_allergens
                })
        
        return render_template('verify.html', items=items_data, valid_allergens=VALID_ALLERGENS)
        
    return render_template('index.html')

@app.route('/save_missing', methods=['POST'])
def save_missing():
    # Process the form from missing_info.html
    original_list_str = request.form.get('original_list_json')
    import json
    original_list = json.loads(original_list_str)
    
    for key, value in request.form.items():
        if key.endswith('_calories'):
            item_name = key[:-9].upper() # remove '_calories'
            calories = value
            allergens = request.form.getlist(f"{item_name}_allergens")
            add_food(item_name, calories, allergens)
            
    # Now fetch full data for verification
    items_data = []
    for name in original_list:
        item = get_food(name)
        if item:
            algs_str = item['allergens'] if item['allergens'] else ""
            current_allergens = [a.strip().title() for a in algs_str.split(',') if a.strip()]
            
            items_data.append({
                'name': item['name'],
                'calories': item['calories'],
                'allergens_list': current_allergens
            })

    return render_template('verify.html', items=items_data, valid_allergens=VALID_ALLERGENS)

@app.route('/verify_generate', methods=['POST'])
def verify_generate():
    try:
        item_count = int(request.form.get('item_count', 0))
        food_names = []
        custom_data = {}
        
        for i in range(item_count):
            name = request.form.get(f'name_{i}')
            calories = request.form.get(f'calories_{i}')
            # Allergens are now checkboxes, so getlist
            allergens_list = request.form.getlist(f'allergens_{i}')
            
            if name:
                food_names.append(name)
                custom_data[name] = {
                    'calories': int(calories) if calories else 0,
                    'allergens': allergens_list # List of strings
                }
        
        output_file, _ = generate_excel(food_names, custom_data=custom_data)
        return send_file(output_file, as_attachment=True)
        
    except Exception as e:
        flash(f"Error generating file: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/bulk_upload', methods=['POST'])
def bulk_upload():
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index', tab='upload'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('index', tab='upload'))
        
    if file and file.filename.endswith('.xlsx'):
        # Save temp
        temp_path = os.path.join(os.path.dirname(__file__), 'data', 'temp_upload.xlsx')
        file.save(temp_path)
        
        items = process_bulk_upload_excel(temp_path)
        
        added_count = 0
        duplicates = []
        
        for item in items:
            if get_food(item['name']):
                duplicates.append(item['name'])
            else:
                add_food(item['name'], item['calories'], item['allergens'])
                added_count += 1
                
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        if added_count > 0:
             flash(f"Successfully added {added_count} items.", 'success')
        
        if duplicates:
            flash(f"Skipped {len(duplicates)} duplicate items: {', '.join(duplicates[:5])}...", 'warning')
            
        if added_count == 0 and not duplicates:
             flash("No valid items found in file.", 'warning')

        return redirect(url_for('index', tab='upload'))
    else:
        flash('Invalid file type. Please upload .xlsx', 'error')
        return redirect(url_for('index', tab='upload'))

@app.route('/add_single_item', methods=['POST'])
def add_single_item():
    name = request.form.get('name')
    calories = request.form.get('calories')
    allergens = request.form.getlist('allergens')

    if not name or not calories:
        flash('Name and Calories are required.', 'error')
        return redirect(url_for('index', tab='single'))
    
    clean_name = name.strip().upper()
    
    if get_food(clean_name):
        flash(f'Duplicate: "{clean_name}" already exists in the database.', 'warning')
        return redirect(url_for('index', tab='single'))
    
    add_food(clean_name, calories, allergens)
    flash(f'Success: "{clean_name}" added to database.', 'success')
    return redirect(url_for('index', tab='single'))

@app.route('/extract_names', methods=['POST'])
def extract_names():
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index', tab='extract'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('index', tab='extract'))
        
    if file and file.filename.endswith('.xlsx'):
        temp_path = os.path.join(os.path.dirname(__file__), 'data', 'temp_extract.xlsx')
        file.save(temp_path)
        
        extracted_names = extract_names_from_excel(temp_path)
        
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        if not extracted_names:
             flash("No valid names found in D2:D60.", 'warning')
             return redirect(url_for('index', tab='extract'))
             
        # Render index with extracted names to show in the text area
        # We pass 'extracted_names' which index.html checks
        return render_template('index.html', extracted_names=extracted_names, active_tab='extract')
    else:
        flash('Invalid file type. Please upload .xlsx', 'error')
        return redirect(url_for('index', tab='extract'))

# API Endpoints
@app.route('/api/extract_names', methods=['POST'])
def api_extract_names():
    if 'file' not in request.files:
        return {'error': 'No file part'}, 400
        
    file = request.files['file']
    if file.filename == '':
        return {'error': 'No selected file'}, 400
        
    if file and file.filename.endswith('.xlsx'):
        temp_path = os.path.join(os.path.dirname(__file__), 'data', 'api_temp_extract.xlsx')
        file.save(temp_path)
        
        extracted_names = extract_names_from_excel(temp_path)
        
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return {
            'status': 'success',
            'count': len(extracted_names),
            'names': extracted_names
        }
    return {'error': 'Invalid file type. Please upload .xlsx'}, 400

@app.route('/api/process', methods=['POST'])
def api_process():
    data = request.get_json()
    if not data or 'foods' not in data:
        return {'error': 'Invalid request. "foods" list required.'}, 400
        
    food_names = data['foods']
    food_names = [str(f).strip().upper() for f in food_names if str(f).strip()]
    
    # Check for missing items
    missing_items = []
    for name in food_names:
        if not get_food(name):
            if name not in missing_items:
                missing_items.append(name)
                
    if missing_items:
        return {
            'status': 'missing_data',
            'missing_items': missing_items
        }
        
    # Generate Excel
    output_file, _ = generate_excel(food_names)
    
    # Generate a download URL (assuming server is accessible via IP/domain)
    # Since this is an API, we can return the full path or a relative URL
    download_url = url_for('download_file', filename=os.path.basename(output_file), _external=True)
    
    return {
        'status': 'complete',
        'download_url': download_url
    }

@app.route('/api/add_food', methods=['POST'])
def api_add_food():
    data = request.get_json()
    required_fields = ['name', 'calories']
    if not data or any(k not in data for k in required_fields):
        return {'error': 'Invalid request. "name" and "calories" required.'}, 400
        
    name = data['name'].strip().upper()
    calories = data['calories']
    allergens = data.get('allergens', [])
    
    if get_food(name):
        return {'status': 'error', 'message': f'Food "{name}" already exists.'}, 409
    
    add_food(name, calories, allergens)
    
    return {'status': 'success', 'message': f'Food "{name}" added.'}

@app.route('/api/bulk_upload', methods=['POST'])
def api_bulk_upload():
    if 'file' not in request.files:
        return {'error': 'No file part'}, 400
        
    file = request.files['file']
    if file.filename == '':
        return {'error': 'No selected file'}, 400
        
    if file and file.filename.endswith('.xlsx'):
        temp_path = os.path.join(os.path.dirname(__file__), 'data', 'api_temp_upload.xlsx')
        file.save(temp_path)
        
        items = process_bulk_upload_excel(temp_path)
        
        added = []
        duplicates = []
        
        for item in items:
            if get_food(item['name']):
                duplicates.append(item['name'])
            else:
                add_food(item['name'], item['calories'], item['allergens'])
                added.append(item['name'])
                
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return {
            'status': 'success',
            'added_count': len(added),
            'skipped_count': len(duplicates),
            'added_items': added,
            'skipped_duplicates': duplicates
        }
    return {'error': 'Invalid file type. Please upload .xlsx'}, 400

@app.route('/api/get_details', methods=['POST'])
def api_get_details():
    data = request.get_json()
    if not data or 'foods' not in data:
        return {'error': 'Invalid request. "foods" list required.'}, 400
        
    food_names = data['foods']
    food_names = [str(f).strip().upper() for f in food_names if str(f).strip()]
    
    results = []
    for name in food_names:
        item = get_food(name)
        if item:
            # item is sqlite3.Row or dict-like
            results.append({
                'name': item['name'],
                'calories': item['calories'],
                'allergens': item['allergens'] # String from DB
            })
        else:
            # Should not happen if confirmed before calling this, but handle safety
            results.append({
                'name': name,
                'calories': 0,
                'allergens': ''
            })
            
    return {'status': 'success', 'data': results}

@app.route('/api/generate_custom', methods=['POST'])
def api_generate_custom():
    data = request.get_json()
    if not data or 'foods' not in data:
        return {'error': 'Invalid request. "foods" list of objects required.'}, 400
        
    # data['foods'] is list of {'name':..., 'calories':..., 'allergens':...}
    food_objects = data['foods']
    
    # Prepare inputs for generate_excel
    food_names = [f['name'] for f in food_objects]
    
    # Create valid custom_data dictionary
    custom_data = {}
    for f in food_objects:
        custom_data[f['name']] = {
            'calories': f['calories'],
            'allergens': f['allergens'] # Can be list or comma-separated string
        }
    
    try:
        output_file, _ = generate_excel(food_names, custom_data=custom_data)
        download_url = url_for('download_file', filename=os.path.basename(output_file), _external=True)
        
        return {
            'status': 'complete',
            'download_url': download_url
        }
    except Exception as e:
        print(f"Generate Error: {e}")
        return {'error': str(e)}, 500

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(os.path.dirname(__file__), 'data', 'output', filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return {'error': 'File not found'}, 404

if __name__ == '__main__':
    # Listen on all interfaces
    app.run(host='0.0.0.0', port=5000, debug=True)
