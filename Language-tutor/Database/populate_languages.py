# populate_languages.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "language_learning.db"

def populate_languages():
    """Add some common languages to the database"""
    
    languages = [
        "English",
        "Spanish",
        "French",
        "German",
        "Italian",
        "Portuguese",
        "Russian",
        "Chinese (Mandarin)",
        "Japanese",
        "Korean",
        "Arabic",
        "Hindi"
    ]
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for lang in languages:
            try:
                cursor.execute('INSERT INTO LANGUAGE (language_name) VALUES (?)', (lang,))
                print(f"✓ Added: {lang}")
            except sqlite3.IntegrityError:
                print(f"⊙ Already exists: {lang}")
        
        conn.commit()
        conn.close()
        
        print("\nLanguages populated successfully!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    populate_languages()

