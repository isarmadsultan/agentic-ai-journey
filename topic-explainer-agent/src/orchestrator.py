#!/usr/bin/env python3
"""
Orchestrator Agent
------------------
End-to-end pipeline:
  1) planner.py  -> create outline from topic
  2) explainer.py generate -> create explanation from outline
  3) critic.py  -> critique + iterative revisions until approved or capped
  4) notes_creator.py -> produce final study notes PDF

Usage:
    python orchestrator.py "<topic>"
    python orchestrator.py Machine Learning Basics
"""

import os
import sys
import subprocess


def sanitize_filename(topic: str) -> str:
    """Match planner.py filename rules for consistent slugging."""
    safe = topic.lower().strip()
    safe = safe.replace(" ", "-")
    safe = "".join(c for c in safe if c.isalnum() or c in ("-", "_"))
    return safe or "lecture"


def run_step(cmd, cwd, label):
    print(f"\n[INFO] TASK: {label}")
    print(f"[INFO] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, text=True)
    if result.returncode != 0:
        print(f"[ERROR] Step failed: {label}")
        sys.exit(result.returncode)


def print_file_contents(label: str, path: str) -> None:
    if not os.path.exists(path):
        print(f"[WARNING] {label} not found: {path}")
        return
    print("\n" + "=" * 60)
    print(f"  OUTPUT: {label}")
    print("=" * 60)
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().rstrip()
        print(content)
    except OSError as e:
        print(f"[WARNING] Could not read {label}: {e}")
    print("\n" + "=" * 60)


def main() -> None:
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:]).strip()
    else:
        topic = input("Enter the lecture topic: ").strip()

    if not topic:
        print("[ERROR] No topic provided.")
        print("Usage: python orchestrator.py <topic>")
        sys.exit(1)

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    src_dir = os.path.join(project_root, "src")

    planner_py = os.path.join(src_dir, "planner.py")
    explainer_py = os.path.join(src_dir, "explainer.py")
    critic_py = os.path.join(src_dir, "critic.py")
    notes_py = os.path.join(src_dir, "notes_creator.py")

    for path in (planner_py, explainer_py, critic_py, notes_py):
        if not os.path.exists(path):
            print(f"[ERROR] Missing required script: {path}")
            sys.exit(1)

    slug = sanitize_filename(topic)
    output_dir = os.path.join(project_root, "outputs", slug)
    outline_path = os.path.join(output_dir, "outline.txt")
    explanation_path = os.path.join(output_dir, "explanation.txt")

    print("\n" + "=" * 60)
    print("  ORCHESTRATOR AGENT")
    print("=" * 60)
    print(f"[INFO] Topic: {topic}")
    print(f"[INFO] Working directory: {project_root}")

    # Step 1: Planner -> outline
    run_step([sys.executable, planner_py, topic], project_root, "Step 1/4: Planning outline")
    if not os.path.exists(outline_path):
        print(f"[ERROR] Outline not found after planner: {outline_path}")
        sys.exit(1)
    print_file_contents("Generated Outline", outline_path)

    # Step 2: Explainer -> explanation
    run_step([sys.executable, explainer_py, "generate", outline_path], project_root, "Step 2/4: Generating explanation")
    if not os.path.exists(explanation_path):
        print(f"[ERROR] Explanation not found after explainer: {explanation_path}")
        sys.exit(1)
    print_file_contents("Generated Explanation (Pre-Critique)", explanation_path)

    # Step 3: Critic -> iterative revision
    run_step([sys.executable, critic_py, explanation_path], project_root, "Step 3/4: Critiquing and revising")
    if not os.path.exists(explanation_path):
        print(f"[ERROR] Explanation missing after critique loop: {explanation_path}")
        sys.exit(1)
    print_file_contents("Final Explanation (Post-Critique)", explanation_path)

    # Step 4: Notes creator -> PDF
    run_step([sys.executable, notes_py, explanation_path], project_root, "Step 4/4: Creating study notes PDF")

    notes_path = os.path.join(output_dir, "notes.pdf")
    print("\n" + "=" * 60)
    print("[DONE] Pipeline complete.")
    print(f"[INFO] Outline: {outline_path}")
    print(f"[INFO] Explanation: {explanation_path}")
    if os.path.exists(notes_path):
        print(f"[INFO] Notes PDF: {notes_path}")
    else:
        print("[WARNING] Notes PDF not found. Check notes_creator output.")


if __name__ == "__main__":
    main()
