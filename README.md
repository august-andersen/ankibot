<p align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/3/3d/Anki-icon.svg" alt="Anki" width="80">
</p>

<h1 align="center">ankibot</h1>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.9+-3776AB?logo=python&logoColor=white" alt="Python 3.9+"></a>
  <a href="https://docs.anthropic.com/"><img src="https://img.shields.io/badge/Anthropic-Claude_API-191919?logo=anthropic&logoColor=white" alt="Claude API"></a>
  <a href="https://apps.ankiweb.net/"><img src="https://img.shields.io/badge/export-.apkg-326CE5" alt=".apkg"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License"></a>
</p>

<p align="center">Turn any folder of multimedia materials into an importable .apkg file through a multistage AI orchestration workflow.</p>

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
