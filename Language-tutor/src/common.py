import hashlib
from getpass import getpass

from db import connect


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate_user():
    print("=== Login ===\n")

    email = input("Email: ").strip()
    password = getpass("Password: ")
    password_hash = hash_password(password)

    try:
        conn = connect()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT user_id, name FROM USER
            WHERE email = ? AND password_hash = ?
            """,
            (email, password_hash),
        )

        result = cursor.fetchone()
        conn.close()

        if result:
            print(f"\nOK. Welcome, {result[1]}!\n")
            return result[0], result[1]

        print("\nInvalid email or password!")
        return None, None

    except Exception as exc:
        print(f"Error: {exc}")
        return None, None


def get_user_languages(user_id):
    try:
        conn = connect()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT ul.user_language_id, l.language_name, l.language_id
            FROM USER_LANGUAGE ul
            JOIN LANGUAGE l ON ul.language_id = l.language_id
            WHERE ul.user_id = ?
            ORDER BY l.language_name
            """,
            (user_id,),
        )

        languages = cursor.fetchall()
        conn.close()
        return languages

    except Exception as exc:
        print(f"Error: {exc}")
        return []


def prompt_user_language(user_id):
    languages = get_user_languages(user_id)

    if not languages:
        print("You have not selected any languages yet.")
        return None

    print("=== Your Languages ===\n")
    for i, (_, lang_name, _) in enumerate(languages, 1):
        print(f"{i}. {lang_name}")

    while True:
        choice = input("\nSelect a language (number) or 'q' to quit: ").strip()
        if choice.lower() == "q":
            return None
        try:
            choice_num = int(choice)
        except ValueError:
            print("Please enter a valid number.")
            continue

        if 1 <= choice_num <= len(languages):
            return languages[choice_num - 1]

        print(f"Please enter a number between 1 and {len(languages)}.")
