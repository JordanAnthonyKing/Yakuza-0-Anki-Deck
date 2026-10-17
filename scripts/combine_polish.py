"""Merge the per-batch polish partials into one gloss_polish_ch{lo}.json.

Misparse flags ("__flags__") are split out to gloss_polish_ch{lo}_flags.json — candidates
for drop_cards.py once the orchestrator has reviewed them.

Usage: python combine_polish.py 1
"""
import os, json, sys, glob

REPO = r"C:\Users\jordan\repos\yakuza"
DATA = os.path.join(REPO, "data")

lo = int(sys.argv[1])
merged, flags = {}, {}
parts = sorted(glob.glob(os.path.join(DATA, f"gloss_polish_ch{lo}_part*.json")))
for p in parts:
    d = json.load(open(p, encoding="utf-8"))
    flags.update(d.pop("__flags__", {}) or {})
    merged.update(d)
    print(f"  {os.path.basename(p)}: {len(d)} words")

out = os.path.join(DATA, f"gloss_polish_ch{lo}.json")
json.dump(merged, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(flags, open(os.path.join(DATA, f"gloss_polish_ch{lo}_flags.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"merged {len(parts)} parts -> {len(merged)} words -> {out}")
if flags:
    print(f"misparse flags: " + "; ".join(f"{w}: {r}" for w, r in flags.items()))
