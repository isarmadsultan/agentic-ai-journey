from db import bootstrap
from common import authenticate_user
from user_account_creation import create_user_account
from select_language import select_language
from add_vocabulary import add_vocabulary_flow
from story_creation import story_creation_flow


def user_menu(user_id, user_name):
    while True:
        print("\n=== Language Tutor ===")
        print("1. Select a language")
        print("2. Add vocabulary")
        print("3. Generate a story")
        print("4. Log out")
        print("5. Exit")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            select_language(user_id)
        elif choice == "2":
            add_vocabulary_flow(user_id)
        elif choice == "3":
            story_creation_flow(user_id, user_name)
        elif choice == "4":
            return
        elif choice == "5":
            raise SystemExit(0)
        else:
            print("Please choose a valid option.")


def main():
    bootstrap()

    while True:
        print("\n=== Welcome ===")
        print("1. Create an account")
        print("2. Log in")
        print("3. Exit")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            create_user_account()
        elif choice == "2":
            user_id, user_name = authenticate_user()
            if user_id:
                user_menu(user_id, user_name)
        elif choice == "3":
            break
        else:
            print("Please choose a valid option.")


if __name__ == "__main__":
    main()
