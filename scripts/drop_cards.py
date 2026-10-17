"""Drop mistagged cards from a chapter IN PLACE (never renumbers survivors, so order-keyed
translations stay valid — the same rule as the frozen Ch1 file). Removes each word from
cards_ch{N}_{N}.json and gloss_polish_ch{N}.json. Run BEFORE update_taught so dropped
words never enter the ledger.

Usage: python drop_cards.py <ch> <word> [<word> ...]
"""
import os, sys, json
from build_deck import DATA

ch, words = int(sys.argv[1]), set(sys.argv[2:])
cp = os.path.join(DATA, f"cards_ch{ch}_{ch}.json")
cards = json.load(open(cp, encoding="utf-8"))
keep = [c for c in cards if c["word"] not in words]
gone = [c for c in cards if c["word"] in words]
missing = words - {c["word"] for c in gone}
if missing:
    sys.exit(f"not in ch{ch}: {' '.join(sorted(missing))} — nothing changed")
json.dump(keep, open(cp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
gp = os.path.join(DATA, f"gloss_polish_ch{ch}.json")
if os.path.exists(gp):
    g = json.load(open(gp, encoding="utf-8"))
    json.dump({w: v for w, v in g.items() if w not in words}, open(gp, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
# record the drops so pipeline.py's GUID check can tell intended removals from lost notes
lp = os.path.join(DATA, "pipeline", f"ch{ch}", "dropped.json")
os.makedirs(os.path.dirname(lp), exist_ok=True)
log = json.load(open(lp, encoding="utf-8")) if os.path.exists(lp) else []
log += [{"order": c["order"], "word": c["word"], "sentence": c["sentence"]} for c in gone]
json.dump(log, open(lp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for c in gone:
    print(f"dropped order {c['order']}: {c['word']} ({c['reading']}) | {c['sentence'][:40]}")
print(f"ch{ch}: {len(cards)} -> {len(keep)} cards")
