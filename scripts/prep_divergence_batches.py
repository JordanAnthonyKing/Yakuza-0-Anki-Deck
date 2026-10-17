"""Emit review batches for the sense-divergence gate, to run BEFORE building chapter N.

Scans chapter N dialogue for words ALREADY taught in an earlier chapter that are multi-sense
(mono-sense words can't diverge, so they stay suppressed automatically). For each reoccurring
word it captures a chapter-N context sentence + the taught gloss(es) + the JMdict candidate
senses, so a subagent can judge: does ch N use a DRASTICALLY different meaning (=> reteach)
or the same one (=> keep suppressed)?

Usage: python prep_divergence_batches.py 2 [nbatches]
"""
import os, json, sys
import fugashi
from build_deck import content_tokens, load_jmdict, strip_orphan_brackets
from taught_ledger import DATA, load_ledger

SCRATCH = os.path.join(DATA, "work", f"ch{int(sys.argv[1])}")   # batch inputs live in the repo

ch = int(sys.argv[1]); nb = int(sys.argv[2]) if len(sys.argv) > 2 else 3

known = json.load(open(os.path.join(DATA, "known_words.json"), encoding="utf-8"))
known_w = set(known["words"]); known_r = set(known["readings"])
pre = json.load(open(os.path.join(DATA, "pretaught_words.json"), encoding="utf-8"))
known_w |= set(pre["words"]); known_r |= set(pre["readings"])
# NOTE: deliberately do NOT fold in the taught ledger here -- we WANT to see taught words.

led = load_ledger()
taught_multi = {w: e for w, e in led["entries"].items()
                if e["chapter"] < ch and e.get("multi_sense")}

dia = json.load(open(os.path.join(DATA, "dialogue_by_chapter.json"), encoding="utf-8"))
jm = load_jmdict()
tagger = fugashi.Tagger()

found = {}   # word -> review item; first occurrence in the chapter wins
for row in dia.get(str(ch), []):
    for t in content_tokens(row["line"], tagger, known_w, known_r, jm):
        w = t["lemma"]
        if w in taught_multi and w not in found:
            sent = strip_orphan_brackets(row["line"])
            if t["surface"] in sent:
                sent = sent.replace(t["surface"], f"<b>{t['surface']}</b>", 1)
            e = taught_multi[w]
            found[w] = {
                "word": w, "reading": e["reading"],
                "taught_gloss": "; ".join(e["glosses"]),
                "candidates": e["candidates"],
                "sentence": sent,
            }

items = list(found.values())
print(f"ch{ch}: {len(taught_multi)} taught multi-sense words, {len(items)} reoccur here")
if not items:
    print("no divergence review needed -> run build_deck directly")
    sys.exit(0)

size = (len(items) + nb - 1) // nb
os.makedirs(SCRATCH, exist_ok=True)
for i in range(nb):
    chunk = items[i*size:(i+1)*size]
    if not chunk:
        continue
    p = os.path.join(SCRATCH, f"divergence_batch_{ch}_{i+1}.json")
    json.dump(chunk, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  {len(chunk):4}  {p}")
print(f"\nspawn one subagent per batch (see scripts/divergence_prompt.txt); each writes")
print(f"data/divergence_ch{ch}_part{{N}}.json = {{word: true|false}}  (true = divergent = reteach)")
