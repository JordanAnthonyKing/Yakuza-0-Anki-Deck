"""Shared helpers for the cumulative cross-chapter 'taught words' ledger.

data/taught_words.json accumulates every content word introduced by a built story-chapter
deck, so later chapters don't re-teach it -- EXCEPT words whose later-chapter meaning is
drastically different (the sense-divergence gate). Those are listed per chapter in
data/sense_divergent_ch{N}.json and reappear in their new sense.

Ledger shape:
  {"built_chapters": [1, 2, ...],
   "entries": {word: {reading, chapter (first taught), multi_sense, glosses[], candidates[]}}}
"""
import os, json

REPO = r"C:\Users\jordan\repos\yakuza"
DATA = os.path.join(REPO, "data")
LEDGER = os.path.join(DATA, "taught_words.json")

def load_ledger():
    if os.path.exists(LEDGER):
        return json.load(open(LEDGER, encoding="utf-8"))
    return {"built_chapters": [], "entries": {}}

def save_ledger(led):
    json.dump(led, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def load_divergent(chapter):
    """Set of words to un-suppress (reteach) for `chapter`, from sense_divergent_ch{N}.json."""
    p = os.path.join(DATA, f"sense_divergent_ch{chapter}.json")
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        return set(d if isinstance(d, list) else d.get("words", []))
    return set()

def suppression_sets(led, before_chapter, keep=frozenset()):
    """Words+readings to suppress when building `before_chapter`: everything taught in a
    strictly-earlier chapter, minus the `keep` (sense-divergent) allow-list. A kept word's
    reading is never added, so it survives reading-based suppression too."""
    words, readings = set(), set()
    for w, e in led["entries"].items():
        if e["chapter"] < before_chapter and w not in keep:
            words.add(w)
            if e.get("reading"):
                readings.add(e["reading"])
    return words, readings
