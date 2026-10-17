"""Combine the classify_ch0_part*.json outputs and build the two word-first decks:
  - Chapter 0 (CORE)  -> data/decks/yakuza0_ch0.apkg
  - Minigame terms    -> data/decks/yakuza0_minigame.apkg
Card model is WORD-FIRST: front = word only; back = reading, meaning, optional example.

Also writes data/pretaught_words.json = CORE + MINIGAME words MINUS the sense-divergent
set, so later story/substory builds can treat them as known (see build_deck.py, which
loads this automatically). Sense-divergent terms are intentionally left out so they can
reappear later in their other meaning.
"""
import os, json, glob, re
import genanki
from build_deck import DATA, kata2hira, strip_orphan_brackets
from keep_guids import old_guids, guid
from term_model import MODEL

# word -> {reading,pos} from the candidate pool
cand = {c["word"]: c for c in json.load(open(os.path.join(DATA, "candidates_ch0.json"), encoding="utf-8"))}

# merge classifier parts
cls = {}
for p in sorted(glob.glob(os.path.join(DATA, "classify_ch0_part*.json"))):
    cls.update(json.load(open(p, encoding="utf-8")))
print(f"merged {len(cls)} classified words")

buckets = {"CORE": [], "MINIGAME": [], "GENERAL": []}
divergent = []
for word, v in cls.items():
    b = v.get("bucket", "GENERAL").upper()
    if b not in buckets:
        b = "GENERAL"
    meta = cand.get(word, {})
    card = {
        "word": word,
        "reading": meta.get("reading", ""),
        "meaning": (v.get("meaning") or "").strip(),
        "example": strip_orphan_brackets((v.get("example") or "").strip()),
        "pos": meta.get("pos", ""),
    }
    buckets[b].append(card)
    if b in ("CORE", "MINIGAME") and v.get("sense_divergent"):
        divergent.append(word)

for b in buckets:
    buckets[b].sort(key=lambda c: kata2hira(c["reading"] or c["word"]))
print("  CORE:", len(buckets["CORE"]), " MINIGAME:", len(buckets["MINIGAME"]),
      " GENERAL(drop):", len(buckets["GENERAL"]), " sense-divergent:", len(divergent))

# English for the example sentences (prep_term_examples.py -> translate subagent):
# literal always, official localization only when the gate passed
tdir = os.path.join(DATA, "translate", "terms")
ex_en = {}
if os.path.exists(os.path.join(tdir, "out.json")):
    res = json.load(open(os.path.join(tdir, "out.json"), encoding="utf-8"))
    for r in json.load(open(os.path.join(tdir, "in.json"), encoding="utf-8")):
        t = res.get(str(r["order"]), {})
        ex_en[(r["bucket"], r["word"])] = ((t.get("literal") or "").strip(),
                                          (t.get("official") or "").strip() if t.get("official_ok") else "")

def build(cards, bucket, deck_id, name, fname):
    out = os.path.join(DATA, "decks"); os.makedirs(out, exist_ok=True)
    path = os.path.join(out, fname)
    old = old_guids(path)                    # key (Word, Reading) -> guid already in Anki
    deck = genanki.Deck(deck_id, name)
    n_en = 0
    for c in cards:
        eng, off = ex_en.get((bucket, c["word"]), ("", "")) if c["example"] else ("", "")
        n_en += bool(eng)
        fields = [c["word"], c["reading"], c["meaning"], c["example"], c["pos"], eng, off]
        deck.add_note(genanki.Note(model=MODEL, fields=fields, guid=guid(old, fields)))
    genanki.Package(deck).write_to_file(path)
    print("wrote", path, f"({len(cards)} cards, {n_en} examples with English)")

build(buckets["CORE"], "CORE", 2059400100, "Yakuza 0 · Chapter 0 (Game Basics)", "yakuza0_ch0.apkg")
build(buckets["MINIGAME"], "MINIGAME", 2059400200, "Yakuza 0 · Minigame Terms", "yakuza0_minigame.apkg")

# suppression list for later story/substory mining (exclude sense-divergent so they recur)
pre_words, pre_readings = [], []
for b in ("CORE", "MINIGAME"):
    for c in buckets[b]:
        if c["word"] in divergent:
            continue
        pre_words.append(c["word"])
        if c["reading"]:
            pre_readings.append(kata2hira(c["reading"]))
json.dump({"words": sorted(set(pre_words)), "readings": sorted(set(pre_readings)),
           "sense_divergent": sorted(divergent)},
          open(os.path.join(DATA, "pretaught_words.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"pretaught_words.json: {len(set(pre_words))} suppressed, {len(divergent)} kept reappearable")

# save merged classification + bucket lists for review
json.dump(buckets, open(os.path.join(DATA, "ch0_buckets.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nCORE sample:", "  ".join(c["word"] for c in buckets["CORE"][:25]))
print("MINIGAME sample:", "  ".join(c["word"] for c in buckets["MINIGAME"][:25]))
