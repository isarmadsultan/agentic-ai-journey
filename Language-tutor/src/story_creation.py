import os
import random
from datetime import datetime

from db import BASE_DIR, bootstrap, connect
from common import authenticate_user, prompt_user_language


LLM_URL = os.getenv("LLM_URL", "http://127.0.0.1:1235/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "local-model")


def get_user_vocabulary(user_language_id):
    try:
        conn = connect()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT word, meaning, proficiency
            FROM USER_VOCABULARY
            WHERE user_language_id = ?
            ORDER BY created_at
            """,
            (user_language_id,),
        )

        vocabulary = cursor.fetchall()
        conn.close()
        return vocabulary

    except Exception as exc:
        print(f"Error: {exc}")
        return []


def choose_vocabulary(vocabulary):
    if not vocabulary:
        return []

    all_vocab = list(vocabulary)
    proficiency = input(
        "Filter by proficiency? [beginner/intermediate/advanced/none] (default none): "
    ).strip().lower()

    if proficiency and proficiency != "none":
        vocabulary = [v for v in all_vocab if (v[2] or "").lower() == proficiency]
        if not vocabulary:
            print("No words found at that proficiency. Using all words instead.")
            vocabulary = all_vocab
    else:
        vocabulary = all_vocab

    try:
        max_words = input("Max words to include (default 20): ").strip()
        max_words = int(max_words) if max_words else 20
    except ValueError:
        max_words = 20

    if max_words <= 0:
        max_words = 20

    if len(vocabulary) <= max_words:
        return vocabulary

    return random.sample(vocabulary, max_words)


def generate_story_with_llm(language_name, vocabulary, user_name):
    if not vocabulary:
        print("\nYou do not have any vocabulary words yet for this language.")
        print("Please add some vocabulary first.")
        return None

    vocab_list = []
    for word, meaning, _ in vocabulary:
        if meaning:
            vocab_list.append(f"{word} ({meaning})")
        else:
            vocab_list.append(word)

    vocab_text = ", ".join(vocab_list)

    prompt = f"""You are a creative storyteller. Create an engaging short story in {language_name} for a language learner named {user_name}.

IMPORTANT REQUIREMENTS:
1. The story MUST use ALL of these vocabulary words: {vocab_text}
2. The story should be at an appropriate difficulty level for a language learner
3. Make the story interesting, fun, and memorable
4. Keep the story between 150-250 words
5. Use simple sentence structures when possible
6. After the story, provide a brief English summary (2-3 sentences)

Vocabulary to use: {vocab_text}

Please write the story now:"""

    print("\nGenerating your personalized story...")
    print("Please wait...\n")

    try:
        import requests
    except ImportError:
        print("Error: The 'requests' package is not installed.")
        print("Install it with: pip install requests")
        return None

    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": LLM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful language learning assistant that creates engaging stories using specific vocabulary words.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 1000,
            },
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        if response.status_code == 200:
            result = response.json()
            story = result["choices"][0]["message"]["content"]
            return story

        print(f"Error: LLM returned status code {response.status_code}")
        print(f"Response: {response.text}")
        return None

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to LLM at {LLM_URL}")
        print("Please make sure your LLM server is running.")
        return None
    except requests.exceptions.Timeout:
        print("Error: Request timed out. The LLM is taking too long to respond.")
        return None
    except Exception as exc:
        print(f"Error generating story: {exc}")
        return None


def save_story_to_file(story, language_name, user_name):
    stories_dir = BASE_DIR / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = stories_dir / f"{user_name}_{language_name}_{timestamp}.txt"

    try:
        with filename.open("w", encoding="utf-8") as handle:
            handle.write(f"Story for {user_name} - {language_name}\n")
            handle.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            handle.write("=" * 60 + "\n\n")
            handle.write(story)

        print(f"\nStory saved to: {filename}")
        return filename
    except Exception as exc:
        print(f"Error saving story: {exc}")
        return None


def story_creation_flow(user_id, user_name):
    selected = prompt_user_language(user_id)
    if not selected:
        return False

    user_language_id, language_name, _ = selected
    print(f"\nSelected: {language_name}")

    vocabulary = get_user_vocabulary(user_language_id)
    if not vocabulary:
        print(f"\nNo vocabulary found for {language_name}!")
        print("Please add some vocabulary words first.")
        return False

    print(f"\nFound {len(vocabulary)} vocabulary word(s).")
    chosen_vocab = choose_vocabulary(vocabulary)

    print("\nWords that will be used:")
    for word, meaning, _ in chosen_vocab:
        if meaning:
            print(f" - {word} ({meaning})")
        else:
            print(f" - {word}")

    confirm = input("\nGenerate a story using these words? (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return False

    story = generate_story_with_llm(language_name, chosen_vocab, user_name)
    if story:
        print("\n" + "=" * 60)
        print("YOUR STORY")
        print("=" * 60 + "\n")
        print(story)
        print("\n" + "=" * 60)

        save = input("\nSave this story to a file? (y/n): ").strip().lower()
        if save == "y":
            save_story_to_file(story, language_name, user_name)
        return True

    print("\nFailed to generate story.")
    return False


def main():
    print("=" * 60)
    print("PERSONALIZED STORY GENERATOR")
    print("=" * 60)

    bootstrap()
    user_id, user_name = authenticate_user()

    if not user_id:
        return

    story_creation_flow(user_id, user_name)


if __name__ == "__main__":
    main()
