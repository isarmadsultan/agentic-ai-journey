import random
import re
import tkinter as tk
from tkinter import messagebox, ttk

from common import hash_password
from db import bootstrap, connect
from story_creation import generate_story_with_llm, save_story_to_file


EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class LanguageTutorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Language Tutor")
        self.user_id = None
        self.user_name = None
        self.user_languages = []
        self.user_language_map = {}

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=12)

        self.account_tab = ttk.Frame(self.notebook)
        self.login_tab = ttk.Frame(self.notebook)
        self.languages_tab = ttk.Frame(self.notebook)
        self.vocab_tab = ttk.Frame(self.notebook)
        self.story_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.account_tab, text="Create Account")
        self.notebook.add(self.login_tab, text="Login")
        self.notebook.add(self.languages_tab, text="Languages")
        self.notebook.add(self.vocab_tab, text="Vocabulary")
        self.notebook.add(self.story_tab, text="Story")

        self._build_account_tab()
        self._build_login_tab()
        self._build_languages_tab()
        self._build_vocab_tab()
        self._build_story_tab()

        self._set_auth_state(False)

    def _set_auth_state(self, is_logged_in):
        state = "normal" if is_logged_in else "disabled"
        for tab in (self.languages_tab, self.vocab_tab, self.story_tab):
            self.notebook.tab(tab, state=state)

    def _build_account_tab(self):
        frame = self.account_tab

        ttk.Label(frame, text="Name").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.acc_name = ttk.Entry(frame, width=30)
        self.acc_name.grid(row=0, column=1, padx=4, pady=4)

        ttk.Label(frame, text="Email").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.acc_email = ttk.Entry(frame, width=30)
        self.acc_email.grid(row=1, column=1, padx=4, pady=4)

        ttk.Label(frame, text="Password").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        self.acc_password = ttk.Entry(frame, width=30, show="*")
        self.acc_password.grid(row=2, column=1, padx=4, pady=4)

        ttk.Label(frame, text="Confirm Password").grid(
            row=3, column=0, sticky="w", padx=4, pady=4
        )
        self.acc_confirm = ttk.Entry(frame, width=30, show="*")
        self.acc_confirm.grid(row=3, column=1, padx=4, pady=4)

        ttk.Button(frame, text="Create Account", command=self.create_account).grid(
            row=4, column=0, columnspan=2, pady=8
        )

    def _build_login_tab(self):
        frame = self.login_tab

        ttk.Label(frame, text="Email").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.login_email = ttk.Entry(frame, width=30)
        self.login_email.grid(row=0, column=1, padx=4, pady=4)

        ttk.Label(frame, text="Password").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.login_password = ttk.Entry(frame, width=30, show="*")
        self.login_password.grid(row=1, column=1, padx=4, pady=4)

        ttk.Button(frame, text="Log In", command=self.login).grid(
            row=2, column=0, columnspan=2, pady=8
        )

        self.login_status = ttk.Label(frame, text="")
        self.login_status.grid(row=3, column=0, columnspan=2, pady=4)

    def _build_languages_tab(self):
        frame = self.languages_tab

        ttk.Label(frame, text="Available Languages").grid(
            row=0, column=0, sticky="w", padx=4, pady=4
        )
        self.available_list = tk.Listbox(frame, height=10, width=30)
        self.available_list.grid(row=1, column=0, padx=4, pady=4)

        ttk.Label(frame, text="Your Languages").grid(
            row=0, column=1, sticky="w", padx=4, pady=4
        )
        self.user_lang_list = tk.Listbox(frame, height=10, width=30)
        self.user_lang_list.grid(row=1, column=1, padx=4, pady=4)

        ttk.Button(frame, text="Refresh", command=self.refresh_languages).grid(
            row=2, column=0, padx=4, pady=8, sticky="w"
        )
        ttk.Button(frame, text="Enroll Selected", command=self.enroll_language).grid(
            row=2, column=1, padx=4, pady=8, sticky="w"
        )

    def _build_vocab_tab(self):
        frame = self.vocab_tab

        ttk.Label(frame, text="Language").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.vocab_language = ttk.Combobox(frame, values=[], state="readonly", width=27)
        self.vocab_language.grid(row=0, column=1, padx=4, pady=4)
        self.vocab_language.bind("<<ComboboxSelected>>", lambda _e: self.refresh_vocab())

        ttk.Label(frame, text="Word").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.vocab_word = ttk.Entry(frame, width=30)
        self.vocab_word.grid(row=1, column=1, padx=4, pady=4)

        ttk.Label(frame, text="Meaning").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        self.vocab_meaning = ttk.Entry(frame, width=30)
        self.vocab_meaning.grid(row=2, column=1, padx=4, pady=4)

        ttk.Label(frame, text="Proficiency").grid(
            row=3, column=0, sticky="w", padx=4, pady=4
        )
        self.vocab_prof = ttk.Combobox(
            frame, values=["", "beginner", "intermediate", "advanced"], state="readonly"
        )
        self.vocab_prof.grid(row=3, column=1, padx=4, pady=4)

        ttk.Button(frame, text="Add Word", command=self.add_vocab).grid(
            row=4, column=0, columnspan=2, pady=8
        )

        ttk.Label(frame, text="Vocabulary List").grid(
            row=5, column=0, columnspan=2, sticky="w", padx=4, pady=4
        )
        self.vocab_list = tk.Listbox(frame, height=10, width=60)
        self.vocab_list.grid(row=6, column=0, columnspan=2, padx=4, pady=4)

        ttk.Button(frame, text="Refresh", command=self.refresh_vocab).grid(
            row=7, column=0, columnspan=2, pady=6
        )

    def _build_story_tab(self):
        frame = self.story_tab

        ttk.Label(frame, text="Language").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.story_language = ttk.Combobox(frame, values=[], state="readonly", width=27)
        self.story_language.grid(row=0, column=1, padx=4, pady=4)

        ttk.Label(frame, text="Proficiency Filter").grid(
            row=1, column=0, sticky="w", padx=4, pady=4
        )
        self.story_prof = ttk.Combobox(
            frame, values=["any", "beginner", "intermediate", "advanced"], state="readonly"
        )
        self.story_prof.grid(row=1, column=1, padx=4, pady=4)
        self.story_prof.set("any")

        ttk.Label(frame, text="Max Words").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        self.story_max = ttk.Entry(frame, width=10)
        self.story_max.grid(row=2, column=1, sticky="w", padx=4, pady=4)

        ttk.Button(frame, text="Generate Story", command=self.generate_story).grid(
            row=3, column=0, columnspan=2, pady=8
        )

        self.story_text = tk.Text(frame, width=70, height=18)
        self.story_text.grid(row=4, column=0, columnspan=2, padx=4, pady=4)

        ttk.Button(frame, text="Save Story", command=self.save_story).grid(
            row=5, column=0, columnspan=2, pady=6
        )

    def create_account(self):
        name = self.acc_name.get().strip()
        email = self.acc_email.get().strip()
        password = self.acc_password.get()
        confirm = self.acc_confirm.get()

        if not name:
            messagebox.showerror("Error", "Name cannot be empty.")
            return
        if not EMAIL_PATTERN.match(email):
            messagebox.showerror("Error", "Invalid email format.")
            return
        if len(password) < 8:
            messagebox.showerror("Error", "Password must be at least 8 characters.")
            return
        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match.")
            return

        password_hash = hash_password(password)
        try:
            conn = connect()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO USER (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, password_hash),
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Account created. Please log in.")
            self.acc_name.delete(0, tk.END)
            self.acc_email.delete(0, tk.END)
            self.acc_password.delete(0, tk.END)
            self.acc_confirm.delete(0, tk.END)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not create account: {exc}")

    def login(self):
        email = self.login_email.get().strip()
        password = self.login_password.get()

        if not email or not password:
            messagebox.showerror("Error", "Email and password are required.")
            return

        password_hash = hash_password(password)

        try:
            conn = connect()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, name FROM USER WHERE email = ? AND password_hash = ?",
                (email, password_hash),
            )
            result = cursor.fetchone()
            conn.close()

            if not result:
                messagebox.showerror("Error", "Invalid email or password.")
                return

            self.user_id, self.user_name = result
            self.login_status.config(text=f"Logged in as {self.user_name}")
            self._set_auth_state(True)
            self.refresh_languages()
            self.refresh_user_languages()
            messagebox.showinfo("Success", f"Welcome, {self.user_name}!")

        except Exception as exc:
            messagebox.showerror("Error", f"Login failed: {exc}")

    def refresh_languages(self):
        self.available_list.delete(0, tk.END)
        try:
            conn = connect()
            cursor = conn.cursor()
            cursor.execute("SELECT language_id, language_name FROM LANGUAGE ORDER BY language_name")
            languages = cursor.fetchall()
            conn.close()
            for lang_id, lang_name in languages:
                self.available_list.insert(tk.END, f"{lang_id}: {lang_name}")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load languages: {exc}")

    def refresh_user_languages(self):
        self.user_lang_list.delete(0, tk.END)
        if not self.user_id:
            return
        try:
            conn = connect()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ul.user_language_id, l.language_name
                FROM USER_LANGUAGE ul
                JOIN LANGUAGE l ON ul.language_id = l.language_id
                WHERE ul.user_id = ?
                ORDER BY l.language_name
                """,
                (self.user_id,),
            )
            self.user_languages = cursor.fetchall()
            conn.close()

            self.user_language_map = {
                lang_name: user_language_id for user_language_id, lang_name in self.user_languages
            }

            for _, lang_name in self.user_languages:
                self.user_lang_list.insert(tk.END, lang_name)

            languages = [lang for _, lang in self.user_languages]
            self.vocab_language["values"] = languages
            self.story_language["values"] = languages

        except Exception as exc:
            messagebox.showerror("Error", f"Could not load your languages: {exc}")

    def enroll_language(self):
        if not self.user_id:
            messagebox.showerror("Error", "Please log in first.")
            return

        selection = self.available_list.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a language.")
            return

        item = self.available_list.get(selection[0])
        language_id = int(item.split(":")[0])

        try:
            conn = connect()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO USER_LANGUAGE (user_id, language_id) VALUES (?, ?)",
                (self.user_id, language_id),
            )
            conn.commit()
            conn.close()
            self.refresh_user_languages()
        except Exception as exc:
            messagebox.showerror("Error", f"Could not enroll language: {exc}")

    def add_vocab(self):
        if not self.user_id:
            messagebox.showerror("Error", "Please log in first.")
            return

        language = self.vocab_language.get().strip()
        if not language:
            messagebox.showerror("Error", "Please choose a language.")
            return

        word = self.vocab_word.get().strip()
        meaning = self.vocab_meaning.get().strip() or None
        proficiency = self.vocab_prof.get().strip().lower() or None

        if not word:
            messagebox.showerror("Error", "Word cannot be empty.")
            return

        user_language_id = self.user_language_map.get(language)
        if not user_language_id:
            messagebox.showerror("Error", "Selected language is not available.")
            return

        try:
            conn = connect()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO USER_VOCABULARY (user_language_id, word, meaning, proficiency)
                VALUES (?, ?, ?, ?)
                """,
                (user_language_id, word, meaning, proficiency),
            )
            conn.commit()
            conn.close()

            self.vocab_word.delete(0, tk.END)
            self.vocab_meaning.delete(0, tk.END)
            self.vocab_prof.set("")
            self.refresh_vocab()
        except Exception as exc:
            messagebox.showerror("Error", f"Could not add word: {exc}")

    def refresh_vocab(self):
        self.vocab_list.delete(0, tk.END)
        language = self.vocab_language.get().strip()
        if not language:
            return

        user_language_id = self.user_language_map.get(language)
        if not user_language_id:
            return

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
            vocab = cursor.fetchall()
            conn.close()

            for word, meaning, proficiency in vocab:
                label = word
                if meaning:
                    label += f" ({meaning})"
                if proficiency:
                    label += f" [{proficiency}]"
                self.vocab_list.insert(tk.END, label)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load vocabulary: {exc}")

    def generate_story(self):
        language = self.story_language.get().strip()
        if not language:
            messagebox.showerror("Error", "Please choose a language.")
            return

        user_language_id = self.user_language_map.get(language)
        if not user_language_id:
            messagebox.showerror("Error", "Selected language is not available.")
            return

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
            vocab = cursor.fetchall()
            conn.close()
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load vocabulary: {exc}")
            return

        if not vocab:
            messagebox.showerror("Error", "No vocabulary found for this language.")
            return

        prof_filter = self.story_prof.get()
        if prof_filter and prof_filter != "any":
            vocab = [v for v in vocab if (v[2] or "").lower() == prof_filter]
            if not vocab:
                messagebox.showwarning(
                    "Notice", "No words match that proficiency. Using all words."
                )
                vocab = [v for v in vocab]

        max_words = self.story_max.get().strip()
        try:
            max_words = int(max_words) if max_words else 20
        except ValueError:
            max_words = 20

        if max_words <= 0:
            max_words = 20

        if len(vocab) > max_words:
            vocab = random.sample(vocab, max_words)

        story = generate_story_with_llm(language, vocab, self.user_name)
        if not story:
            messagebox.showerror("Error", "Could not generate story.")
            return

        self.story_text.delete("1.0", tk.END)
        self.story_text.insert(tk.END, story)

    def save_story(self):
        story = self.story_text.get("1.0", tk.END).strip()
        language = self.story_language.get().strip()
        if not story:
            messagebox.showerror("Error", "No story to save.")
            return
        if not language:
            messagebox.showerror("Error", "Please choose a language first.")
            return

        filename = save_story_to_file(story, language, self.user_name)
        if filename:
            messagebox.showinfo("Saved", f"Story saved to: {filename}")


def main():
    bootstrap()
    root = tk.Tk()
    root.geometry("700x600")
    LanguageTutorUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
