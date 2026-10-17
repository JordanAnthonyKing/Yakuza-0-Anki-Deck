"""Append speaker-descriptor label cards to an ALREADY-BUILT chapter, in place.

build_deck's Phase 3 does this at build time for new chapters; this is for chapters built
before speakers were per-line (msg_speakers.py) and DESC_HEAD was widened. Never rebuilds:
new cards go after the current max order (safe for the FROZEN cards_ch1_1.json), only
words untaught ANYWHERE (known/pretaught/name_block/ledger/this chapter) are added.

Also prints each label's official English name (index-parallel wdr/ name table) to seed
the translation range file. Afterwards: add glosses to gloss_polish_ch{ch}.json, write
data/translate/ch{ch}/{lo}-{hi}.json, then update_taught {ch} + build_final {ch}.

Usage: python append_label_cards.py <ch> [--write]
"""
import os, re, sys, json
import fugashi
import build_deck as BD
from taught_ledger import load_ledger, suppression_sets
from msg_speakers import names

ch, write = int(sys.argv[1]), "--write" in sys.argv
D = BD.DATA
known = json.load(open(os.path.join(D, "known_words.json"), encoding="utf-8"))
kw, kr = set(known["words"]), set(known["readings"])
pre = json.load(open(os.path.join(D, "pretaught_words.json"), encoding="utf-8"))
kw |= set(pre["words"]); kr |= set(pre["readings"])
for e in json.load(open(os.path.join(D, "name_block.json"), encoding="utf-8")):
    if e.get("surface"): kw.add(e["surface"])
    if e.get("reading"): kr.add(e["reading"])
sw, sr = suppression_sets(load_ledger(), before_chapter=99); kw |= sw; kr |= sr

path = os.path.join(D, f"cards_ch{ch}_{ch}.json")
cards = json.load(open(path, encoding="utf-8"))
have = {c["word"] for c in cards}
dia = json.load(open(os.path.join(D, "dialogue_by_chapter.json"), encoding="utf-8"))
jm, tagger = BD.load_jmdict(), fugashi.Tagger()
SRC = os.path.join(os.path.dirname(D), "source")

def official_label(label):
    for r in dia[str(ch)]:
        if r["speaker"] != label:
            continue
        jp = os.path.join(SRC, "wdrj", "msg", f"uid{r['uid'][:2]}xxxxxx", f"uid{r['uid']}.msg")
        ja, en = names(jp), names(jp.replace(os.sep + "wdrj" + os.sep, os.sep + "wdr" + os.sep))
        if label in ja and ja.index(label) < len(en):
            return en[ja.index(label)]
    return ""

order, new, seen = max(c["order"] for c in cards) + 1, [], set()
for row in dia[str(ch)]:
    s = (row.get("speaker") or "").strip()
    if not s or s in seen or re.search(r"[0-9０-９]", s) or not BD.DESC_HEAD.search(s):
        continue
    seen.add(s)
    pseudo = {"line": s, "uid": f"label-ch{ch}", "speaker": "〔人物呼称〕", "chapter": ch}
    for t in BD.content_tokens(s, tagger, kw, kr, jm):
        if t["lemma"] in have or (s, t["lemma"]) in BD.LABEL_SKIP:
            continue
        c = BD.make_card(pseudo, t, jm, order, "label", standalone=True)
        new.append(c); have.add(t["lemma"]); order += 1
        print(f"  order {c['order']}: {c['word']} ({c['reading']}) in 「{s}」 official: {official_label(s)!r}")
        print(f"      senses: {' | '.join(c['candidates'][:4])}")

print(f"Ch{ch}: {len(new)} label card(s) to append")
if write and new:
    json.dump(cards + new, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("   written", path)
