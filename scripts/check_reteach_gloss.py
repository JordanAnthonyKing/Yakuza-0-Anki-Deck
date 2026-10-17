"""Flag sense-divergent (reteach) cards whose polished gloss is still the OLD taught sense.

A word is retaught because the chapter uses it in a new meaning, but the polish agent can only
pick from JMdict's candidates; when the new sense is a set phrase JMdict lacks (いい加減,
手に負えない, 身体を張る …) it falls back to the old gloss, and the card teaches the wrong thing.
Fix the flagged glosses by hand in gloss_polish_ch{N}.json before merge-gloss.

Usage: python check_reteach_gloss.py <ch>
"""
import os, sys, json
from build_deck import DATA

ch = int(sys.argv[1])
sd = os.path.join(DATA, f"sense_divergent_ch{ch}.json")
div = set(json.load(open(sd, encoding="utf-8"))) if os.path.exists(sd) else set()
led = json.load(open(os.path.join(DATA, "taught_words.json"), encoding="utf-8"))["entries"]
gp = os.path.join(DATA, f"gloss_polish_ch{ch}.json")
g = json.load(open(gp, encoding="utf-8")) if os.path.exists(gp) else {}
for c in json.load(open(os.path.join(DATA, f"cards_ch{ch}_{ch}.json"), encoding="utf-8")):
    w = c["word"]
    if w in div and w in led:
        gl = (g.get(w) or c["meaning"]).strip()
        if gl in led[w]["glosses"]:
            print(f"ch{ch} order {c['order']}: {w} still glossed with an old sense: {gl!r} | {c['sentence'][:45]}")
