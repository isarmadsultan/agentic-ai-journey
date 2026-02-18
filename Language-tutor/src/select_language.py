from db import bootstrap, connect
from common import authenticate_user


def display_available_languages():
    """Display all languages in the database"""
    try:
        conn = connect()
        cursor = conn.cursor()

        cursor.execute("SELECT language_id, language_name FROM LANGUAGE ORDER BY language_name")
        languages = cursor.fetchall()

        conn.close()

        if not languages:
            print("No languages available in the database.")
            return None

        print("=== Available Languages ===\n")
        for lang in languages:
            print(f"{lang[0]}. {lang[1]}")

        return languages

    except Exception as exc:
        print(f"Error retrieving languages: {exc}")
        return None


def select_language(user_id):
    """Let user select a language to learn"""
    languages = display_available_languages()

    if not languages:
        return False

    print("\n" + "=" * 30)

    while True:
        try:
            choice = input(
                "\nEnter the number of the language you want to learn (or 'q' to quit): "
            ).strip()

            if choice.lower() == "q":
                print("Goodbye!")
                return False

            language_id = int(choice)

            # Check if the choice is valid
            valid_ids = [lang[0] for lang in languages]
            if language_id not in valid_ids:
                print(
                    f"Invalid choice. Please select a number between {min(valid_ids)} and {max(valid_ids)}."
                )
                continue

            # Get the language name
            language_name = next(lang[1] for lang in languages if lang[0] == language_id)

            # Add to USER_LANGUAGE table
            conn = connect()
            cursor = conn.cursor()

            # Check if already enrolled
            cursor.execute(
                """
                SELECT user_language_id FROM USER_LANGUAGE
                WHERE user_id = ? AND language_id = ?
                """,
                (user_id, language_id),
            )

            existing = cursor.fetchone()

            if existing:
                print(f"\nYou are already learning {language_name}!")
                print(f"User-Language ID: {existing[0]}")
            else:
                cursor.execute(
                    """
                    INSERT INTO USER_LANGUAGE (user_id, language_id)
                    VALUES (?, ?)
                    """,
                    (user_id, language_id),
                )

                conn.commit()
                user_language_id = cursor.lastrowid

                print(f"\nSuccessfully enrolled in {language_name}!")
                print(f"User-Language ID: {user_language_id}")

            conn.close()
            return True

        except ValueError:
            print("Please enter a valid number.")
        except Exception as exc:
            print(f"Error: {exc}")
            return False


def main():
    # Authenticate user first
    bootstrap()
    user_id, _ = authenticate_user()

    if not user_id:
        return

    # Let user select a language
    select_language(user_id)


if __name__ == "__main__":
    main()
