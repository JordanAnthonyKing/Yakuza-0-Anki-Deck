"""Feasibility test for aligning JA example sentences to the official English (wdr).
Parallel-walks wdrj/wdr, splits each file into positional runs, and builds a
cleaned-JA -> EN map for runs at the same index. Then measures coverage against the
example sentences already chosen for the Ch0 + minigame decks.
"""
import os, re, glob, json, collections

BASE = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad"
DATA = r"C:\Users\jordan\repos\yakuza\data"
JP  = re.compile(r"[぀-ヿ一-龯ｦ-ﾟ]")
LAT = re.compile(r"[A-Za-z]")

def clean(r):
    r = re.sub(r"<[^>]*>", "", r).strip()
    r = re.sub(r"[%＆][sd&Rr]", "", r).strip()
    return r

def raw_runs(path):
    text = open(path, "rb").read().decode("utf-8", "replace")
    return re.split(r"[\x00-\x1f�]+", text)

ja_files = glob.glob(os.path.join(BASE, "wdrj", "**", "*.*"), recursive=True)
match_files = mismatch_files = 0
amap = {}
for jp in ja_files:
    rel = os.path.relpath(jp, os.path.join(BASE, "wdrj"))
    ep = os.path.join(BASE, "wdr", rel)
    if not os.path.exists(ep):
        continue
    ja, en = raw_runs(jp), raw_runs(ep)
    if len(ja) == len(en):
        match_files += 1
        for a, b in zip(ja, en):
            a, b = clean(a), clean(b)
            if a and JP.search(a) and b and LAT.search(b):
                amap.setdefault(a, b)   # first occurrence wins
    else:
        mismatch_files += 1

print(f"parallel files: run-count MATCH={match_files}  MISMATCH={mismatch_files}")
print(f"JA->EN aligned string pairs: {len(amap)}")

# coverage against our deck example sentences (both trimmed classify output and raw candidates)
buckets = json.load(open(os.path.join(DATA, "ch0_buckets.json"), encoding="utf-8"))
cand = {c["word"]: c for c in json.load(open(os.path.join(DATA, "candidates_ch0.json"), encoding="utf-8"))}
exs = []
for b in ("CORE", "MINIGAME"):
    for c in buckets[b]:
        if c["example"]:
            exs.append((c["word"], c["example"]))
hit = miss = 0
samples = []
for word, ex in exs:
    en = amap.get(ex)
    if not en:                                   # try untrimmed candidate example lines
        for raw in cand.get(word, {}).get("examples", []):
            if ex in raw and amap.get(raw):
                en = amap[raw]; break
    if en:
        hit += 1
        if len(samples) < 12:
            samples.append((word, ex, en))
    else:
        miss += 1
print(f"\ndeck example sentences: {len(exs)}  aligned to official EN: {hit}  miss: {miss}")
for word, ex, en in samples:
    print(f"  {word}: {ex[:34]}  ->  {en[:52]}")
