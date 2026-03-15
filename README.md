# ankibot

Turn any folder of multimedia materials into an importable .apkg file.

## Installation

```bash
git clone https://github.com/yourusername/ankibot.git
cd ankibot
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

ankibot scans the current directory, asks for a deck name and detail level, generates flashcards with Claude, and saves an `.apkg` file ready to import into Anki.

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
