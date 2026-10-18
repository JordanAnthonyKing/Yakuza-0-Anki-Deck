"""Build an i+1 Yakuza-0 vocab Anki deck for a chapter range.

Pipeline: ordered dialogue -> fugashi tokens -> drop known/function words ->
JMdict gloss -> i+1 selection (introduce each new word in a sentence whose only
unknown is that word) -> genanki .apkg. Target word(s) go in a separate field.

Usage: python build_deck.py 1            # chapter 1
       python build_deck.py 1 3          # chapters 1..3
       python build_deck.py 0 0 system_by_chapter.json   # alt source (e.g. system/UI terms)
"""
import os, re, json, glob, sys, pickle
import fugashi, genanki

REPO = r"C:\Users\jordan\repos\yakuza"
DATA = os.path.join(REPO, "data")

# ---------- helpers ----------
KATA = {chr(c): chr(c - 0x60) for c in range(0x30A1, 0x30F7)}
def kata2hira(s): return "".join(KATA.get(ch, ch) for ch in s)

# In-game monologue is wrapped in fullwidth brackets that span multiple display
# sub-lines; sub-line splitting orphans a bracket at a fragment edge. Strip a bracket
# ONLY when it's unbalanced at the very start/end -- balanced pairs inside are kept.
_CLOSE2OPEN = {"）": "（", "」": "「", "』": "『", "】": "【", "》": "《", "〉": "〈", ")": "(", "]": "["}
_OPEN2CLOSE = {v: k for k, v in _CLOSE2OPEN.items()}
def strip_orphan_brackets(s):
    s = s.strip("　 ").strip()
    prev = None
    while s and s != prev:
        prev = s
        if s[-1] in _CLOSE2OPEN and s.count(_CLOSE2OPEN[s[-1]]) < s.count(s[-1]):
            s = s[:-1].strip("　 ").strip(); continue
        if s[0] in _OPEN2CLOSE and s.count(_OPEN2CLOSE[s[0]]) < s.count(s[0]):
            s = s[1:].strip("　 ").strip(); continue
    return s

CONTENT_POS = {"名詞", "動詞", "形容詞", "形状詞", "副詞"}
SKIP_POS2   = {"固有名詞", "数詞", "代名詞", "非自立可能"}
STOPLEMMA   = set("そう こう ああ どう よう もの こと の ん さん ちゃん くん さ ため 方 事 物 訳 為".split())
# Person-descriptor speaker labels: unnamed characters the game tags by description
# (e.g. 小太りの男 "chubby man", 謎の男 "mysterious man"). Their distinguishing words only
# appear in the speaker tag, never in a spoken line, so normal mining never teaches them.
# Phase 3 mines these into the chapter deck. Menu-choice speakers (諦める, 大丈夫だ, ...) are
# excluded because they don't end in a person-descriptor head noun. Widened 2026-10-17 once
# speakers became per-line (msg_speakers.py) and labels like 髭のホームレス / 今時の青年 /
# 守衛の組員 surfaced; tutorial/menu headings (〜について, 店舗の獲得) still don't match.
DESC_HEAD = re.compile(r"(男|女|声|者|老人|仲間|店員|店主|住人|子分|マフィア|ヤクザ|極道|医者|坊主|野郎|客|女将"
                       r"|組員|若衆|弟分|部下|ホームレス|ヤンキー|チンピラ|青年|少年|外国人|学生|ボーイ"
                       r"|マスター|店長|社長|部長|部員|運転手|受付|警察官|職人さん|彼氏|酔っ払い|おばちゃん"
                       r"|電話番|リングアナ)$")
# (label, lemma) misparses Phase 3 must not teach: fragments of names/loanwords
LABEL_SKIP = {("鬼仁会組員", "鬼"), ("リングアナ", "リング")}

# ---------- JMdict index (cached) ----------
def load_jmdict():
    cache = os.path.join(DATA, "jmdict_index.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    jf = [x for x in glob.glob(os.path.join(DATA, "jmdict-eng*.json")) if not x.endswith("zip")][0]
    d = json.load(open(jf, encoding="utf-8"))
    idx = {}
    for w in d["words"]:
        kanji = [k["text"] for k in w.get("kanji", [])]
        kana  = [k["text"] for k in w.get("kana", [])]
        senses = []
        for s in w["sense"][:6]:
            gl = [g["text"] for g in s.get("gloss", []) if g.get("lang") == "eng"]
            if gl:
                senses.append({"pos": s.get("partOfSpeech", []), "glosses": gl[:4]})
        if not senses:
            continue
        reading = kana[0] if kana else ""
        entry = {"reading": reading, "senses": senses,
                 "common": any(k.get("common") for k in w.get("kanji", []) + w.get("kana", []))}
        for key in kanji + kana:
            if key not in idx or (entry["common"] and not idx[key]["common"]):
                idx[key] = entry
    pickle.dump(idx, open(cache, "wb"))
    return idx

def gloss_pos(tags):
    if any(t.startswith("v") for t in tags): return "verb"
    if any(t.startswith("adj-i") for t in tags): return "i-adjective"
    if any(t.startswith("adj-na") or t == "adj-na" for t in tags): return "na-adjective"
    if any(t == "adv" for t in tags): return "adverb"
    if any(t.startswith("n") for t in tags): return "noun"
    return tags[0] if tags else ""

def standalone_aux_verb(t, before):
    """unidic tags verbs that can ALSO be auxiliaries 非自立可能 (抜ける as in 走り抜ける,
    しまう as in 食べてしまう). Skipping them all dropped real words (組を抜ける, 迷惑を掛ける)
    from every deck, so such a verb counts unless it follows a verb, te-form, auxiliary or
    adjective (its helper use) or the honorific prefix お/御 (お願い)."""
    if t.feature.pos1 != "動詞" or t.feature.pos2 != "非自立可能":
        return False
    if before is None:
        return True
    return not (before.feature.pos1 in ("動詞", "助動詞", "形容詞", "接頭辞")
                or before.surface in ("て", "で"))

def content_tokens(line, tagger, known_w, known_r, jm):
    """Yield the minable content tokens of a line: content POS, not a stoplemma, not
    known/suppressed, and glossable in JMdict. Shared by build_deck and the divergence gate
    so both see the exact same token stream."""
    prev = None
    for t in tagger(line):
        p1 = t.feature.pos1; p2 = t.feature.pos2
        before, prev = prev, t
        if p1 not in CONTENT_POS or (p2 in SKIP_POS2 and not standalone_aux_verb(t, before)):
            continue
        lemma = t.feature.lemma or t.surface
        lemma = re.sub(r"-.*$", "", lemma)          # strip unidic lemma suffixes
        reading = kata2hira(t.feature.kana or "")
        if lemma in STOPLEMMA:
            continue
        base = kata2hira(t.feature.lForm or "")     # dictionary-form reading: やっ -> やる
        if lemma in known_w or reading in known_r or base in known_r:
            continue
        if lemma not in jm:                          # need a gloss
            continue
        yield {"lemma": lemma, "surface": t.surface, "reading": reading, "base_reading": base}

# ---------- main ----------
def main():
    ch_lo = int(sys.argv[1]); ch_hi = int(sys.argv[2]) if len(sys.argv) > 2 else ch_lo
    dia_file = sys.argv[3] if len(sys.argv) > 3 else "dialogue_by_chapter.json"
    known = json.load(open(os.path.join(DATA, "known_words.json"), encoding="utf-8"))
    known_w = set(known["words"]); known_r = set(known["readings"])
    # words pre-taught by the Chapter 0 / minigame term decks are treated as known here,
    # so they aren't re-mined -- EXCEPT the sense-divergent set (deliberately left out of
    # this file) which we WANT to reappear later in its other meaning. Ch0 builds skip this.
    pre_path = os.path.join(DATA, "pretaught_words.json")
    if os.path.exists(pre_path) and dia_file == "dialogue_by_chapter.json":
        pre = json.load(open(pre_path, encoding="utf-8"))
        known_w |= set(pre["words"]); known_r |= set(pre["readings"])
    # Name-collision blocklist: character/place names the POS tagger mistags as common nouns
    # because the surface IS a real word (e.g. 錦 = Nishiki, also 'brocade'). The 固有名詞 filter
    # can't catch these, so we suppress them explicitly here. Per entry, a non-empty surface is
    # folded into known_w and a non-empty reading into known_r (leave reading "" when it is too
    # broad to block safely, e.g. 李/り). Add new colliding names/aliases to data/name_block.json.
    nb_path = os.path.join(DATA, "name_block.json")
    if os.path.exists(nb_path) and dia_file == "dialogue_by_chapter.json":
        for e in json.load(open(nb_path, encoding="utf-8")):
            if e.get("surface"): known_w.add(e["surface"])
            if e.get("reading"): known_r.add(e["reading"])
    # Cumulative cross-chapter suppression: words introduced by EARLIER story-chapter decks
    # are treated as known here so we don't re-teach them -- EXCEPT words flagged sense-divergent
    # for this chapter (data/sense_divergent_ch{lo}.json), which reappear in their new meaning.
    # Words first taught within [lo,hi] itself are NOT suppressed (they're this deck's content).
    if dia_file == "dialogue_by_chapter.json":
        from taught_ledger import load_ledger, load_divergent, suppression_sets
        divergent = load_divergent(ch_lo)
        sup_w, sup_r = suppression_sets(load_ledger(), before_chapter=ch_lo, keep=divergent)
        known_w |= sup_w; known_r |= sup_r
        if sup_w:
            print(f"cross-chapter suppression: {len(sup_w)} earlier-taught words hidden"
                  f"{f', {len(divergent)} sense-divergent kept' if divergent else ''}")
    dia = json.load(open(os.path.join(DATA, dia_file), encoding="utf-8"))
    jm = load_jmdict()
    tagger = fugashi.Tagger()

    # gather ordered lines for range, tokenize once
    lines = []
    for ch in range(ch_lo, ch_hi + 1):
        for row in dia.get(str(ch), []):
            toks = list(content_tokens(row["line"], tagger, known_w, known_r, jm))
            lines.append({**row, "chapter": ch, "toks": toks})

    # Phase 1 - i+1: iterate to convergence (introduce word when it's a sentence's ONLY unknown)
    introduced = {}   # lemma -> card
    order = 0
    changed = True
    while changed:
        changed = False
        for ln in lines:
            uniq = {t["lemma"] for t in ln["toks"] if t["lemma"] not in introduced}
            if len(uniq) == 1:
                t = next(t for t in ln["toks"] if t["lemma"] not in introduced)
                introduced[t["lemma"]] = make_card(ln, t, jm, order, "i+1"); order += 1; changed = True
    # Phase 2 - leftovers: forward pass, introduce each line's remaining new words BACK-TO-BACK
    # (group of 2-3 share the sentence; groups of 4+ become standalone word cards)
    for ln in lines:
        new = []
        seen = set()
        for t in ln["toks"]:
            if t["lemma"] not in introduced and t["lemma"] not in seen:
                new.append(t); seen.add(t["lemma"])
        if not new:
            continue
        kind = f"grp{len(new)}" if len(new) <= 3 else "solo"
        for t in new:
            introduced[t["lemma"]] = make_card(ln, t, jm, order, kind, standalone=(kind == "solo"))
            order += 1

    # Phase 3 - speaker-descriptor labels: APPENDED after all dialogue cards so existing card
    # orders (and the order-keyed translations of already-finalized chapters) are never disturbed.
    if dia_file == "dialogue_by_chapter.json":
        for ch in range(ch_lo, ch_hi + 1):
            seen_lab = set()
            for row in dia.get(str(ch), []):
                s = (row.get("speaker") or "").strip()
                if not s or s in seen_lab or re.search(r"[0-9０-９]", s) or not DESC_HEAD.search(s):
                    continue
                seen_lab.add(s)
                pseudo = {"line": s, "uid": f"label-ch{ch}", "speaker": "〔人物呼称〕", "chapter": ch}
                for t in content_tokens(s, tagger, known_w, known_r, jm):
                    if t["lemma"] not in introduced and (s, t["lemma"]) not in LABEL_SKIP:
                        introduced[t["lemma"]] = make_card(pseudo, t, jm, order, "label", standalone=True)
                        order += 1

    cards = sorted(introduced.values(), key=lambda c: c["order"])
    n_i1  = sum(1 for c in cards if c["kind"] == "i+1")
    n_grp = sum(1 for c in cards if c["kind"].startswith("grp"))
    n_solo = sum(1 for c in cards if c["kind"] == "solo")
    n_lab = sum(1 for c in cards if c["kind"] == "label")
    print(f"chapters {ch_lo}-{ch_hi}: {len(lines)} lines -> {len(cards)} new words "
          f"({n_i1} i+1, {n_grp} back-to-back, {n_solo} standalone, {n_lab} speaker-label)")
    json.dump(cards, open(os.path.join(DATA, f"cards_ch{ch_lo}_{ch_hi}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    build_apkg(cards, ch_lo, ch_hi)
    print("\nfirst 12 cards:")
    for c in cards[:12]:
        print(f"  [{c['kind']:5}] {c['word']} ({c['reading']}) = {c['meaning'][:38]} | {re.sub('<[^>]+>','',c['sentence'])[:42]}")

def make_card(ln, t, jm, order, kind, standalone=False):
    e = jm[t["lemma"]]
    sent = strip_orphan_brackets(ln["line"])
    if t["surface"] in sent:
        sent = sent.replace(t["surface"], f"<b>{t['surface']}</b>", 1)
    s0 = e["senses"][0]
    # candidate senses text for the polish subagent to choose among
    cand = [f"({gloss_pos(s['pos'])}) " + "; ".join(s["glosses"]) for s in e["senses"]]
    return {
        "order": order, "kind": kind, "standalone": standalone,
        "sentence": sent,
        "word": t["lemma"],
        "reading": e["reading"] or t["reading"],
        "meaning": "; ".join(s0["glosses"]),        # default = first sense; overwritten by polish
        "pos": gloss_pos(s0["pos"]),
        "chapter": ln["chapter"],
        "speaker": ln.get("speaker") or "",
        "uid": ln["uid"],
        "candidates": cand,
    }

MODEL = genanki.Model(
    1607392319, "Yakuza0 i+1",
    fields=[{"name": n} for n in ["Sentence", "Word", "Reading", "Meaning", "POS", "Chapter", "Speaker", "UID"]],
    templates=[{
        "name": "Recognition",
        "qfmt": '<div class="sent">{{Sentence}}</div><div class="spk">{{Speaker}} · Ch.{{Chapter}}</div>',
        "afmt": '{{FrontSide}}<hr id="answer"><div class="word">{{Word}}</div>'
                '<div class="read">{{Reading}}</div><div class="mean">{{Meaning}}</div>'
                '<div class="pos">{{POS}}</div>',
    }],
    css=".card{font-family:'Meiryo','Yu Gothic',sans-serif;font-size:22px;text-align:center;color:#111;background:#fff}"
        ".sent{font-size:26px;margin:14px}.spk{color:#888;font-size:14px}"
        ".word{font-size:34px;font-weight:700;margin-top:12px}.read{color:#0a7;font-size:20px}"
        ".mean{margin:10px;font-size:20px}.pos{color:#999;font-size:14px} b{color:#c00}",
)

def build_apkg(cards, lo, hi):
    from keep_guids import old_guids, guid
    from deck_names import chapter as chapter_deck
    name = chapter_deck(lo) + (f"-{hi}" if hi != lo else "")
    out = os.path.join(DATA, "decks"); os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"yakuza0_ch{lo}" + (f"_{hi}" if hi != lo else "") + ".apkg")
    old = old_guids(path)                    # key (Sentence, Word) -> guid already in Anki
    deck = genanki.Deck(2059400110 + lo, name)
    for c in cards:
        fields = [c["sentence"], c["word"], c["reading"], c["meaning"], c["pos"],
                  str(c["chapter"]), c["speaker"], c["uid"]]
        deck.add_note(genanki.Note(model=MODEL, fields=fields, guid=guid(old, fields)))
    genanki.Package(deck).write_to_file(path)
    print("wrote", path)

if __name__ == "__main__":
    main()
