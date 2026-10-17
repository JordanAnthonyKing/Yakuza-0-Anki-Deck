"""One-off: find vocab cards whose word is actually a character/place name that the
POS tagger mistagged as a common noun (e.g. 錦 'brocade' = Nishiki). Cross-references
each card against the curated name roster by (a) exact surface, (b) card word being a
kanji substring of a name surface, (c) card reading being a prefix/substring of a name
reading. Prints suspects for human review -- does NOT modify anything."""
import os, json, glob
from build_deck import DATA

names = json.load(open(os.path.join(DATA, "names_curated.json"), encoding="utf-8"))
surfs = [n["word"] for n in names]
reads = [n["reading"] for n in names]

def suspect(word, reading):
    hits = []
    for n in names:
        s, r = n["word"], n["reading"]
        if word == s:
            hits.append(f"exact {s}({r})")
        elif len(word) >= 1 and word in s and word != s:
            hits.append(f"substr-of {s}({r})")
        elif reading and (r.startswith(reading) or reading in r) and reading != r and len(reading) >= 2:
            hits.append(f"read~{s}({r})")
    return hits

for cf in sorted(glob.glob(os.path.join(DATA, "cards_ch*.json"))):
    cards = json.load(open(cf, encoding="utf-8"))
    flagged = []
    for c in cards:
        h = suspect(c.get("word",""), c.get("reading",""))
        if h:
            flagged.append((c["order"], c["word"], c["reading"], c.get("meaning",""), c.get("speaker",""), "; ".join(h)))
    if flagged:
        print(f"\n=== {os.path.basename(cf)} ({len(flagged)} suspects) ===")
        for order, w, r, m, spk, h in flagged:
            print(f"  order {order:>4}  {w} ({r}) = {m!r}  spk={spk}  [{h}]")
