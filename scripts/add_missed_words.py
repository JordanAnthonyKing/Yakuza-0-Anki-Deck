"""Insert words the old 非自立可能 filter hid (組を抜ける, 迷惑を掛ける ...) into the built
story decks at their earliest true i+1 spot, without changing any existing card.

Missed words = lemmas content_tokens() yields now (standalone_aux_verb) but did not before.
Per chapter, in story order: replay the chapter's existing cards in deck order as the
learner's growing vocabulary; before each card, a missed word whose chapter line has it as
the ONLY unknown is introduced there (inserted in the list before that card). Words with no
i+1 line in a chapter are carried to later chapters. New cards get fresh `order` numbers
(max + 1 ...), so every order-keyed translation/audio file stays attached; build_final emits
cards in file order, so the inserted position is the deck position.

Usage: python add_missed_words.py            dry run: print the plan
       python add_missed_words.py --write    insert into data/cards_ch*_*.json
"""
import os, sys, json, glob, re
import fugashi
import build_deck
from build_deck import DATA, content_tokens, load_jmdict, make_card
from taught_ledger import load_ledger, load_divergent, suppression_sets

sys.stdout.reconfigure(encoding="utf-8")
WRITE = "--write" in sys.argv
CHAPTERS = sorted(int(re.search(r"cards_ch(\d+)_", p).group(1))
                  for p in glob.glob(os.path.join(DATA, "cards_ch*_*.json")) if "cards_ch0_" not in p)

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
ledger = load_ledger()

# lines that would teach a missed word wrongly: a tokenizer misparse or a fixed phrase
SKIP_LINES = {
    "抜く": ["ぬかせ"],                   # アホぬかせ = 抜かす "to spout", not 抜く
    "通す": ["張り通"],                   # 張り通す is its own compound
}
# ござる is only worth teaching as the polite copula でございます, not in greetings
# (ありがとう/おはようございます) the learner already knows as fixed phrases
ONLY_LINES = {"御座る": "でござい"}

def tokens(line, kw, kr, relaxed):
    if relaxed:
        return list(content_tokens(line, tagger, kw, kr, jm))
    keep, build_deck.standalone_aux_verb = build_deck.standalone_aux_verb, lambda t, b: False
    try:
        return list(content_tokens(line, tagger, kw, kr, jm))
    finally:
        build_deck.standalone_aux_verb = keep

# lemmas only reachable through the relaxed rule, anywhere in the story
old_l, new_l = set(), set()
for ch in CHAPTERS:
    for row in dia.get(str(ch), []):
        old_l |= {t["lemma"] for t in tokens(row["line"], base_w, base_r, False)}
        new_l |= {t["lemma"] for t in tokens(row["line"], base_w, base_r, True)}
missed = new_l - old_l
print(f"missed words in the story: {len(missed)}: {' '.join(sorted(missed))}")

placed = {}                                   # lemma -> chapter
plan = []
for ch in CHAPTERS:
    sup_w, sup_r = suppression_sets(ledger, before_chapter=ch, keep=load_divergent(ch))
    kw, kr = base_w | sup_w | set(placed), base_r | sup_r
    lines = [dict(row, chapter=ch, toks=tokens(row["line"], kw, kr, True)) for row in dia.get(str(ch), [])]
    path = os.path.join(DATA, f"cards_ch{ch}_{ch}.json")
    cards = json.load(open(path, encoding="utf-8"))
    cand = {t["lemma"] for ln in lines for t in ln["toks"]} & missed - set(placed)
    if not cand:
        continue
    learned, inserts = set(), []              # inserts: (position, card)
    nxt = max(c["order"] for c in cards) + 1
    for p in range(len(cards) + 1):
        changed = True
        while changed:
            changed = False
            for w in sorted(cand - set(placed)):
                for ln in lines:
                    if any(x in ln["line"] for x in SKIP_LINES.get(w, [])):
                        continue
                    if w in ONLY_LINES and ONLY_LINES[w] not in ln["line"]:
                        continue
                    unknown = {t["lemma"] for t in ln["toks"]} - learned - {x for x in placed if placed[x] == ch}
                    if unknown == {w}:
                        tok = next(t for t in ln["toks"] if t["lemma"] == w)
                        card = make_card(ln, tok, jm, nxt, "i+1"); nxt += 1
                        if tok.get("base_reading"):   # JMdict's first reading can be another word's (回る: めぐる)
                            card["reading"] = tok["base_reading"]
                        inserts.append((p, card))
                        placed[w] = ch; changed = True
                        break
        if p < len(cards):
            learned.add(cards[p]["word"])
    for p, c in inserts:
        before = cards[p]["word"] if p < len(cards) else "(end)"
        plan.append((ch, c["word"], c["reading"], p, before, re.sub("<[^>]+>", "", c["sentence"])))
    if WRITE and inserts:
        for p, c in sorted(inserts, key=lambda pc: -pc[0]):   # from the back so positions hold
            cards.insert(p, c)
        json.dump(cards, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

for ch, w, r, p, before, s in plan:
    print(f"  ch{ch:<2} {w} ({r})  at #{p} before 「{before}」  {s}")
left = sorted(missed - set(placed))
print(f"placed {len(placed)}; no i+1 line anywhere: {len(left)}: {' '.join(left)}")
if not WRITE:
    print("(dry run - nothing written)")
