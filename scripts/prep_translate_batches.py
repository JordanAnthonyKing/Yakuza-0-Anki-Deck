"""Split a subset of align_ch1.json into batches for the Opus translate+gate subagents.
Usage: python prep_translate_batches.py <subset_count> <nbatches>
"""
import os, json, sys

DATA = r"C:\Users\jordan\repos\yakuza\data"
SCRATCH = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\661dd7e3-534c-470c-9106-33c76f67f358\scratchpad"

n = int(sys.argv[1]); nb = int(sys.argv[2])
rows = json.load(open(os.path.join(DATA, "align_ch1.json"), encoding="utf-8"))
rows = sorted(rows, key=lambda r: r["order"])[:n]
slim = [{"order": r["order"], "word": r["word"], "reading": r["reading"],
         "meaning": r["meaning"], "speaker": r["speaker"], "sentence": r["sentence"],
         "official_candidate": r["official_candidate"],
         "official_neighbors": r["official_neighbors"]} for r in rows]

size = (len(slim) + nb - 1) // nb
paths = []
for i in range(nb):
    chunk = slim[i*size:(i+1)*size]
    if not chunk:
        continue
    p = os.path.join(SCRATCH, f"translate_batch_{i+1}.json")
    json.dump(chunk, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    paths.append((p, len(chunk)))
print(f"subset {len(slim)} cards -> {len(paths)} batches")
for p, c in paths:
    print(f"  {c:3}  {p}")
