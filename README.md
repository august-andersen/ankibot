# ankibot

Turn any folder of multimedia materials into an importable .apkg file through a multistage AI orchestration workflow.

## Installation

**Recommended (pipx):**
```bash
git clone https://github.com/august-andersen/ankibot.git
cd ankibot
pipx install .
```

**Alternative (pip + venv):**
```bash
git clone https://github.com/august-andersen/ankibot.git
cd ankibot
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

## API Key Setup

ankibot uses Anthropic API. Set your key one of two ways:

- **Environment variable** (takes priority): `export ANTHROPIC_API_KEY=sk-ant-...`
- **First-run prompt**: ankibot will ask for your key and save it to `~/.ankibot/config.json`

## Usage

```bash
cd ~/my-multimedia-materials
ankibot
```

ankibot scans the current directory, asks for a deck name and detail level, executes the workflow, and saves an `.apkg` file ready to import into Anki. Workflow:
1. Classifies and extracts file contents with format-specific parsers and Claude vision for OCR/visual interpretation
2. Content payloads are chunked into context-window-optimized batches
3. Batches are sent to Claude via API with a system prompt and deck-specific context. Output is parsed, validated, and deduplicated.
4. Cards are compiled into a styled Anki deck with formatting, tags, and a consistent note model, then packaged as an importable `.apkg` file.

## Supported File Types

| Type | Extensions |
|------|-----------|
| PDF | `.pdf` |
| Word | `.docx` |
| PowerPoint | `.pptx` |
| Markdown | `.md` |
| CSV | `.csv` |
| Images | `.jpg`, `.jpeg`, `.png` |

## Detail Levels

| Level | Description |
|-------|-------------|
| 1 | Basics only — key definitions, core facts, surface-level recall |
| 2 | Fundamental understanding — concepts, relationships, why things work |
| 3 | Highly detailed — nuance, edge cases, deep connections, advanced details |
