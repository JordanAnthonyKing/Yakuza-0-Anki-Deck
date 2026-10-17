"""Decisive alignment test: split each .msg on NUL bytes into logical messages, strip
inline <tags> and join \r\n sub-lines, then align JA<->EN by message index within each
parallel file. Reports per-file count parity and checks correctness by locating our
deck example fragments inside the aligned JA message and showing the paired EN.
"""
import os, re, glob, json

BASE = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad"
DATA = r"C:\Users\jordan\repos\yakuza\data"
JP = re.compile(r"[぀-ヿ一-龯ｦ-ﾟ]")
ENW = re.compile(r"[A-Za-z]{2,}")
VOW = re.compile(r"[aeiouAEIOU]")

def msgs(path, ja):
    data = open(path, "rb").read()
    out = []
    for part in data.split(b"\x00"):
        s = part.decode("utf-8", "replace")
        s = re.sub(r"<[^>]*>", "", s)                 # strip inline tags
        s = re.sub(r"[\r\n]+", "", s)                 # join sub-lines
        s = s.replace("�", "").strip()
        if not s:
            continue
        if ja:
            if JP.search(s):
                out.append(s)
        else:
            if ENW.search(s) and VOW.search(s) and (len(s) >= 4 or " " in s):
                out.append(s)
    return out

# 1. per-file parity
files = glob.glob(os.path.join(BASE, "wdrj", "**", "*.*"), recursive=True)
match = mism = 0
amap = {}                     # exact JA message -> EN message (from count-matched files)
pair_files = {}              # rel -> (ja_list, en_list) for matched files
for jp in files:
    rel = os.path.relpath(jp, os.path.join(BASE, "wdrj"))
    ep = os.path.join(BASE, "wdr", rel)
    if not os.path.exists(ep):
        continue
    ja, en = msgs(jp, True), msgs(ep, False)
    if ja and len(ja) == len(en):
        match += 1
        pair_files[rel] = (ja, en)
        for a, b in zip(ja, en):
            amap.setdefault(a, b)
    elif ja:
        mism += 1
print(f"message-count parity: MATCH={match}  MISMATCH={mism}  ({100*match//max(1,match+mism)}%)")
print(f"exact JA->EN message pairs (from matched files): {len(amap)}")

# 2. correctness: find each deck example (a fragment) inside a matched JA message
buckets = json.load(open(os.path.join(DATA, "ch0_buckets.json"), encoding="utf-8"))
exs = [(c["word"], c["example"]) for b in ("CORE", "MINIGAME") for c in buckets[b] if c["example"]]
frag2en = {}
for ja, en in pair_files.values():
    for a, b in zip(ja, en):
        frag2en.setdefault(a, b)
hit = 0; samples = []
for word, ex in exs:
    exn = re.sub(r"[\r\n]+", "", re.sub(r"<[^>]*>", "", ex)).strip()
    found = None
    for a, b in frag2en.items():
        if exn and (exn in a or a in exn):
            found = (a, b); break
    if found:
        hit += 1
        if len(samples) < 16:
            samples.append((word, exn, found[1]))
print(f"\ndeck examples matched to an aligned EN message: {hit}/{len(exs)}")
for w, e, en in samples:
    print(f"  {w}: {e[:30]}  ->  {en[:56]}")
