"""CLI entry point — prompts, orchestration, terminal output."""

from pathlib import Path

from ankibot.extractor import (
    EXTENSION_LABELS,
    extract_file,
    is_image,
    scan_directory,
    word_count,
)
from ankibot.generator import generate_cards, get_api_key
from ankibot.deck import create_deck


def main():
    cwd = Path.cwd()

    print("\n📂 Scanning current directory...")
    files = scan_directory(cwd)

    if not files:
        print("No supported files found in the current directory.")
        return

    print(f"Found {len(files)} file{'s' if len(files) != 1 else ''}:")
    for f in files:
        label = EXTENSION_LABELS.get(f.suffix.lower(), "Unknown")
        print(f"  - {f.name} ({label})")

    print()
    deck_name = input("Deck name: ").strip()
    if not deck_name:
        print("Error: Deck name cannot be empty.")
        return

    print("Detail levels:")
    print("  1 — Quick    (~20-30 cards, key concepts only)")
    print("  2 — Standard (~50-80 cards, thorough coverage)")
    print("  3 — Deep     (100+ cards, exhaustive, multiple card types per concept)")
    while True:
        level_input = input("Detail level (1-3): ").strip()
        if level_input in ("1", "2", "3"):
            detail_level = int(level_input)
            break
        print("Please enter 1, 2, or 3.")

    api_key = get_api_key()

    print("\n⏳ Extracting content from files...")
    all_text_parts = []
    all_image_blocks = []

    for f in files:
        text, images = extract_file(f)
        if text:
            words = word_count(text)
            print(f"  ✓ {f.name} (extracted {words:,} words)")
            all_text_parts.append(f"=== {f.name} ===\n{text}")
        elif images:
            if is_image(f):
                print(f"  ✓ {f.name} (sending to vision)")
            else:
                print(f"  ✓ {f.name} (scanned PDF, sending {len(images)} pages to vision)")
            all_image_blocks.extend(images)
        else:
            print(f"  ⚠ {f.name} (no content extracted)")

    combined_text = "\n\n".join(all_text_parts)

    if not combined_text.strip() and not all_image_blocks:
        print("\nNo content could be extracted from any files.")
        return

    print("\n🤖 Generating flashcards with Claude...")
    cards = generate_cards(combined_text, all_image_blocks, detail_level, api_key)

    if not cards:
        print("No flashcards were generated. Check your API key and try again.")
        return

    # Summarize by model type
    from collections import Counter
    model_counts = Counter(c.get("model", "basic") for c in cards)
    subdeck_count = len({c.get("subdeck", "") for c in cards} - {""})
    parts = [f"{count} {model}" for model, count in sorted(model_counts.items())]
    print(f"  Generated {len(cards)} cards ({', '.join(parts)})")
    if subdeck_count:
        print(f"  Organized into {subdeck_count} subdeck{'s' if subdeck_count != 1 else ''}")

    filepath = create_deck(deck_name, cards, str(cwd))
    print(f"\n✅ Saved: {filepath}\n")


if __name__ == "__main__":
    main()
