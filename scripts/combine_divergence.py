"""Merge divergence-gate parts -> data/sense_divergent_ch{N}.json (list of words to reteach).

Usage: python combine_divergence.py 2
"""
import os, json, sys, glob
from taught_ledger import DATA

ch = int(sys.argv[1])
judged = {}
for p in sorted(glob.glob(os.path.join(DATA, f"divergence_ch{ch}_part*.json"))):
    d = json.load(open(p, encoding="utf-8"))
    judged.update(d)
    print(f"  {os.path.basename(p)}: {len(d)} words")

divergent = sorted(w for w, keep in judged.items() if keep)
out = os.path.join(DATA, f"sense_divergent_ch{ch}.json")
json.dump(divergent, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(judged)} judged -> {len(divergent)} divergent (reteach): {' '.join(divergent) or '(none)'}")
print(f"wrote {out}  -> now run: python build_deck.py {ch}")
