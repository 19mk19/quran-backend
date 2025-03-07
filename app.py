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

# Find verses by letter position
def find_verses_by_letter_position(letter, position, limit=5, exclude_ids=None):
    if exclude_ids is None:
        exclude_ids = []
        
    try:
        verses = load_quran_data()
        random.shuffle(verses)
        
        matching_verses = []
        
        for verse in verses:
            if verse['id'] in exclude_ids:
                continue
                
            verse_text = verse['text_uthmani']
            words = verse_text.split()
            
            surah, verse_number = verse['verse_key'].split(':')
            
            matching_word_indices = []
            
            if position == 'first':
                for i, word in enumerate(words):
                    if word and word.startswith(letter):
                        matching_word_indices.append(i)
            elif position == 'last':
                for i, word in enumerate(words):
                    if word and word.endswith(letter):
                        matching_word_indices.append(i)
            elif position == 'middle':
                for i, word in enumerate(words):
                    if len(word) > 2 and letter in word[1:-1]:
                        matching_word_indices.append(i)
            
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
        return []

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

# Download data at startup
try:
    download_quran_data()
except Exception as e:
    print(f"Error downloading data at startup: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)