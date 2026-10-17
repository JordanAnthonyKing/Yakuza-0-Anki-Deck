"""Merge divergence-gate parts -> data/sense_divergent_ch{N}.json (list of words to reteach).

Words the agents flagged as tokenizer misparses ("__flags__") are forced OUT of the divergent
set (a fake word must never be retaught) and saved to sense_divergent_ch{N}_flags.json for
the orchestrator's review.

Usage: python combine_divergence.py 2
"""
import os, json, sys, glob
from taught_ledger import DATA

ch = int(sys.argv[1])
judged, flags = {}, {}
for p in sorted(glob.glob(os.path.join(DATA, f"divergence_ch{ch}_part*.json"))):
    d = json.load(open(p, encoding="utf-8"))
    flags.update(d.pop("__flags__", {}) or {})
    judged.update(d)
    print(f"  {os.path.basename(p)}: {len(d)} words")

divergent = sorted(w for w, keep in judged.items() if keep and w not in flags)
out = os.path.join(DATA, f"sense_divergent_ch{ch}.json")
json.dump(divergent, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(flags, open(os.path.join(DATA, f"sense_divergent_ch{ch}_flags.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"{len(judged)} judged -> {len(divergent)} divergent (reteach): {' '.join(divergent) or '(none)'}")
if flags:
    print(f"misparse flags (kept out of the divergent set): " + "; ".join(f"{w}: {r}" for w, r in flags.items()))
print(f"wrote {out}  -> now run: python build_deck.py {ch}")
