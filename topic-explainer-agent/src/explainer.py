#!/usr/bin/env python3
"""
Explainer Agent
---------------
Two-module agent that works with lecture outline files.

MODULE 1 - Generate:
    Reads an outline file and produces a full explanation
    document saved alongside it as explanation.txt.

    Usage:
        python explainer.py generate <outline-file>
        python explainer.py generate outputs\\machine-learning\\outline.txt

MODULE 2 - Revise:
    Reads the existing explanation and a critique (from
    critic.py or a plain .txt file), applies ONLY the critiqued changes,
    and overwrites the same explanation file in-place — no duplicates.

    Usage:
        python explainer.py revise <explanation-file> <critique-file>
        python explainer.py revise outputs\\machine-learning\\explanation.txt critique.txt

System prompts are loaded from:
    prompts/explainer_system_prompt.txt  (Module 1)
    prompts/reviser_system_prompt.txt    (Module 2)
"""

import sys
import os
import json
import urllib.request
import urllib.error
from datetime import datetime


# ─── Configuration ────────────────────────────────────────────────────────────

OLLAMA_URL              = "http://localhost:11434/api/chat"
MODEL_NAME              = "llama3.2:3b"
EXPLAINER_PROMPT_FILE   = "explainer_system_prompt.txt"
REVISER_PROMPT_FILE     = "reviser_system_prompt.txt"


# ─── Shared Utilities ─────────────────────────────────────────────────────────

def load_file(filepath: str, label: str = "file") -> str:
    """Read and return the contents of a text file."""
    if not os.path.exists(filepath):
        print(f"[ERROR] {label} not found: {filepath}")
        sys.exit(1)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        print(f"[ERROR] {label} is empty: {filepath}")
        sys.exit(1)
    print(f"[INFO] Loaded {label}: {filepath}")
    return content


def load_system_prompt(filename: str) -> str:
    """Load a system prompt from the same directory as this script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath   = os.path.abspath(os.path.join(script_dir, "..", "prompts", filename))
    return load_file(filepath, label=f"system prompt ({filename})")


def query_ollama(system_prompt: str, user_message: str, task_label: str = "Generating") -> str:
    """
    Send a streaming request to the local Ollama API.
    Returns the complete response as a single string.
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

    print(f"[INFO] Connecting to Ollama ({MODEL_NAME}) ...")
    print(f"[INFO] {task_label} – please wait ...\n")

    full_response = []
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
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
                    if chunk.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue

    except urllib.error.URLError as e:
        print(f"\n[ERROR] Could not reach Ollama: {e}")
        print("[HINT]  Make sure Ollama is running:  ollama serve")
        print(f"[HINT]  Make sure the model is pulled: ollama pull {MODEL_NAME}")
        sys.exit(1)

    print()  # trailing newline after streamed output
    result = "".join(full_response).strip()

    if not result:
        print("[ERROR] Received an empty response from Ollama.")
        sys.exit(1)

    return result


def derive_explanation_path(outline_path: str) -> str:
    """
    Given an outline filepath, return the corresponding explanation filepath.
    Example: 'machine-learning-outline.txt' -> 'machine-learning-explanation.txt'
    """
    directory = os.path.dirname(os.path.abspath(outline_path))
    basename  = os.path.basename(outline_path)

    if basename == "outline.txt":
        return os.path.join(directory, "explanation.txt")

    if basename.endswith("-outline.txt"):
        slug = basename[: -len("-outline.txt")]
    else:
        # Strip any extension and use the full name as slug
        slug = os.path.splitext(basename)[0]

    return os.path.join(directory, f"{slug}-explanation.txt")


# ─── Module 1: Generate Explanation ──────────────────────────────────────────

def module_generate(outline_path: str) -> None:
    """
    Read an outline file, generate a full lecture explanation via Ollama,
    and save it to '{topic}-explanation.txt' (overwrite if already exists).
    """
    print("\n" + "=" * 60)
    print("  MODULE 1 — GENERATE EXPLANATION")
    print("=" * 60)

    # Load inputs
    outline_text  = load_file(outline_path, label="outline file")
    system_prompt = load_system_prompt(EXPLAINER_PROMPT_FILE)

    # Build user message
    user_message = (
        "Below is a structured lecture outline. "
        "Expand it into a full, detailed lecture explanation document.\n\n"
        "Follow all formatting and content guidelines from your instructions.\n\n"
        "OUTLINE:\n"
        + ("─" * 60) + "\n"
        + outline_text + "\n"
        + ("─" * 60)
    )

    # Query Ollama
    explanation = query_ollama(system_prompt, user_message, task_label="Generating explanation")

    # Derive output path and save (overwrite if exists)
    output_path = derive_explanation_path(outline_path)
    timestamp   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    header = (
        f"LECTURE EXPLANATION\n"
        f"{'=' * 60}\n"
        f"Generated : {timestamp}\n"
        f"Model     : {MODEL_NAME}\n"
        f"Source    : {os.path.basename(outline_path)}\n"
        f"{'=' * 60}\n\n"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + explanation)

    print(f"\n[SUCCESS] Explanation saved to: {output_path}")
    print(f"          View it with: cat \"{output_path}\"")


# ─── Module 2: Revise with Critique ──────────────────────────────────────────

def module_revise(explanation_path: str, critique_path: str) -> None:
    """
    Read the existing explanation and a critique file, apply ONLY the
    critiqued changes via Ollama, and overwrite the same explanation file
    in-place. No version stacking — always one live file.
    """
    print("\n" + "=" * 60)
    print("  MODULE 2 — REVISE WITH CRITIQUE")
    print("=" * 60)

    # Load inputs
    explanation   = load_file(explanation_path, label="explanation file")
    critique      = load_file(critique_path,    label="critique file")
    system_prompt = load_system_prompt(REVISER_PROMPT_FILE)

    # Build user message — send both documents clearly separated
    user_message = (
        "You are given an existing lecture explanation document and a critique.\n"
        "Apply ONLY the changes the critique specifies. "
        "Return the complete revised document.\n\n"
        "CURRENT EXPLANATION DOCUMENT:\n"
        + ("─" * 60) + "\n"
        + explanation + "\n"
        + ("─" * 60) + "\n\n"
        "CRITIQUE TO APPLY:\n"
        + ("─" * 60) + "\n"
        + critique + "\n"
        + ("─" * 60)
    )

    # Query Ollama
    revised = query_ollama(system_prompt, user_message, task_label="Applying critique")

    # Update the timestamp in the header, keep everything else
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Read existing header lines to preserve Source field
    source_name = os.path.basename(explanation_path)
    # Try to extract original source outline name from existing file
    for line in explanation.splitlines():
        if line.startswith("Source    :"):
            source_name = line.split(":", 1)[1].strip()
            break

    updated_header = (
        f"LECTURE EXPLANATION\n"
        f"{'=' * 60}\n"
        f"Revised   : {timestamp}\n"
        f"Model     : {MODEL_NAME}\n"
        f"Source    : {source_name}\n"
        f"Critique  : {os.path.basename(critique_path)}\n"
        f"{'=' * 60}\n\n"
    )

    # Overwrite the SAME file — no copies, no stacking
    with open(explanation_path, "w", encoding="utf-8") as f:
        f.write(updated_header + revised)

    print(f"\n[SUCCESS] Explanation updated in-place: {explanation_path}")
    print(f"          Critique applied from: {critique_path}")
    print(f"          View it with: cat \"{explanation_path}\"")


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

def print_usage() -> None:
    print("""
Explainer Agent — Usage
-----------------------

MODULE 1 — Generate explanation from an outline:
  python explainer.py generate <outline-file>

  Example:
    python explainer.py generate outputs\\machine-learning\\outline.txt

  Output:
    outputs\\machine-learning\\explanation.txt  (created/overwritten)

MODULE 2 — Revise explanation using a critique:
  python explainer.py revise <explanation-file> <critique-file>

  Example:
    python explainer.py revise outputs\\machine-learning\\explanation.txt critique.txt

  Output:
    outputs\\machine-learning\\explanation.txt  (updated IN-PLACE, no duplicates)
""")


def main() -> None:
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    mode = sys.argv[1].lower()

    # ── Module 1: generate ────────────────────────────────────────────────────
    if mode == "generate":
        if len(sys.argv) < 3:
            print("[ERROR] Missing outline file.")
            print("Usage: python explainer.py generate <outline-file>")
            sys.exit(1)
        outline_path = sys.argv[2]
        module_generate(outline_path)

    # ── Module 2: revise ──────────────────────────────────────────────────────
    elif mode == "revise":
        if len(sys.argv) < 4:
            print("[ERROR] Missing arguments.")
            print("Usage: python explainer.py revise <explanation-file> <critique-file>")
            sys.exit(1)
        explanation_path = sys.argv[2]
        critique_path    = sys.argv[3]
        module_revise(explanation_path, critique_path)

    # ── Unknown mode ──────────────────────────────────────────────────────────
    else:
        print(f"[ERROR] Unknown mode: '{mode}'. Choose 'generate' or 'revise'.")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
