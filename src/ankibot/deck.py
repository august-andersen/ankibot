"""Genanki deck/model creation and .apkg export."""

import re

import genanki

# Fixed model IDs so Anki recognizes updates to the same note types
MODEL_ID_BASIC = 1607392319
MODEL_ID_REVERSED = 1607392320
MODEL_ID_MULTI = 1607392321
MODEL_ID_IMAGE = 1607392322
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
.extra {
  font-size: 13px;
  color: #888;
  margin-top: 8px;
  font-style: italic;
}
"""

# --- Basic (Forward Only) ---
BASIC_MODEL = genanki.Model(
    MODEL_ID_BASIC,
    "AnkiBot Basic",
    fields=[{"name": "Front"}, {"name": "Back"}, {"name": "Extra"}],
    templates=[
        {
            "name": "Forward",
            "qfmt": "<div class='front'>{{Front}}</div>",
            "afmt": (
                "<div class='front'>{{Front}}</div>"
                "<hr id='answer'>"
                "<div class='back'>{{Back}}</div>"
                "{{#Extra}}<div class='extra'>{{Extra}}</div>{{/Extra}}"
            ),
        },
    ],
    css=CSS,
)

# --- Basic (and Reversed) ---
REVERSED_MODEL = genanki.Model(
    MODEL_ID_REVERSED,
    "AnkiBot Reversed",
    fields=[{"name": "Front"}, {"name": "Back"}, {"name": "Extra"}],
    templates=[
        {
            "name": "Forward",
            "qfmt": "<div class='front'>{{Front}}</div>",
            "afmt": (
                "<div class='front'>{{Front}}</div>"
                "<hr id='answer'>"
                "<div class='back'>{{Back}}</div>"
                "{{#Extra}}<div class='extra'>{{Extra}}</div>{{/Extra}}"
            ),
        },
        {
            "name": "Reverse",
            "qfmt": "<div class='front'>{{Back}}</div>",
            "afmt": (
                "<div class='front'>{{Back}}</div>"
                "<hr id='answer'>"
                "<div class='back'>{{Front}}</div>"
                "{{#Extra}}<div class='extra'>{{Extra}}</div>{{/Extra}}"
            ),
        },
    ],
    css=CSS,
)

# --- Multi-Card Note ---
MULTI_MODEL = genanki.Model(
    MODEL_ID_MULTI,
    "AnkiBot Multi",
    fields=[
        {"name": "Concept"},
        {"name": "Detail1"},
        {"name": "Detail2"},
        {"name": "Detail3"},
        {"name": "Extra"},
    ],
    templates=[
        {
            "name": "Detail 1",
            "qfmt": "<div class='front'>{{Concept}}</div><br><div class='back'>Detail 1?</div>",
            "afmt": (
                "<div class='front'>{{Concept}}</div>"
                "<hr id='answer'>"
                "<div class='back'>{{Detail1}}</div>"
                "{{#Extra}}<div class='extra'>{{Extra}}</div>{{/Extra}}"
            ),
        },
        {
            "name": "Detail 2",
            "qfmt": "{{#Detail2}}<div class='front'>{{Concept}}</div><br><div class='back'>Detail 2?</div>{{/Detail2}}",
            "afmt": (
                "<div class='front'>{{Concept}}</div>"
                "<hr id='answer'>"
                "<div class='back'>{{Detail2}}</div>"
                "{{#Extra}}<div class='extra'>{{Extra}}</div>{{/Extra}}"
            ),
        },
        {
            "name": "Detail 3",
            "qfmt": "{{#Detail3}}<div class='front'>{{Concept}}</div><br><div class='back'>Detail 3?</div>{{/Detail3}}",
            "afmt": (
                "<div class='front'>{{Concept}}</div>"
                "<hr id='answer'>"
                "<div class='back'>{{Detail3}}</div>"
                "{{#Extra}}<div class='extra'>{{Extra}}</div>{{/Extra}}"
            ),
        },
    ],
    css=CSS,
)

# --- Image Card ---
IMAGE_MODEL = genanki.Model(
    MODEL_ID_IMAGE,
    "AnkiBot Image",
    fields=[
        {"name": "Image"},
        {"name": "Question"},
        {"name": "Answer"},
        {"name": "Extra"},
    ],
    templates=[
        {
            "name": "Image Card",
            "qfmt": "<div class='front'>{{Image}}<br>{{Question}}</div>",
            "afmt": (
                "<div class='front'>{{Image}}<br>{{Question}}</div>"
                "<hr id='answer'>"
                "<div class='back'>{{Answer}}</div>"
                "{{#Extra}}<div class='extra'>{{Extra}}</div>{{/Extra}}"
            ),
        },
    ],
    css=CSS,
)

MODELS = {
    "basic": BASIC_MODEL,
    "reversed": REVERSED_MODEL,
    "multi": MULTI_MODEL,
    "image": IMAGE_MODEL,
}


def sanitize_filename(name: str) -> str:
    """Convert a deck name to a safe filename."""
    name = name.strip().lower()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s]+", "-", name)
    return name


def _deck_id_for(name: str) -> int:
    """Generate a deterministic deck ID from a name."""
    return DECK_ID_BASE + sum(ord(c) for c in name)


def create_deck(deck_name: str, cards: list[dict], output_dir: str = ".") -> str:
    """Create an .apkg file from a list of card dicts with subdeck support.
    Returns the path to the created file.
    """
    decks: dict[str, genanki.Deck] = {}

    def get_deck(subdeck: str) -> genanki.Deck:
        if subdeck:
            full_name = f"{deck_name}::{subdeck}"
        else:
            full_name = deck_name
        if full_name not in decks:
            decks[full_name] = genanki.Deck(_deck_id_for(full_name), full_name)
        return decks[full_name]

    for card in cards:
        model_name = card.get("model", "basic")
        model = MODELS.get(model_name, BASIC_MODEL)
        subdeck = card.get("subdeck", "")
        deck = get_deck(subdeck)

        tags = card.get("tags", [])
        clean_tags = [re.sub(r"\s+", "-", str(t)) for t in tags if t]
        extra = card.get("extra", "")

        if model_name == "multi":
            fields = [
                card.get("concept", ""),
                card.get("detail1", ""),
                card.get("detail2", ""),
                card.get("detail3", ""),
                extra,
            ]
        elif model_name == "image":
            fields = [
                card.get("image", ""),
                card.get("question", ""),
                card.get("answer", ""),
                extra,
            ]
        else:
            # basic or reversed
            fields = [card.get("front", ""), card.get("back", ""), extra]

        note = genanki.Note(model=model, fields=fields, tags=clean_tags)
        deck.add_note(note)

    # Ensure the root deck exists even if all cards went to subdecks
    if deck_name not in decks:
        decks[deck_name] = genanki.Deck(_deck_id_for(deck_name), deck_name)

    filename = sanitize_filename(deck_name) + ".apkg"
    filepath = f"{output_dir}/{filename}"
    package = genanki.Package(list(decks.values()))
    package.write_to_file(filepath)
    return filepath
