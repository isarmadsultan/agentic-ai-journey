import shutil
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "Database" / "language_learning.db"

LANGUAGES = [
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
    "Hindi",
    "Urdu"
]


def connect():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS USER (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS LANGUAGE (
            language_id INTEGER PRIMARY KEY AUTOINCREMENT,
            language_name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS USER_LANGUAGE (
            user_language_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            language_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES USER(user_id) ON DELETE CASCADE,
            FOREIGN KEY (language_id) REFERENCES LANGUAGE(language_id) ON DELETE CASCADE,
            UNIQUE(user_id, language_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS USER_VOCABULARY (
            vocab_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_language_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            meaning TEXT,
            proficiency TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_language_id) REFERENCES USER_LANGUAGE(user_language_id) ON DELETE CASCADE
        )
        """
    )

    conn.commit()
    conn.close()


def seed_languages():
    conn = connect()
    cursor = conn.cursor()

    for lang in LANGUAGES:
        cursor.execute(
            "INSERT OR IGNORE INTO LANGUAGE (language_name) VALUES (?)",
            (lang,),
        )

    conn.commit()
    conn.close()


def bootstrap():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    legacy_path = BASE_DIR / "language_learning.db"
    if not DB_PATH.exists() and legacy_path.exists():
        shutil.copy2(legacy_path, DB_PATH)

    init_db()
    seed_languages()
