"""Flag cards whose word is (part of) a character's speaker name appearing in its sentence.

Every character with dialogue appears as a speaker name, so this catches name leaks that
name_leak_scan.py (which only knows names_curated.json) misses — e.g. 山形 (Yamagata) taught
as the city. Descriptor labels (小太りの男 …) are excluded. Prints suspects for review only.

Usage: python speaker_name_scan.py <ch> [<ch> ...]
"""
import os, re, sys, json, collections
import build_deck as BD

dia = json.load(open(os.path.join(BD.DATA, "dialogue_by_chapter.json"), encoding="utf-8"))
spk = collections.Counter(r["speaker"] for v in dia.values() for r in v if r["speaker"])
names = {s for s in spk if not BD.DESC_HEAD.search(s) and "の" not in s and len(s) <= 6}
for ch in [int(a) for a in sys.argv[1:]]:
    for c in json.load(open(os.path.join(BD.DATA, f"cards_ch{ch}_{ch}.json"), encoding="utf-8")):
        w, plain = c["word"], re.sub(r"<[^>]+>", "", c["sentence"])
        for n in names:
            if (w == n or (len(w) >= 2 and w in n)) and n in plain:
                print(f"ch{ch} order {c['order']}: {w} ⊂ speaker {n} | {plain[:50]}")
