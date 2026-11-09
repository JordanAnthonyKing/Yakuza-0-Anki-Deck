"""Teach compound words the tokenizer splits into parts the learner already knows.

unidic cuts 情報屋 into 情報 (known) + 屋 (suffix, dropped) and 不動産 into 不 + 動産, so these
compounds never became cards -- or worse, the deck taught a FRAGMENT from the compound's line
(動産 "personal property" for 不動産, 伯父 "uncle" for オッサン). data/compounds.json is the
hand-curated list of compounds whose meaning is NOT obvious from their parts (unknown part,
part in a secondary sense like 屋 = "dealer in", idiom, or changed reading); transparent ones
(大成功, 被害者, お金, 営業中) are deliberately absent.

Per entry: reading, meaning, pos, and optionally
  match       surfaces to find in a line (default [word]); longest first
  repoint     [[ch, order], ...] fragment cards to turn INTO this compound in place (same
              position, same Anki GUID via c["guid"])
  drop        [[ch, order], ...] further fragment cards from this compound's lines to remove
  alias       never carded; counts as learned once the named compound is (ご存知 -> 御存知)
  skip_lines  substrings of lines that must not teach it (お使いください = honorific 使う)

Then, as add_missed_words.py does, every compound without a card -- and every fragment the
repoints displaced that still occurs on its own -- is inserted at its earliest i+1 line
(replaying each chapter's cards as the growing vocabulary), with fresh `order` numbers so all
order-keyed translation/audio files stay attached. A word with no i+1 line anywhere goes in
just before the first card that comes after its first line (an i+2 card).

Usage: python add_compounds.py            dry run: print the plan
       python add_compounds.py --write    rewrite data/cards_ch*_*.json, gloss_polish, ledger
"""
import os, sys, json, glob, re
import fugashi
from build_deck import DATA, content_tokens, load_jmdict, make_card, strip_orphan_brackets
from keep_guids import old_guids, _key

sys.stdout.reconfigure(encoding="utf-8")
WRITE = "--write" in sys.argv
CHAPTERS = sorted(int(re.search(r"cards_ch(\d+)_", p).group(1))
                  for p in glob.glob(os.path.join(DATA, "cards_ch*_*.json")) if "cards_ch0_" not in p)
plain = lambda s: re.sub(r"<[^>]+>", "", s)

COMP = json.load(open(os.path.join(DATA, "compounds.json"), encoding="utf-8"))
SURF = sorted(((s, w) for w, e in COMP.items() for s in e.get("match", [w])), key=lambda x: -len(x[0]))
canon = lambda w: COMP[w].get("alias", w)

known = json.load(open(os.path.join(DATA, "known_words.json"), encoding="utf-8"))
pre = json.load(open(os.path.join(DATA, "pretaught_words.json"), encoding="utf-8"))
base_w = set(known["words"]) | set(pre["words"])
base_r = set(known["readings"]) | set(pre["readings"])
for e in json.load(open(os.path.join(DATA, "name_block.json"), encoding="utf-8")):
    if e.get("surface"): base_w.add(e["surface"])
    if e.get("reading"): base_r.add(e["reading"])
dia = json.load(open(os.path.join(DATA, "dialogue_by_chapter.json"), encoding="utf-8"))
jm = load_jmdict()
tagger = fugashi.Tagger()

def spans(line):
    """[(start, end, compound)] non-overlapping compound occurrences, longest match wins."""
    got = []
    for s, w in SURF:
        for m in re.finditer(re.escape(s), line):
            if not any(a < m.end() and m.start() < b for a, b, _ in got):
                if not any(x in line for x in COMP[w].get("skip_lines", [])):
                    got.append((m.start(), m.end(), w))
    return sorted(got)

def line_words(line):
    """(content tokens outside compound spans, compounds present) for one line."""
    sp = spans(line)
    toks, pos = [], 0
    for t in content_tokens(line, tagger, base_w, base_r, jm):
        k = line.find(t["surface"], pos)
        if k < 0:
            k = pos
        pos = k + len(t["surface"])
        if not any(a <= k < b for a, b, _ in sp):
            toks.append(t)
    return toks, [w for _, _, w in sp]

def bold(sentence, surfaces):
    s = plain(sentence)
    for x in surfaces:
        if x in s:
            return s.replace(x, f"<b>{x}</b>", 1)
    raise ValueError(f"none of {surfaces} in {s}")

def compound_card(ln, w, order, kind):
    e = COMP[w]
    return {"order": order, "kind": kind, "standalone": False,
            "sentence": bold(strip_orphan_brackets(ln["line"]), e.get("match", [w])),
            "word": w, "reading": e["reading"], "meaning": e["meaning"], "pos": e["pos"],
            "chapter": ln["chapter"], "speaker": ln.get("speaker") or "", "uid": ln["uid"],
            "candidates": []}

decks = {ch: json.load(open(os.path.join(DATA, f"cards_ch{ch}_{ch}.json"), encoding="utf-8")) for ch in CHAPTERS}
polish = {ch: json.load(open(os.path.join(DATA, f"gloss_polish_ch{ch}.json"), encoding="utf-8")) for ch in CHAPTERS}

# ---- 1. repoint / drop fragment cards ----
displaced, log = set(), []
for w, e in COMP.items():
    for ch, order in e.get("repoint", []):
        c = next(c for c in decks[ch] if c["order"] == order)
        if c["word"] == w:
            continue                                   # already applied
        sent = strip_orphan_brackets(c["sentence"])
        old = old_guids(os.path.join(DATA, "decks", f"yakuza0_ch{ch}.apkg"))
        c["guid"] = c.get("guid") or old[_key([sent, c["word"]], 2)]
        log.append(f"  ch{ch:<2} o{order:<4} {c['word']} -> {w}   {plain(c['sentence'])[:40]}")
        displaced.add(c["word"])
        c.update(sentence=bold(c["sentence"], e.get("match", [w])), word=w, reading=e["reading"],
                 meaning=e["meaning"], pos=e["pos"], candidates=[])
    for ch, order in e.get("drop", []):
        c = next((c for c in decks[ch] if c["order"] == order), None)
        if c:
            log.append(f"  ch{ch:<2} o{order:<4} {c['word']} dropped ({w} line)")
            displaced.add(c["word"])
            decks[ch].remove(c)
print(f"repointed/dropped {len(log)} fragment cards:"); print("\n".join(log))
carded = {c["word"] for cs in decks.values() for c in cs}
displaced -= carded
displaced -= {"真"}          # its only other hits are tokenizer splits of the name 真島

# ---- 2. insert at the earliest i+1 line ----
targets = {w for w in COMP if "alias" not in COMP[w] and w not in carded} | displaced
lines = {ch: [] for ch in CHAPTERS}
for ch in CHAPTERS:
    for i, row in enumerate(dia.get(str(ch), [])):
        toks, comps = line_words(row["line"])
        lines[ch].append(dict(row, chapter=ch, idx=i, toks=toks, comps=comps))

def unknown(ln, learned_w, learned_r):
    u = {t["lemma"] for t in ln["toks"] if t["lemma"] not in learned_w
         and t["reading"] not in learned_r and t["base_reading"] not in learned_r}
    return u | {canon(w) for w in ln["comps"] if canon(w) not in learned_w}

placed, plan = {}, []
learned_w, learned_r = set(base_w), set(base_r)
for ch in CHAPTERS:
    cards = decks[ch]
    present = {t["lemma"] for ln in lines[ch] for t in ln["toks"]} | {canon(w) for ln in lines[ch] for w in ln["comps"]}
    cand = (targets & present) - set(placed)
    nxt = max(c["order"] for c in cards) + 1
    inserts = []
    for p in range(len(cards) + 1):
        changed = True
        while changed:
            changed = False
            for w in sorted(cand - set(placed)):
                for ln in lines[ch]:
                    if unknown(ln, learned_w, learned_r) == {w}:
                        if w in COMP:
                            card = compound_card(ln, w, nxt, "i+1")
                        else:
                            tok = next(t for t in ln["toks"] if t["lemma"] == w)
                            card = make_card(ln, tok, jm, nxt, "i+1")
                            if tok.get("base_reading"):
                                card["reading"] = tok["base_reading"]
                        nxt += 1
                        inserts.append((p, card)); placed[w] = ch
                        learned_w.add(w); changed = True
                        break
        if p < len(cards):
            learned_w.add(cards[p]["word"]); learned_r.add(cards[p]["reading"])
    for p, c in sorted(inserts, key=lambda pc: -pc[0]):
        cards.insert(p, c)
    plan += [(ch, c, "i+1") for _, c in inserts]

# fallback: no i+1 line anywhere -> before the first card that follows its first line
def card_line(ch, c):
    s = plain(c["sentence"])
    return next((ln["idx"] for ln in lines[ch] if ln["uid"] == c["uid"] and s in strip_orphan_brackets(ln["line"])), None)

for w in sorted(targets - set(placed)):
    ch, ln = next(((ch, ln) for ch in CHAPTERS for ln in lines[ch]
                   if w in {t["lemma"] for t in ln["toks"]} | {canon(x) for x in ln["comps"]}), (None, None))
    if ch is None:
        print(f"  {w}: no longer occurs outside a compound -- not reinserted"); continue
    cards = decks[ch]
    order = max(c["order"] for c in cards) + 1
    if w in COMP:
        card = compound_card(ln, w, order, "grp")
    else:
        tok = next(t for t in ln["toks"] if t["lemma"] == w)
        card = make_card(ln, tok, jm, order, "grp")
        if tok.get("base_reading"):
            card["reading"] = tok["base_reading"]
    p = next((i for i, c in enumerate(cards) if (card_line(ch, c) or -1) > ln["idx"]), len(cards))
    cards.insert(p, card); placed[w] = ch
    plan.append((ch, card, "i+2"))

print(f"\ninserted {len(plan)} cards:")
for ch, c, k in sorted(plan, key=lambda x: x[0]):
    pos = decks[ch].index(c)
    print(f"  ch{ch:<2} #{pos:<4} {k} {c['word']} ({c['reading']}) = {c['meaning'][:40]} | {plain(c['sentence'])[:36]}")

if not WRITE:
    print("(dry run - nothing written)"); sys.exit()

for ch in CHAPTERS:
    for c in decks[ch]:
        if c["word"] in COMP:
            polish[ch][c["word"]] = COMP[c["word"]]["meaning"]
    json.dump(decks[ch], open(os.path.join(DATA, f"cards_ch{ch}_{ch}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(polish[ch], open(os.path.join(DATA, f"gloss_polish_ch{ch}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# taught ledger: compounds in, fragments that no longer have a card out
from taught_ledger import load_ledger, save_ledger
led = load_ledger()
first = {}
for ch in CHAPTERS:
    for c in decks[ch]:
        first.setdefault(c["word"], (ch, c))
for w in displaced - set(first):
    led["entries"].pop(w, None)
for w, (ch, c) in first.items():
    if w in COMP or w in placed:
        led["entries"][w] = {"reading": c["reading"], "chapter": ch, "multi_sense": False,
                             "glosses": [polish[ch].get(w) or c["meaning"]], "candidates": c.get("candidates", [])}
save_ledger(led)
print("written")
