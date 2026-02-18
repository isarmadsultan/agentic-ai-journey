import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "language_learning.db"

# Connect to database (creates file if it doesn't exist)
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create USER table
cursor.execute('''
CREATE TABLE IF NOT EXISTS USER (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Create LANGUAGE table
cursor.execute('''
CREATE TABLE IF NOT EXISTS LANGUAGE (
    language_id INTEGER PRIMARY KEY AUTOINCREMENT,
    language_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Create USER_LANGUAGE table (junction table)
cursor.execute('''
CREATE TABLE IF NOT EXISTS USER_LANGUAGE (
    user_language_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    language_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    FOREIGN KEY (language_id) REFERENCES LANGUAGE(language_id) ON DELETE CASCADE,
    UNIQUE(user_id, language_id)
)
''')

# Create USER_VOCABULARY table (weak entity)
cursor.execute('''
CREATE TABLE IF NOT EXISTS USER_VOCABULARY (
    vocab_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_language_id INTEGER NOT NULL,
    word TEXT NOT NULL,
    meaning TEXT,
    proficiency TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_language_id) REFERENCES USER_LANGUAGE(user_language_id) ON DELETE CASCADE
)
''')

# Commit changes and close connection
conn.commit()
conn.close()

print("Database created successfully!")
