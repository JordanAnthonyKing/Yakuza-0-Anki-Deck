"""Build the word-first 'Characters & Places' deck (Chapter 0.5), taught before the story.

Front = name (kanji/kana); back = reading, romaji + role/identity, and (kind + first-appearance).
Reuses the Yakuza0 Term word-first model. Input: data/names_curated.json (hand-curated,
identities verified against the Yakuza wiki — proper nouns are excluded from the vocab decks
so names are otherwise never taught).

Usage: python build_names_deck.py
"""
import os, json
import genanki
from build_deck import DATA, kata2hira
from keep_guids import old_guids, guid
from term_model import MODEL      # shared word-first Term note type (same id as ch0/minigame)

cards = json.load(open(os.path.join(DATA, "names_curated.json"), encoding="utf-8"))
cards.sort(key=lambda c: ({"character": 0, "alias": 1, "organization": 2, "place": 3}.get(c["kind"], 4),
                          kata2hira(c["reading"] or c["word"])))

out = os.path.join(DATA, "decks"); os.makedirs(out, exist_ok=True)
path = os.path.join(out, "yakuza0_names.apkg")
old = old_guids(path)                        # key (Word, Reading) -> guid already in Anki

from deck_names import NAMES
deck = genanki.Deck(2059400050, NAMES)
for c in cards:
    ex = f"first appears: Ch.{c['first_chapter']}" if c.get("first_chapter") else ""
    fields = [c["word"], c["reading"], c["meaning"], ex, c["kind"], "", ""]
    deck.add_note(genanki.Note(model=MODEL, fields=fields, guid=guid(old, fields)))
genanki.Package(deck).write_to_file(path)

n = {}
for c in cards:
    n[c["kind"]] = n.get(c["kind"], 0) + 1
print(f"wrote {path} ({len(cards)} cards: " + ", ".join(f"{k} {v}" for k, v in n.items()) + ")")
for c in cards:
    print(f"  [{c['kind']:12}] {c['word']} ({c['reading']}) = {c['meaning'][:60]}")
