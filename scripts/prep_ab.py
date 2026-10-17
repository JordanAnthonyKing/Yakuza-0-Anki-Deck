"""Prep one batch (a card range) for the Opus-vs-Sonnet A/B. Both models read the SAME
file. Usage: python prep_ab.py <start_order> <count>
"""
import os, json, sys
DATA = r"C:\Users\jordan\repos\yakuza\data"
SCRATCH = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\661dd7e3-534c-470c-9106-33c76f67f358\scratchpad"
start = int(sys.argv[1]); count = int(sys.argv[2])
rows = sorted(json.load(open(os.path.join(DATA, "align_ch1.json"), encoding="utf-8")), key=lambda r: r["order"])
sub = [r for r in rows if start <= r["order"] < start + count]
slim = [{"order": r["order"], "word": r["word"], "reading": r["reading"], "meaning": r["meaning"],
         "speaker": r["speaker"], "sentence": r["sentence"],
         "official_candidate": r["official_candidate"], "official_neighbors": r["official_neighbors"]} for r in sub]
p = os.path.join(SCRATCH, "ab_batch.json")
json.dump(slim, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {p}: {len(slim)} cards (orders {slim[0]['order']}-{slim[-1]['order']})")
