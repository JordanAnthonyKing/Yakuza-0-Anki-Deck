"""Fold a built+polished chapter's introduced words into the cumulative taught ledger.

Run AFTER build_deck + the gloss-polish/merge stage for the chapter. Idempotent: re-running
refreshes glosses but keeps each word's FIRST-taught chapter (so it's never self-suppressed).
A word retaught later in a divergent sense gets its extra gloss appended, so still-later
chapters suppress that meaning too.

Usage: python update_taught.py 1
"""
import os, json, sys
from taught_ledger import DATA, load_ledger, save_ledger

ch = int(sys.argv[1])
cards = json.load(open(os.path.join(DATA, f"cards_ch{ch}_{ch}.json"), encoding="utf-8"))
pp = os.path.join(DATA, f"gloss_polish_ch{ch}.json")
polish = json.load(open(pp, encoding="utf-8")) if os.path.exists(pp) else {}

led = load_ledger()
entries = led["entries"]
added = extra = 0
for c in cards:
    w = c["word"]
    gloss = (polish.get(w) or c.get("meaning") or "").strip()
    if w not in entries:
        entries[w] = {
            "reading": c["reading"], "chapter": ch,
            "multi_sense": len(c.get("candidates", [])) > 1,
            "glosses": [gloss] if gloss else [],
            "candidates": c.get("candidates", []),
        }
        added += 1
    else:
        e = entries[w]
        if gloss and gloss not in e["glosses"]:
            e["glosses"].append(gloss); extra += 1
if ch not in led["built_chapters"]:
    led["built_chapters"].append(ch); led["built_chapters"].sort()
save_ledger(led)
print(f"ch{ch}: {len(cards)} cards -> ledger now {len(entries)} words "
      f"(+{added} new, {extra} extra senses); built chapters {led['built_chapters']}")
