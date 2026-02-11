#!/usr/bin/env python3
"""
Critic Agent
------------
Analyzes a lecture explanation file, generates a critique, sends it to the
explainer for revision, then re-reviews the result. Loops until all critiques
are satisfied OR the max iteration cap is hit.

The feedback loop:
  1. Read explanation file
  2. Generate critique via Ollama
  3. If APPROVED  → done, exit cleanly
  4. If issues    → call explainer.py revise (Module 2)
  5. Re-read updated explanation → go to step 2
  6. Stop after MAX_ITERATIONS regardless

Usage:
    python critic.py <explanation-file>

    Example:
        python critic.py outputs\\machine-learning\\explanation.txt

Files expected:
    prompts/critic_system_prompt.txt  - system prompt for critique generation
    src/explainer.py                  - used to apply revisions (Module 2)

The critique is written to a temp file 'active_critique.txt' (overwritten each
round). No historical critique files pile up.
"""

import sys
import os
import json
import subprocess
import urllib.request
import urllib.error
from datetime import datetime


# ─── Configuration ────────────────────────────────────────────────────────────

OLLAMA_URL           = "http://localhost:11434/api/chat"
MODEL_NAME           = "llama3.2:3b"
CRITIC_PROMPT_FILE   = "critic_system_prompt.txt"
ACTIVE_CRITIQUE_FILE = "active_critique.txt"   # single reused file, no stacking
MAX_ITERATIONS       = 4                        # safety cap — prevent infinite loops
APPROVED_SIGNAL      = "VERDICT: APPROVED"      # string the LLM uses to signal done


# ─── Utilities ────────────────────────────────────────────────────────────────

def load_file(filepath: str, label: str = "file") -> str:
    """Read and return contents of a text file."""
    if not os.path.exists(filepath):
        print(f"[ERROR] {label} not found: {filepath}")
        sys.exit(1)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        print(f"[ERROR] {label} is empty: {filepath}")
        sys.exit(1)
    return content


def load_system_prompt() -> str:
    """Load critic_system_prompt.txt from the script's directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath   = os.path.abspath(os.path.join(script_dir, "..", "prompts", CRITIC_PROMPT_FILE))
    prompt     = load_file(filepath, label=f"system prompt ({CRITIC_PROMPT_FILE})")
    print(f"[INFO] Loaded system prompt: {filepath}")
    return prompt


def query_ollama(system_prompt: str, user_message: str, task_label: str = "Thinking") -> str:
    """Send a streaming request to Ollama and return the full response."""
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

    print(f"[INFO] Querying Ollama ({MODEL_NAME}) — {task_label} ...\n")

    tokens = []
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
                        tokens.append(token)
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

    print()
    result = "".join(tokens).strip()
    if not result:
        print("[ERROR] Empty response from Ollama.")
        sys.exit(1)
    return result


# ─── Critique Logic ───────────────────────────────────────────────────────────

def generate_critique(system_prompt: str, explanation: str,
                      filename: str, iteration: int,
                      previous_critique: str = "") -> str:
    """
    Ask the LLM to review the explanation.
    On iterations > 1, also pass what was previously asked so the LLM
    can verify whether earlier issues were actually fixed.
    """
    if iteration == 1:
        user_message = (
            f"Please review the following lecture explanation document.\n"
            f"Filename: {filename}\n\n"
            f"EXPLANATION DOCUMENT:\n"
            f"{'─' * 60}\n"
            f"{explanation}\n"
            f"{'─' * 60}\n\n"
            f"Produce your critique report following all instructions."
        )
    else:
        user_message = (
            f"You are reviewing a REVISED version of a lecture explanation.\n"
            f"Filename: {filename}\n\n"
            f"YOUR PREVIOUS CRITIQUE (what you asked to be fixed):\n"
            f"{'─' * 60}\n"
            f"{previous_critique}\n"
            f"{'─' * 60}\n\n"
            f"THE UPDATED EXPLANATION DOCUMENT (after revision):\n"
            f"{'─' * 60}\n"
            f"{explanation}\n"
            f"{'─' * 60}\n\n"
            f"IMPORTANT INSTRUCTIONS FOR THIS RE-REVIEW:\n"
            f"1. First check each issue from your previous critique — is it now resolved?\n"
            f"2. If an issue is resolved, do NOT raise it again\n"
            f"3. Only raise an issue again if it is genuinely still present and unaddressed\n"
            f"4. You may also raise NEW issues if they are significant (max 4 total)\n"
            f"5. If all previous issues are fixed and there are no new significant ones, "
            f"output VERDICT: APPROVED\n\n"
            f"Produce your critique report following all instructions."
        )

    return query_ollama(system_prompt, user_message,
                        task_label=f"Reviewing (iteration {iteration})")


def is_approved(critique_text: str) -> bool:
    """Return True if the critique signals the document is approved."""
    return APPROVED_SIGNAL in critique_text


def save_critique(critique_text: str, iteration: int, explanation_path: str) -> str:
    """
    Overwrite the single active_critique.txt file with the latest critique.
    No pile-up of critique files — always one live file.
    """
    critique_dir = os.path.dirname(os.path.abspath(explanation_path))
    critique_path = os.path.join(critique_dir, ACTIVE_CRITIQUE_FILE)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header    = (
        f"ACTIVE CRITIQUE — Iteration {iteration}\n"
        f"Generated: {timestamp}\n"
        f"{'=' * 60}\n\n"
    )

    with open(critique_path, "w", encoding="utf-8") as f:
        f.write(header + critique_text)

    print(f"[INFO] Critique saved to: {critique_path}")
    return critique_path


def call_explainer_revise(explanation_path: str, critique_path: str) -> None:
    """
    Invoke explainer.py Module 2 as a subprocess to apply the critique.
    The explanation file is updated in-place by the explainer.
    """
    script_dir    = os.path.dirname(os.path.abspath(__file__))
    explainer_py  = os.path.join(script_dir, "explainer.py")

    if not os.path.exists(explainer_py):
        print(f"[ERROR] explainer.py not found at: {explainer_py}")
        print("[HINT]  Make sure explainer.py is in the same directory as critic.py")
        sys.exit(1)

    print(f"\n[INFO] Calling explainer.py revise ...")
    cmd = [sys.executable, explainer_py, "revise", explanation_path, critique_path]

    result = subprocess.run(cmd, text=True)

    if result.returncode != 0:
        print(f"[ERROR] explainer.py exited with code {result.returncode}")
        sys.exit(1)


# ─── Main Loop ────────────────────────────────────────────────────────────────

def print_banner(text: str) -> None:
    width = 60
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)


def main() -> None:
    if len(sys.argv) < 2:
        print("\nUsage: python critic.py <explanation-file>")
        print("Example: python critic.py outputs\\machine-learning\\explanation.txt\n")
        sys.exit(1)

    explanation_path = sys.argv[1]

    if not os.path.exists(explanation_path):
        print(f"[ERROR] Explanation file not found: {explanation_path}")
        sys.exit(1)

    system_prompt    = load_system_prompt()
    filename         = os.path.basename(explanation_path)
    previous_critique = ""

    print_banner(f"CRITIC AGENT — {filename}")
    print(f"[INFO] Max iterations: {MAX_ITERATIONS}")
    print(f"[INFO] Approval signal: \"{APPROVED_SIGNAL}\"")

    for iteration in range(1, MAX_ITERATIONS + 1):

        print_banner(f"ITERATION {iteration} / {MAX_ITERATIONS}")

        # ── Step 1: Load current explanation ─────────────────────────────────
        explanation = load_file(explanation_path, label="explanation file")

        # ── Step 2: Generate critique ─────────────────────────────────────────
        critique = generate_critique(
            system_prompt    = system_prompt,
            explanation      = explanation,
            filename         = filename,
            iteration        = iteration,
            previous_critique = previous_critique,
        )

        # ── Step 3: Check for approval ────────────────────────────────────────
        if is_approved(critique):
            print_banner("APPROVED — CRITIQUE CYCLE COMPLETE")
            print(f"[SUCCESS] The explanation passed review after {iteration} iteration(s).")
            print(f"[INFO]    Final file: {explanation_path}")

            # Clean up active_critique file on approval — no leftover noise
            critique_dir = os.path.dirname(os.path.abspath(explanation_path))
            critique_path = os.path.join(critique_dir, ACTIVE_CRITIQUE_FILE)
            if os.path.exists(critique_path):
                os.remove(critique_path)
                print(f"[INFO]    Removed temp critique file: {ACTIVE_CRITIQUE_FILE}")

            sys.exit(0)

        # ── Step 4: Save critique and send to explainer ───────────────────────
        critique_path    = save_critique(critique, iteration, explanation_path)
        previous_critique = critique   # remember what we asked for next round

        print(f"\n[INFO] Issues found — sending to explainer for revision ...")
        call_explainer_revise(explanation_path, critique_path)

    # ── Cap reached ───────────────────────────────────────────────────────────
    print_banner(f"MAX ITERATIONS ({MAX_ITERATIONS}) REACHED")
    print(f"[WARNING] The critique loop hit the iteration cap.")
    print(f"[INFO]    The explanation has been revised {MAX_ITERATIONS} time(s).")
    print(f"[INFO]    Final file: {explanation_path}")
    print(f"[INFO]    Last critique: {ACTIVE_CRITIQUE_FILE}")
    print(f"[INFO]    Review manually if further refinement is needed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
