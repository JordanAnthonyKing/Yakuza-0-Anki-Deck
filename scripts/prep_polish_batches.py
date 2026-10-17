"""Split multi-sense cards into batch files for the gloss-polish subagents.

Each batch is a list of {word, reading, pos, sentence, candidates}. Single-sense
cards are skipped (their default gloss is the only choice). Sentence keeps the
<b>...</b> target markup so the agent sees which token to disambiguate.

Usage: python prep_polish_batches.py 1 1 [nbatches]
"""
import os, json, sys, re

REPO = r"C:\Users\jordan\repos\yakuza"
DATA = os.path.join(REPO, "data")
SCRATCH = os.path.join(DATA, "work", f"ch{int(sys.argv[1])}")   # batch inputs live in the repo

lo = int(sys.argv[1]); hi = int(sys.argv[2]) if len(sys.argv) > 2 else lo
nb = int(sys.argv[3]) if len(sys.argv) > 3 else 5

cards = json.load(open(os.path.join(DATA, f"cards_ch{lo}_{hi}.json"), encoding="utf-8"))
multi = [c for c in cards if len(c["candidates"]) > 1]

items = [{
    "word": c["word"], "reading": c["reading"], "pos": c["pos"],
    "sentence": c["sentence"], "candidates": c["candidates"],
} for c in multi]

# de-dup by word: if the same lemma recurs, the first sentence context is enough
seen = {}
uniq = []
for it in items:
    if it["word"] in seen:
        continue
    seen[it["word"]] = 1
    uniq.append(it)

size = (len(uniq) + nb - 1) // nb
os.makedirs(SCRATCH, exist_ok=True)
paths = []
for i in range(nb):
    chunk = uniq[i*size:(i+1)*size]
    if not chunk:
        continue
    p = os.path.join(SCRATCH, f"polish_batch_{lo}_{i+1}.json")
    json.dump(chunk, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    paths.append((p, len(chunk)))

print(f"{len(multi)} multi-sense cards, {len(uniq)} unique words -> {len(paths)} batches")
for p, n in paths:
    print(f"  {n:4}  {p}")
