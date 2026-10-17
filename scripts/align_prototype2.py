"""Refined alignment test: instead of raw runs, extract ordered *meaningful* strings
(JA: contains kana/kanji; EN: contains a real word = >=3 letters incl. a vowel) and
align by index within each parallel file. Measures file-level count parity and example
coverage, to judge whether Option A works without full .msg format parsing.
"""
import os, re, glob, json

BASE = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad"
DATA = r"C:\Users\jordan\repos\yakuza\data"
JP  = re.compile(r"[぀-ヿ一-龯ｦ-ﾟ]")
ENWORD = re.compile(r"[A-Za-z]*[aeiouAEIOU][A-Za-z]*[A-Za-z]")  # >=word-ish

def clean(r):
    r = re.sub(r"<[^>]*>", "", r).strip()
    r = re.sub(r"[%＆][sd&Rr]", "", r).strip()
    return r

def strings(path, ja):
    text = open(path, "rb").read().decode("utf-8", "replace")
    out = []
    for r in re.split(r"[\x00-\x1f�]+", text):
        r = clean(r)
        if not r:
            continue
        if ja:
            if JP.search(r):
                out.append(r)
        else:
            if len(r) >= 3 and ENWORD.search(r):
                out.append(r)
    return out

amap = {}
match = mism = 0
for jp in glob.glob(os.path.join(BASE, "wdrj", "**", "*.*"), recursive=True):
    rel = os.path.relpath(jp, os.path.join(BASE, "wdrj"))
    ep = os.path.join(BASE, "wdr", rel)
    if not os.path.exists(ep):
        continue
    ja, en = strings(jp, True), strings(ep, False)
    if len(ja) == len(en) and ja:
        match += 1
        for a, b in zip(ja, en):
            amap.setdefault(a, b)
    elif ja or en:
        mism += 1
print(f"filtered-string count MATCH={match}  MISMATCH={mism}")
print(f"aligned JA->EN pairs: {len(amap)}")

buckets = json.load(open(os.path.join(DATA, "ch0_buckets.json"), encoding="utf-8"))
cand = {c["word"]: c for c in json.load(open(os.path.join(DATA, "candidates_ch0.json"), encoding="utf-8"))}
exs = [(c["word"], c["example"]) for b in ("CORE","MINIGAME") for c in buckets[b] if c["example"]]
hit = 0; samples = []
for word, ex in exs:
    en = amap.get(ex)
    if not en:
        for raw in cand.get(word, {}).get("examples", []):
            if (ex in raw or raw in ex) and amap.get(raw):
                en = amap[raw]; break
    if en:
        hit += 1
        if len(samples) < 15: samples.append((word, ex, en))
print(f"deck examples aligned: {hit}/{len(exs)}")
for w,e,en in samples:
    print(f"  {w}: {e[:32]} -> {en[:50]}")
