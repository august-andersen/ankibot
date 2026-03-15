"""Genanki deck/model creation and .apkg export."""

import re
import random

import genanki

# Fixed model ID so Anki recognizes updates to the same note type
MODEL_ID = 1607392319
DECK_ID_BASE = 2059400110

CSS = """\
.card {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 18px;
  text-align: center;
  color: #333;
  background-color: #fafafa;
  padding: 20px;
  line-height: 1.5;
}
.back {
  font-size: 16px;
  text-align: left;
  margin-top: 12px;
}
"""

FRONT_TEMPLATE = "<div class='front'>{{Front}}</div>"
BACK_TEMPLATE = "<div class='front'>{{Front}}</div><hr id='answer'><div class='back'>{{Back}}</div>"

ANKI_MODEL = genanki.Model(
    MODEL_ID,
    "AnkiBot Basic",
    fields=[{"name": "Front"}, {"name": "Back"}],
    templates=[
        {
            "name": "Card 1",
            "qfmt": FRONT_TEMPLATE,
            "afmt": BACK_TEMPLATE,
        },
    ],
    css=CSS,
)


def sanitize_filename(name: str) -> str:
    """Convert a deck name to a safe filename."""
    name = name.strip().lower()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s]+", "-", name)
    return name


def create_deck(deck_name: str, cards: list[dict], output_dir: str = ".") -> str:
    """Create an .apkg file from a list of card dicts.
    Returns the path to the created file.
    """
    # Generate a deterministic deck ID from the name
    deck_id = DECK_ID_BASE + sum(ord(c) for c in deck_name)
    deck = genanki.Deck(deck_id, deck_name)

    for card in cards:
        tags = card.get("tags", [])
        # Ensure tags are strings and sanitized
        clean_tags = [re.sub(r"\s+", "-", str(t)) for t in tags if t]
        note = genanki.Note(
            model=ANKI_MODEL,
            fields=[card["front"], card["back"]],
            tags=clean_tags,
        )
        deck.add_note(note)

    filename = sanitize_filename(deck_name) + ".apkg"
    filepath = f"{output_dir}/{filename}"
    genanki.Package(deck).write_to_file(filepath)
    return filepath
