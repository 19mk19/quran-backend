# quran_backend.py
import json
import os
import random
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

# Create Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


def download_quran_data():
    """Download Quran data if it doesn't exist locally"""
    try:
        if not os.path.exists('quran_data.json'):
            print("Downloading Quran data...")
            # Using the Quran.com API to get the data
            response = requests.get('https://api.quran.com/api/v4/quran/verses/uthmani')
            
            if response.status_code == 200:
                all_verses = response.json()['verses']
                
                # Filter for Juz' 30 (from Surah 78 to 114)
                juz_30_start_verse = 5673  # Approximate starting verse of Juz 30
                juz_30_verses = all_verses[juz_30_start_verse:]
                
                with open('quran_data.json', 'w', encoding='utf-8') as f:
                    json.dump(juz_30_verses, f, ensure_ascii=False, indent=2)
                print(f"Quran data downloaded successfully! Got {len(juz_30_verses)} verses.")
            else:
                print(f"Failed to download Quran data. Status code: {response.status_code}")
                print(f"Response: {response.text}")
        else:
            print("Quran data already exists locally.")
    except Exception as e:
        print(f"Error downloading Quran data: {e}")
        import traceback
        traceback.print_exc()

def load_quran_data():
    """Load the Quran data from the local file"""
    try:
        if not os.path.exists('quran_data.json'):
            download_quran_data()
            
        with open('quran_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Loaded {len(data)} verses from quran_data.json")
            return data
    except Exception as e:
        print(f"Error loading Quran data: {e}")
        import traceback
        traceback.print_exc()
        return []

def find_verses_by_letter_position(letter, position, limit=5, exclude_ids=None):
    """
    Find verses containing the specified Arabic letter in the specified position
    """
    if exclude_ids is None:
        exclude_ids = []
        
    try:
        verses = load_quran_data()
        
        # Shuffle verses for random selection
        random.shuffle(verses)
        
        matching_verses = []
        
        print(f"Searching for letter '{letter}' in position '{position}'")
        
        for verse in verses:
            if verse['id'] in exclude_ids:
                continue  # Skip already displayed verses
                
            # Get the text content of the verse
            verse_text = verse['text_uthmani']
            words = verse_text.split()
            
            # Parse the verse_key to get surah and verse number
            surah, verse_number = verse['verse_key'].split(':')
            
            # Track which words match our criteria
            matching_word_indices = []
            
            if position == 'first':
                # Check if any word starts with the letter
                for i, word in enumerate(words):
                    if word and word.startswith(letter):
                        matching_word_indices.append(i)
            elif position == 'last':
                # Check if any word ends with the letter
                for i, word in enumerate(words):
                    if word and word.endswith(letter):
                        matching_word_indices.append(i)
            elif position == 'middle':
                # Check if the letter appears in the middle of any word (not first or last)
                for i, word in enumerate(words):
                    if len(word) > 2 and letter in word[1:-1]:
                        matching_word_indices.append(i)
            
            if matching_word_indices:
                # Add verse to results with the matching word indices
                matching_verses.append({
                    'id': verse['id'],
                    'surah': int(surah),
                    'verse_number': int(verse_number),
                    'text': verse['text_uthmani'],
                    'matching_word_indices': matching_word_indices,
                    'audio_url': f"https://cdn.islamic.network/quran/audio/128/ar.alafasy/{verse['id']}.mp3"
                })
                
                print(f"Found matching verse: Surah {surah}:{verse_number}")
                
                if len(matching_verses) >= limit:
                    break
        
        print(f"Found {len(matching_verses)} matching verses")
        return matching_verses
    except Exception as e:
        print(f"Error in find_verses_by_letter_position: {e}")
        import traceback
        traceback.print_exc()
        return []

# API Routes
@app.route('/api/search', methods=['GET'])
def search_verses():
    letter = request.args.get('letter', '')
    position = request.args.get('position', 'first')
    limit = int(request.args.get('limit', 5))
    
    print(f"API Request: letter='{letter}', position='{position}', limit={limit}")
    
    if not letter:
        return jsonify({'error': 'Letter parameter is required'}), 400
    
    verses = find_verses_by_letter_position(letter, position, limit)
    return jsonify({'verses': verses})

@app.route('/api/more_verses', methods=['GET'])
def get_more_verses():
    letter = request.args.get('letter', '')
    position = request.args.get('position', 'first')
    limit = int(request.args.get('limit', 5))
    exclude_ids = request.args.get('exclude_ids', '')
    
    print(f"API Request for more verses: letter='{letter}', position='{position}', limit={limit}")
    
    if not letter:
        return jsonify({'error': 'Letter parameter is required'}), 400
    
    # Convert exclude_ids to a list of integers if provided
    exclude_list = []
    if exclude_ids:
        try:
            exclude_list = [int(id) for id in exclude_ids.split(',')]
        except ValueError:
            pass
    
    verses = find_verses_by_letter_position(letter, position, limit, exclude_list)
    return jsonify({'verses': verses})

@app.route('/api/letters', methods=['GET'])
def get_arabic_letters():
    # Arabic alphabet
    arabic_letters = ['ا', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ذ', 'ر', 'ز', 'س', 
                     'ش', 'ص', 'ض', 'ط', 'ظ', 'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 
                     'ن', 'ه', 'و', 'ي']
    return jsonify({'letters': arabic_letters})

def start_server():
    # First make sure we have the data
    download_quran_data()
    # Then run the app
    app.run(debug=True, port=5000)