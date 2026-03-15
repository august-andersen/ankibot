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


SYSTEM_PROMPT = """You are a flashcard generation expert. Your task is to analyze study material and generate high-quality Anki flashcards.

Rules:
1. Analyze the study material thoroughly.
2. Generate flashcards as a JSON array. Each card has "front" (question), "back" (answer), and optionally "tags" (1-2 broad topic tags).
3. Each card's "back" must be a complete, self-contained answer — not just a single word.
4. Output ONLY valid JSON — an array of card objects. No markdown fences, no explanation, no preamble.

Example output format:
[{"front":"What is X?","back":"X is...","tags":["topic"]}]"""


DETAIL_INSTRUCTIONS = {
    1: "Detail level: BASICS ONLY. Generate ~1 card per key concept. Focus on definitions, names, dates, and core facts. Cards should test simple recall.",
    2: "Detail level: FUNDAMENTAL UNDERSTANDING. Generate ~2-3 cards per key concept. Include 'why' and 'how' cards, relationships between concepts, and conceptual understanding.",
    3: "Detail level: HIGHLY DETAILED. Generate ~4-5 cards per key concept. Include edge cases, nuance, comparisons, implications, and deep connections across topics.",
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
        if isinstance(card, dict) and "front" in card and "back" in card:
            valid.append({
                "front": str(card["front"]),
                "back": str(card["back"]),
                "tags": card.get("tags", []),
            })
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

    # Deduplicate by front text
    seen = set()
    unique = []
    for card in all_cards:
        key = card["front"].strip().lower()
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
