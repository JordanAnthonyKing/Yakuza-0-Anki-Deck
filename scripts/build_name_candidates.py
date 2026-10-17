"""Build a candidate pool of character/place/org NAMES for the Characters & Places deck.

Names are proper nouns, deliberately excluded from the vocab decks. Sources:
  - speaker field frequency (the actual cast) -- the primary signal
  - proper-noun tokens tagged 地名 (place) / organisation-ish, from dialogue text
A light prefilter drops obvious menu/choice junk; generic descriptors (男/女/声/...) are
kept but flagged, for the curation subagent to drop. Output: data/name_candidates.json.

Usage: python build_name_candidates.py
"""
import os, json, re
from collections import Counter
from build_deck import DATA, kata2hira
import fugashi

dia = json.load(open(os.path.join(DATA, "dialogue_by_chapter.json"), encoding="utf-8"))

# 1. speakers with frequency + first chapter seen
spk = Counter(); first_ch = {}
for ch, rows in dia.items():
    for row in rows:
        s = (row.get("speaker") or "").strip()
        if s:
            spk[s] += 1
            first_ch.setdefault(s, int(ch))

# obvious non-name menu/choice junk
JUNK = re.compile(r"[0-9０-９]|円|払|獲得|場所|こと|ホステスの|店舗")
# generic descriptor (role, not a name) -- flagged, subagent drops
DESC = re.compile(r"(男|女|声|組員|店長|客|者|仲間|老人|人の|っ払い|ヤクザ|極道|タクシー|謎)")

cands = {}
for name, n in spk.most_common():
    if n < 12:
        break
    if JUNK.search(name):
        continue
    cands[name] = {"name": name, "freq_speaker": n, "freq_text": 0,
                   "first_chapter": first_ch.get(name), "source": "speaker",
                   "descriptor_flag": bool(DESC.search(name))}

# 2. proper-noun place/org tokens from text (catch key locations not in speaker list)
tagger = fugashi.Tagger()
prop = Counter(); psub = {}
for ch, rows in dia.items():
    for row in rows:
        for t in tagger(row["line"]):
            if t.feature.pos2 == "固有名詞" and t.feature.pos3 in ("地名",):
                prop[t.surface] += 1; psub[t.surface] = t.feature.pos3
for name, n in prop.most_common():
    if n < 12:
        break
    if name in cands:
        cands[name]["freq_text"] = n
        continue
    cands[name] = {"name": name, "freq_speaker": 0, "freq_text": n,
                   "first_chapter": None, "source": "place", "descriptor_flag": False}

out = sorted(cands.values(), key=lambda c: -(c["freq_speaker"] + c["freq_text"]))
json.dump(out, open(os.path.join(DATA, "name_candidates.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
kept = [c for c in out if not c["descriptor_flag"]]
print(f"{len(out)} candidates ({len(kept)} non-descriptor, {len(out)-len(kept)} flagged) -> data/name_candidates.json")
for c in out[:60]:
    flag = " [descriptor?]" if c["descriptor_flag"] else ""
    print(f"  spk{c['freq_speaker']:5} txt{c['freq_text']:4}  {c['name']}{flag}")
