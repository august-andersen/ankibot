"""Anthropic API integration for flashcard generation."""

import json
import os
from pathlib import Path

import anthropic

CONFIG_PATH = Path.home() / ".ankibot" / "config.json"
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 16000
# Approximate token limit for content per batch (leave room for prompt overhead)
CONTENT_TOKEN_LIMIT = 150000
CHARS_PER_TOKEN = 4  # rough estimate


SYSTEM_PROMPT = """\
You are a flashcard generation expert producing Anki cards from study material.
Output ONLY a valid JSON array — no markdown fences, no explanation, no preamble.

=== ABSOLUTE RULES ===
1. ANSWERS MUST BE 1-3 WORDS. Never a sentence. If the answer exceeds 4-5 words, split the card or make the question more specific. Push specificity into the question; keep the answer atomic.
2. ONE FACT PER CARD. Never use "What are the...", "List the...", "Name the..." — these ask for sets. Each card targets exactly one item.
3. NO TEACHING. Assume the user already understands the material. No "X is a process in which..." framing. Cards are pure recall triggers — precise cue on front, minimal answer on back.
4. EXTRA FIELD is almost always "" — only populate for disambiguation ("Not to be confused with NADH") or source references ("p.142"). No obvious or descriptive text.
5. 8-SECOND TEST: a prepared student must be able to answer within 8-10 seconds. If not, simplify or split.

=== CARD MODELS ===
Each card object MUST include a "model" field set to one of:

"basic" — Forward only. One-directional facts.
  Fields: {"model":"basic", "front":"...", "back":"...", "extra":"", "tags":[...]}

"reversed" — Generates two cards (both directions). Use for term↔definition, word↔translation.
  Both directions MUST make sense as standalone questions.
  Fields: {"model":"reversed", "front":"...", "back":"...", "extra":"", "tags":[...]}

"multi" — Complex concepts needing multiple angles. Up to 3 detail fields.
  Fields: {"model":"multi", "concept":"...", "detail1":"...", "detail2":"...", "detail3":"...", "extra":"", "tags":[...]}
  detail2 and detail3 may be "" if not needed. detail1 is required.

=== SUBDECKS ===
Each card MUST include a "subdeck" field — a string using :: delimiters for hierarchy (e.g., "Cell Biology::Organelles").
- Group cards into logical subdecks by broad topic area.
- Do NOT over-granulate — avoid micro-topic subdecks. Use tags for fine-grained filtering instead.
- For single-topic material, use a single subdeck name matching the overall topic.

=== TAGS ===
Tag EVERY card with ALL applicable tags from these categories:
- topic/chapter (e.g., "mitosis", "chapter-3", "thermodynamics")
- difficulty: one of "basic", "intermediate", "advanced"
- card-type: one of "definition", "concept", "procedure", "formula", "example", "comparison"
- priority: one of "high", "medium", "low"
Tags must use lowercase-kebab-case. Be consistent across all cards.

=== QUALITY ===
- No duplicate front fields within a model type.
- All cards must be atomic (one fact).
- Reversed cards must make sense read in BOTH directions.
- Consistent tag naming across the entire output."""


DETAIL_INSTRUCTIONS = {
    1: (
        "LEVEL: QUICK (~20-30 cards total). "
        "Key concepts only. Cover the most important definitions, facts, and terms. "
        "Use 'basic' model for most cards; 'reversed' only for essential term↔definition pairs."
    ),
    2: (
        "LEVEL: STANDARD (~50-80 cards total). "
        "Thorough coverage. Cover all significant concepts, relationships, and processes. "
        "Mix 'basic', 'reversed', and 'multi' models as appropriate for each concept."
    ),
    3: (
        "LEVEL: DEEP (100+ cards total). "
        "Exhaustive coverage. Multiple card types per concept — use all models. "
        "Include edge cases, comparisons, nuance, and connections across topics. "
        "Every concept should have basic, reversed, AND multi-angle cards where applicable."
    ),
}


def get_api_key() -> str:
    """Get API key from env var or config file, prompting if neither exists."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key

    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text())
        key = config.get("api_key")
        if key:
            return key

    key = input("Enter your Anthropic API key: ").strip()
    if not key:
        print("Error: No API key provided.")
        raise SystemExit(1)

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"api_key": key}))
    print(f"API key saved to {CONFIG_PATH}")
    return key


def _chunk_text(text: str, max_chars: int) -> list[str]:
    """Split text into chunks that fit within the token limit."""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    while text:
        chunk = text[:max_chars]
        # Try to break at a paragraph or sentence boundary
        last_para = chunk.rfind("\n\n")
        if last_para > max_chars // 2:
            chunk = text[:last_para]
        text = text[len(chunk):]
        chunks.append(chunk.strip())
    return [c for c in chunks if c]


def _parse_cards(response_text: str) -> list[dict]:
    """Parse Claude's response into a list of card dicts."""
    text = response_text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    cards = json.loads(text)
    if not isinstance(cards, list):
        raise ValueError("Expected a JSON array")

    valid = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        model = card.get("model", "basic")
        subdeck = str(card.get("subdeck", ""))
        tags = card.get("tags", [])
        extra = str(card.get("extra", ""))

        if model == "multi":
            if "concept" not in card or "detail1" not in card:
                continue
            valid.append({
                "model": "multi",
                "concept": str(card["concept"]),
                "detail1": str(card["detail1"]),
                "detail2": str(card.get("detail2", "")),
                "detail3": str(card.get("detail3", "")),
                "extra": extra,
                "tags": tags,
                "subdeck": subdeck,
            })
        elif model in ("basic", "reversed"):
            if "front" not in card or "back" not in card:
                continue
            valid.append({
                "model": model,
                "front": str(card["front"]),
                "back": str(card["back"]),
                "extra": extra,
                "tags": tags,
                "subdeck": subdeck,
            })
        # Silently skip unrecognized models
    return valid


def generate_cards(
    text_content: str,
    image_blocks: list[dict],
    detail_level: int,
    api_key: str,
) -> list[dict]:
    """Generate flashcards from extracted content using Claude."""
    client = anthropic.Anthropic(api_key=api_key)
    all_cards = []
    detail_instruction = DETAIL_INSTRUCTIONS[detail_level]

    # Process text content
    if text_content.strip():
        max_chars = CONTENT_TOKEN_LIMIT * CHARS_PER_TOKEN
        chunks = _chunk_text(text_content, max_chars)
        for i, chunk in enumerate(chunks):
            user_msg = f"{detail_instruction}\n\nStudy material:\n\n{chunk}"
            cards = _call_claude(client, user_msg, retry=True)
            all_cards.extend(cards)

    # Process images
    if image_blocks:
        # Batch images in groups of 10 to avoid overly large requests
        batch_size = 10
        for i in range(0, len(image_blocks), batch_size):
            batch = image_blocks[i : i + batch_size]
            content = []
            content.append({
                "type": "text",
                "text": f"{detail_instruction}\n\nExtract all information, text, diagrams, and concepts from these images and generate flashcards from them.",
            })
            content.extend(batch)
            cards = _call_claude(client, content, retry=True)
            all_cards.extend(cards)

    # Deduplicate by front text (per model type, per spec)
    seen = set()
    unique = []
    for card in all_cards:
        model = card.get("model", "basic")
        if model == "multi":
            key = (model, card["concept"].strip().lower())
        else:
            key = (model, card["front"].strip().lower())
        if key not in seen:
            seen.add(key)
            unique.append(card)

    return unique


def _call_claude(client: anthropic.Anthropic, user_content, retry: bool = True) -> list[dict]:
    """Make a single Claude API call and parse the response into cards."""
    if isinstance(user_content, str):
        messages = [{"role": "user", "content": user_content}]
    else:
        messages = [{"role": "user", "content": user_content}]

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        text = response.content[0].text
        return _parse_cards(text)
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        if retry:
            try:
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    messages=messages,
                )
                text = response.content[0].text
                return _parse_cards(text)
            except Exception:
                print(f"  ⚠ Failed to parse flashcards after retry: {e}")
                return []
        print(f"  ⚠ Failed to parse flashcards: {e}")
        return []
    except anthropic.APIError as e:
        print(f"  ⚠ API error: {e}")
        return []
