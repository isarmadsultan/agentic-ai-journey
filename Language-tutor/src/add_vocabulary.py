from db import bootstrap, connect
from common import authenticate_user, prompt_user_language


def add_vocabulary(user_language_id):
    """Add vocabulary words for a user-language"""
    print("\n=== Add Vocabulary ===")
    print("(Press Enter without text to finish)\n")

    conn = connect()
    cursor = conn.cursor()

    count = 0

    while True:
        word = input("Word: ").strip()
        if not word:
            break

        meaning = input("Meaning (optional): ").strip() or None
        proficiency = (
            input("Proficiency [beginner/intermediate/advanced] (optional): ")
            .strip()
            .lower()
            or None
        )

        try:
            cursor.execute(
                """
                INSERT INTO USER_VOCABULARY (user_language_id, word, meaning, proficiency)
                VALUES (?, ?, ?, ?)
                """,
                (user_language_id, word, meaning, proficiency),
            )

            count += 1
            print(f"Added: {word}\n")

        except Exception as exc:
            print(f"Error adding word: {exc}\n")

    conn.commit()
    conn.close()

    print(f"\nTotal words added: {count}")


def add_vocabulary_flow(user_id):
    selected = prompt_user_language(user_id)
    if not selected:
        return False

    user_language_id, language_name, _ = selected
    print(f"\nSelected: {language_name}")
    add_vocabulary(user_language_id)
    return True


def main():
    bootstrap()
    user_id, _ = authenticate_user()

    if not user_id:
        return

    add_vocabulary_flow(user_id)


if __name__ == "__main__":
    main()
