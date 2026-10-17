"""Split candidates_ch0.json into N batches for the classify+gloss subagents.
Usage: python prep_classify_batches.py [nbatches]
"""
import os, json, sys

DATA = r"C:\Users\jordan\repos\yakuza\data"
SCRATCH = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\661dd7e3-534c-470c-9106-33c76f67f358\scratchpad"

nb = int(sys.argv[1]) if len(sys.argv) > 1 else 12
cand = json.load(open(os.path.join(DATA, "candidates_ch0.json"), encoding="utf-8"))
# keep only the fields the subagent needs
slim = [{"word": c["word"], "reading": c["reading"], "pos": c["pos"],
         "mini_ratio": c["mini_ratio"], "candidates": c["candidates"],
         "examples": c["examples"]} for c in cand]

size = (len(slim) + nb - 1) // nb
os.makedirs(SCRATCH, exist_ok=True)
paths = []
for i in range(nb):
    chunk = slim[i*size:(i+1)*size]
    if not chunk:
        continue
    p = os.path.join(SCRATCH, f"classify_batch_{i+1}.json")
    json.dump(chunk, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    paths.append((p, len(chunk)))
print(f"{len(slim)} candidates -> {len(paths)} batches of ~{size}")
for p, n in paths:
    print(f"  {n:4}  {p}")
