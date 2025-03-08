import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import requests
import random

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Download and load Quran data
def download_quran_data():
    """Download Quran data if it doesn't exist locally"""
    if not os.path.exists('quran_data.json'):
        print("Downloading Quran data...")
        response = requests.get('https://api.quran.com/api/v4/quran/verses/uthmani')
        
        if response.status_code == 200:
            all_verses = response.json()['verses']
            juz_30_start_verse = 5673  # Approximate starting verse of Juz 30
            juz_30_verses = all_verses[juz_30_start_verse:]
            
            with open('quran_data.json', 'w', encoding='utf-8') as f:
                json.dump(juz_30_verses, f, ensure_ascii=False, indent=2)
        else:
            print(f"Failed to download Quran data: {response.status_code}")
    else:
        print("Quran data exists")

def load_quran_data():
    if not os.path.exists('quran_data.json'):
        download_quran_data()
    
    try:
        with open('quran_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        # Fallback: download and try again
        download_quran_data()
        with open('quran_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)

def find_verses_by_letter_position(letter, position, limit=5, exclude_ids=None):
    if exclude_ids is None:
        exclude_ids = []
        
    try:
        verses = load_quran_data()
        random.shuffle(verses)
        
        matching_verses = []
        
        # Print the letter we're searching for to help with debugging
        print(f"Searching for letter '{letter}' in position '{position}'")
        # Get the Unicode code point to verify what we're searching for
        print(f"Letter Unicode: {ord(letter)}")
        
        for verse in verses:
            if verse['id'] in exclude_ids:
                continue
                
            verse_text = verse['text_uthmani']
            
            # For debugging specific surahs
            surah, verse_number = verse['verse_key'].split(':')
            if surah == '85' and int(verse_number) <= 3:  # Debug Surah Buruj for ج and د
                print(f"Checking Surah 85:{verse_number}: {verse_text}")
                
            # Split by spaces while keeping diacritics
            words = verse_text.split()
            
            matching_word_indices = []
            
            if position == 'first':
                for i, word in enumerate(words):
                    if word and word.startswith(letter):
                        matching_word_indices.append(i)
                        print(f"Found word starting with {letter}: {word}")
            elif position == 'last':
                for i, word in enumerate(words):
                    if not word or len(word) == 0:
                        continue
                        
                    # Get the actual last character (ignoring diacritics)
                    last_char = None
                    for char in reversed(word):
                        # Check if the character is a letter (not a diacritic)
                        if not is_diacritic(char):
                            last_char = char
                            break
                    
                    if last_char == letter:
                        matching_word_indices.append(i)
                        print(f"Found word ending with {letter}: {word}")
            elif position == 'middle':
                for i, word in enumerate(words):
                    if len(word) <= 2:
                        continue
                        
                    # Get word without diacritics
                    clean_word = remove_diacritics(word)
                    
                    # Check if letter is in the middle (not first or last)
                    if len(clean_word) > 2 and letter in clean_word[1:-1]:
                        matching_word_indices.append(i)
                        print(f"Found word with {letter} in middle: {word}")
            
            if matching_word_indices:
                matching_verses.append({
                    'id': verse['id'],
                    'surah': int(surah),
                    'verse_number': int(verse_number),
                    'text': verse['text_uthmani'],
                    'matching_word_indices': matching_word_indices,
                    'audio_url': f"https://cdn.islamic.network/quran/audio/128/ar.alafasy/{verse['id']}.mp3"
                })
                
                if len(matching_verses) >= limit:
                    break
        
        return matching_verses
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []

# Helper function to determine if a character is a diacritic
def is_diacritic(char):
    diacritics = ['َ', 'ً', 'ُ', 'ٌ', 'ِ', 'ٍ', 'ّ', 'ْ', 'ـ', '٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩']
    return char in diacritics or ord(char) in range(0x064B, 0x065F + 1)

# Helper function to remove diacritics from text
def remove_diacritics(text):
    return ''.join([c for c in text if not is_diacritic(c)])


# API routes
@app.route('/')
def index():
    return jsonify({"message": "Quran Verse Finder API is running"})

@app.route('/api/letters', methods=['GET'])
def get_arabic_letters():
    arabic_letters = ['ا', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ذ', 'ر', 'ز', 'س', 
                     'ش', 'ص', 'ض', 'ط', 'ظ', 'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 
                     'ن', 'ه', 'و', 'ي']
    return jsonify({'letters': arabic_letters})

@app.route('/api/search', methods=['GET'])
def search_verses():
    letter = request.args.get('letter', '')
    position = request.args.get('position', 'first')
    limit = int(request.args.get('limit', 5))
    
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
    
    if not letter:
        return jsonify({'error': 'Letter parameter is required'}), 400
    
    exclude_list = []
    if exclude_ids:
        try:
            exclude_list = [int(id) for id in exclude_ids.split(',')]
        except ValueError:
            pass
    
    verses = find_verses_by_letter_position(letter, position, limit, exclude_list)
    return jsonify({'verses': verses})

# Add this to your app.py file, after your routes
@app.route('/api/test_surah_buruj', methods=['GET'])
def test_surah_buruj():
    """Test endpoint to check Surah Buruj specifically"""
    verses = load_quran_data()
    
    buruj_verses = []
    for verse in verses:
        surah, verse_number = verse['verse_key'].split(':')
        if surah == '85' and int(verse_number) <= 5:
            # Check for words ending with ج and د
            words = verse['text_uthmani'].split()
            ending_with_jim = []
            ending_with_dal = []
            
            for word in words:
                if word:
                    # Clean and check the word
                    last_char = None
                    for char in reversed(word):
                        if not is_diacritic(char):
                            last_char = char
                            break
                    
                    if last_char == 'ج':
                        ending_with_jim.append(word)
                    elif last_char == 'د':
                        ending_with_dal.append(word)
            
            buruj_verses.append({
                'verse_key': verse['verse_key'],
                'text': verse['text_uthmani'],
                'ending_with_jim': ending_with_jim,
                'ending_with_dal': ending_with_dal
            })
    
    return jsonify(buruj_verses)

# Download data at startup
try:
    download_quran_data()
except Exception as e:
    print(f"Error downloading data at startup: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)