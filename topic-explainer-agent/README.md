# Topic Explainer Agent

End-to-end pipeline that turns a topic into a 60-minute lecture outline, a full explanation, and a polished PDF of study notes.

## What This Does
- Plans a lecture outline with time-boxed sections.
- Expands the outline into a full lecture explanation.
- Critiques and revises the explanation iteratively.
- Renders a final PDF from the explanation.

## Pipeline (Default)
1. `src/planner.py` generates `outline.txt`.
2. `src/explainer.py generate` creates `explanation.txt`.
3. `src/critic.py` critiques and calls `explainer.py revise` until approved or capped.
4. `src/notes_creator.py` renders `notes.pdf`.

The orchestrator runs all steps:
```
python src/orchestrator.py "Capitalism vs Liberalism"
```

## Requirements
- Python 3.10+ recommended.
- Ollama running locally at `http://localhost:11434`.
- Model pulled: `llama3.2:3b`.
- ReportLab installed for PDF rendering.

## Setup
1. Start Ollama:
```
ollama serve
```

2. Pull the model:
```
ollama pull llama3.2:3b
```

3. Install Python deps:
```
pip install reportlab
```

## Usage
Run the full pipeline:
```
python src/orchestrator.py "Machine Learning Basics"
```

Run modules individually:
```
python src/planner.py "Machine Learning Basics"
python src/explainer.py generate outputs\machine-learning-basics\outline.txt
python src/critic.py outputs\machine-learning-basics\explanation.txt
python src/notes_creator.py outputs\machine-learning-basics\explanation.txt
```

## Outputs
Each topic is slugged into `outputs/<topic-slug>/`:
- `outline.txt`
- `explanation.txt`
- `notes.pdf`

Example:
```
outputs\capitalism-vs-liberalism\notes.pdf
```

## Notes
- `prompts/notes_system_prompt.txt` is not used by default; notes are generated rule-based in `src/notes_creator.py`.
- The critic loop caps at 4 iterations to avoid infinite loops.
- If you change the model name in scripts, update all agent files for consistency.

## Troubleshooting
- If Ollama is unreachable, make sure `ollama serve` is running.
- If PDFs fail to render, re-install ReportLab and confirm the virtual environment is active.
