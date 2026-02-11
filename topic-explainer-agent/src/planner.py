#!/usr/bin/env python3
"""
Lecture Planner Agent
---------------------
Uses Ollama (llama3.2:3b) to generate a 1-hour lecture outline for a given topic.
System prompt is loaded from prompts/system_prompt.txt.
Output is saved to outputs/<topic>/outline.txt.
"""

import sys
import os
import json
import urllib.request
import urllib.error


# ─── Configuration ────────────────────────────────────────────────────────────

OLLAMA_URL       = "http://localhost:11434/api/chat"
MODEL_NAME       = "llama3.2:3b"
SYSTEM_PROMPT_FILE = "system_prompt.txt"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_system_prompt(filepath: str) -> str:
    """Load the system prompt from a .txt file."""
    if not os.path.exists(filepath):
        print(f"[ERROR] System prompt file not found: {filepath}")
        sys.exit(1)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read().strip()


def build_user_message(topic: str) -> str:
    """Construct the user message for the given topic."""
    return (
        f"Create a detailed 1-hour lecture outline for the following topic:\n\n"
        f"TOPIC: {topic}\n\n"
        f"Please follow all formatting and structural guidelines in your instructions. "
        f"Make the outline comprehensive, time-boxed, and ready for an instructor to use."
    )


def query_ollama(system_prompt: str, user_message: str) -> str:
    """
    Send a request to the local Ollama API and return the full response text.
    Uses streaming to handle the NDJSON response format.
    """
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        "stream": True,
    }

    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        OLLAMA_URL,
        data    = data,
        headers = {"Content-Type": "application/json"},
        method  = "POST",
    )

    print(f"[INFO] Connecting to Ollama at {OLLAMA_URL} using model '{MODEL_NAME}' ...")

    full_response = []
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            print("[INFO] Generating outline – please wait ...\n")
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        full_response.append(token)
                        print(token, end="", flush=True)
                    # stop_reason is in 'done' key
                    if chunk.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue  # skip malformed lines

    except urllib.error.URLError as e:
        print(f"\n[ERROR] Could not reach Ollama: {e}")
        print("[HINT] Make sure Ollama is running:  ollama serve")
        print(f"[HINT] Make sure the model is pulled: ollama pull {MODEL_NAME}")
        sys.exit(1)

    print()  # newline after streaming output
    return "".join(full_response)


def sanitize_filename(topic: str) -> str:
    """Convert a topic string into a safe filename slug."""
    safe = topic.lower().strip()
    safe = safe.replace(" ", "-")
    # Keep only alphanumeric, dash, underscore
    safe = "".join(c for c in safe if c.isalnum() or c in ("-", "_"))
    return safe or "lecture"


def save_outline(topic: str, content: str) -> str:
    """Save the generated outline to a .txt file and return the filename."""
    slug     = sanitize_filename(topic)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    output_dir = os.path.join(project_root, "outputs", slug)
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, "outline.txt")

    header = (
        f"LECTURE OUTLINE\n"
        f"{'=' * 60}\n"
        f"Topic  : {topic}\n"
        f"Model  : {MODEL_NAME}\n"
        f"{'=' * 60}\n\n"
    )

    with open(filename, "w", encoding="utf-8") as f:
        f.write(header + content)

    return filename


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    # ── Get topic from CLI or interactive prompt ──────────────────────────────
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:]).strip()
    else:
        topic = input("Enter the lecture topic: ").strip()

    if not topic:
        print("[ERROR] No topic provided. Usage: python planner.py <topic>")
        sys.exit(1)

    print(f"\n[INFO] Topic: {topic}")

    # ── Load system prompt ────────────────────────────────────────────────────
    script_dir    = os.path.dirname(os.path.abspath(__file__))
    prompt_path   = os.path.abspath(
        os.path.join(script_dir, "..", "prompts", SYSTEM_PROMPT_FILE)
    )
    system_prompt = load_system_prompt(prompt_path)
    print(f"[INFO] Loaded system prompt from '{prompt_path}'")

    # ── Build user message ────────────────────────────────────────────────────
    user_message = build_user_message(topic)

    # ── Query Ollama ──────────────────────────────────────────────────────────
    outline_text = query_ollama(system_prompt, user_message)

    if not outline_text.strip():
        print("[ERROR] Received empty response from Ollama.")
        sys.exit(1)

    # ── Save output ───────────────────────────────────────────────────────────
    output_file = save_outline(topic, outline_text)
    print(f"\n[SUCCESS] Outline saved to: {output_file}")
    print(f"          Open it with:  cat {output_file}")


if __name__ == "__main__":
    main()
