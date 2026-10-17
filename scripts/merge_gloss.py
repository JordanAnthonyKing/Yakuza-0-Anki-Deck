"""Apply polished glosses (from the gloss-polish subagent) onto the card set and rebuild the .apkg.

Usage: python merge_gloss.py 1 1   # chapters lo hi (matches cards_ch{lo}_{hi}.json)
"""
import os, json, sys
from build_deck import build_apkg, DATA

lo = int(sys.argv[1]); hi = int(sys.argv[2]) if len(sys.argv) > 2 else lo
cards = json.load(open(os.path.join(DATA, f"cards_ch{lo}_{hi}.json"), encoding="utf-8"))
polish = json.load(open(os.path.join(DATA, f"gloss_polish_ch{lo}.json"), encoding="utf-8"))

applied = 0
for c in cards:
    g = polish.get(c["word"])
    if g and g.strip():
        c["meaning"] = g.strip()
        applied += 1

print(f"cards: {len(cards)}, polished glosses applied: {applied}, unchanged: {len(cards)-applied}")
build_apkg(cards, lo, hi)
print("\nsample polished cards:")
import re
for c in cards[:14]:
    print(f"  {c['word']} ({c['reading']}) = {c['meaning'][:50]}")
