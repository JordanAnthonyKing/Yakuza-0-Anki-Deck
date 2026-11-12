"""Anki furigana markup for a word: 隠し持つ + かくしもつ -> "隠[かく]し 持[も]つ".

Rendered on the card with {{furigana:Field}}. The reading is aligned to the word by turning
each kanji run into a capture group and each kana run into a literal, so okurigana stays
bare and only the kanji get readings. Words without kanji are returned unchanged; a reading
that can't be aligned falls back to one ruby over the whole word.
"""
import re

KANJI = r"[一-龯㐀-䶿々〆ヶ]"

def _hira(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)

def furigana(word, reading):
    if not reading or not re.search(KANJI, word):
        return word
    runs = re.findall(rf"{KANJI}+|[^一-龯㐀-䶿々〆ヶ]+", word)
    pat = "".join("(.+?)" if re.match(KANJI, r) else "(" + re.escape(_hira(r)) + ")" for r in runs)
    m = re.fullmatch(pat, _hira(reading))
    if not m:
        return f"{word}[{reading}]"
    out = ""
    for run, got in zip(runs, m.groups()):
        if re.match(KANJI, run):
            out += (" " if out else "") + f"{run}[{got}]"   # space ends the previous ruby base
        else:
            out += run
    return out

if __name__ == "__main__":
    for w, r in [("隠し持つ", "かくしもつ"), ("酒盛り", "さかもり"), ("ありがたい", "ありがたい"),
                 ("お陰", "おかげ"), ("神室町", "かむろちょう"), ("ドス黒い", "どすぐろい"), ("糞", "くそ")]:
        print(w, r, "->", furigana(w, r))


# ---------- whole-sentence ruby (story card backs) ----------
# Sentences carry <b>…</b> around the target word, which Anki's bracket syntax can't nest
# with, so this emits HTML <ruby> directly. The card CSS hides each <rt> until its word is
# hovered (tapped on mobile).
import html as _html
import json as _json
import os as _os

_NAMES = None
_tagger = None
# unidic's reading is wrong for every story line using these surfaces
READING_FIX = {"１日": "いちにち", "1日": "いちにち"}

def _names():
    """Curated character/place readings, longest first: unidic misreads several
    (錦山 -> きんざん, 立華 -> りっか)."""
    global _NAMES
    if _NAMES is None:
        p = _os.path.join(_os.path.dirname(__file__), "..", "data", "names_curated.json")
        _NAMES = sorted(((e["word"], _hira(e["reading"])) for e in _json.load(open(p, encoding="utf-8"))
                         if re.search(KANJI, e["word"])), key=lambda x: -len(x[0]))
    return _NAMES

def _ruby_units(word, reading, start):
    """(start, end, html) units for one token: kanji runs carry ruby, kana stay bare."""
    if not reading or not re.search(KANJI, word):
        return [(start + i, start + i + 1, _html.escape(ch)) for i, ch in enumerate(word)]
    runs = re.findall(rf"{KANJI}+|[^一-龯㐀-䶿々〆ヶ]+", word)
    pat = "".join("(.+?)" if re.match(KANJI, r) else "(" + re.escape(_hira(r)) + ")" for r in runs)
    m = re.fullmatch(pat, _hira(reading))
    if not m:                                  # unalignable: one ruby over the whole token
        return [(start, start + len(word),
                 f"<ruby>{_html.escape(word)}<rt>{_html.escape(_hira(reading))}</rt></ruby>")]
    out, pos = [], start
    for run, got in zip(runs, m.groups()):
        if re.match(KANJI, run):
            out.append((pos, pos + len(run), f"<ruby>{run}<rt>{got}</rt></ruby>"))
        else:
            out += [(pos + i, pos + i + 1, _html.escape(ch)) for i, ch in enumerate(run)]
        pos += len(run)
    return out

def sentence_ruby(sentence, word="", reading=""):
    """Story-card sentence HTML -> same HTML with <ruby> over every kanji run.
    Only <b>/</b> tags are expected in the input; a tag that falls inside a ruby unit is
    moved to the unit's edge. The bolded target word uses the card's own reading when the
    bold text starts with the dictionary word (it may run on over a conjugation)."""
    global _tagger
    if _tagger is None:
        import fugashi
        _tagger = fugashi.Tagger()
    plain, tags = "", []                       # tags: (offset in plain, tag)
    for part in re.split(r"(<[^>]+>)", sentence):
        if part.startswith("<"):
            tags.append((len(plain), part))
        else:
            plain += _html.unescape(part)
    fixed = {}                                 # start -> (word, reading): names + target word
    bold = re.search(r"<b>(.*?)</b>", sentence)
    if bold and word and reading and _html.unescape(bold.group(1)).startswith(word):
        s = len(re.sub(r"<[^>]+>", "", sentence[:bold.start()]))
        fixed[s] = (word, reading)
    for name, r in _names():
        for m in re.finditer(re.escape(name), plain):
            if not any(a <= m.start() < a + len(w) or m.start() <= a < m.end() for a, (w, _) in fixed.items()):
                fixed[m.start()] = (name, r)
    units, i = [], 0
    while i < len(plain):                      # fixed spans first, tokenize the gaps between
        nxt = min((a for a in fixed if a >= i), default=len(plain))
        if nxt == i:
            w, r = fixed[i]
            units += _ruby_units(w, r, i); i += len(w); continue
        pos = i
        for t in _tagger(plain[i:nxt]):
            k = plain.index(t.surface, pos) if t.surface and t.surface in plain[pos:nxt] else pos
            for j in range(pos, k):            # whitespace the tagger skipped
                units.append((j, j + 1, _html.escape(plain[j])))
            r = READING_FIX.get(t.surface) or (t.feature.kana if t.feature.kana not in (None, "*") else "")
            units += _ruby_units(t.surface, r, k)
            pos = k + len(t.surface)
        for j in range(pos, nxt):
            units.append((j, j + 1, _html.escape(plain[j])))
        i = nxt
    out, ti = "", 0
    for s, e, h in units:
        while ti < len(tags) and tags[ti][0] <= s:
            out += tags[ti][1]; ti += 1
        out += h
        while ti < len(tags) and tags[ti][0] < e and tags[ti][1].startswith("</"):
            out += tags[ti][1]; ti += 1        # a closing tag inside the unit goes after it
    out += "".join(t for _, t in tags[ti:])
    return out


# ---------- highlight the whole conjugated word ----------
# Cards bold only the dictionary token, which for an inflected verb is its bare stem
# (<b>見かけ</b>たぜ). widen_bold() extends the bold over the word's own endings
# (見かけた, 勧められたら, 知らされて, 改造して) but stops before helper verbs (ている,
# しまう, いただく and unidic's contracted forms てる/とる/ちまう/とく/てく, which it tags as
# auxiliaries), copulas, quotatives and particles -- those are separate, already-known words.
# Rendering only: card files keep the original bold, and the GUID key ignores tags.
# `pos` is the card's own part of speech: JMdict knows ドキドキ/交換 take する even where
# unidic tags them as adverbs or plain nouns.
CONJ_AUX = {"た", "れる", "られる", "せる", "させる", "ます", "ない", "ず", "ぬ", "たい",
            "う", "よう", "まい", "やがる",
            "へん",                            # Kansai negative: 持ち込めへん
            "り"}                              # unidic misreads 詫び入れ|る as classical り
TE = {"て", "で"}
CONJ_PARTICLE = {"ば", "ちゃ", "じゃ"}
SURU = {"為る", "出来る"}                       # 改造して, 交換できる

def widen_bold(sentence, pos=""):
    global _tagger
    if _tagger is None:
        import fugashi
        _tagger = fugashi.Tagger()
    m = re.fullmatch(r"(.*?)<b>(.*?)</b>(.*)", sentence, re.S)
    if not m or "<" in m.group(2) or "<" in m.group(3)[:1]:
        return sentence
    head, body, tail = m.groups()
    toks = list(_tagger(body + re.sub(r"<[^>]+>", "", tail)))
    i, text = 0, ""
    while i < len(toks) and len(text) < len(body):
        text += toks[i].surface; i += 1
    if text != body:                           # bold doesn't end on a token boundary:
        if pos == "verb" and tail[:1] in ("て", "で", "た", "だ"):
            return f"{head}<b>{body}{tail[0]}</b>{tail[1:]}"   # <b>つい</b>で = 継いで
        return sentence
    i0, f = i, toks[i - 1].feature
    if i < len(toks) and toks[i].feature.lemma in SURU and (
            f.pos1 == "名詞" and "サ変" in (f.pos3 or "") or pos in ("verb", "adverb") and f.pos1 not in ("動詞", "形容詞")):
        i += 1
    elif f.pos1 not in ("動詞", "形容詞"):
        return sentence
    j = i
    while j < len(toks):
        t, tf = toks[j], toks[j].feature
        if (toks[j - 1].feature.cForm or "").startswith(("終止形", "連体形")):
            break                              # 駆け込む|だなんて: already a finished word
        if t.surface in TE and (tf.pos2 == "接続助詞" or tf.lemma == "てる"):
            j += 1; break                      # te-form: the next word is a helper
        if tf.pos1 == "助動詞" and tf.lemma in CONJ_AUX:
            j += 1; continue
        if tf.pos1 == "助詞" and tf.pos2 == "接続助詞" and t.surface in CONJ_PARTICLE:
            j += 1; break
        if tf.pos1 == "形容詞" and tf.lemma == "無い" and toks[j - 1].feature.pos1 == "形容詞":
            j += 1; continue                   # 荒っぽく + ない
        if tf.lemma == "そう-様態" and j == i0:
            j += 1; break                      # 素早そう "looks quick"
        break
    add = "".join(t.surface for t in toks[i0:j])
    if not add or not tail.startswith(add):    # nothing to add, or a tag sits in the way
        return sentence
    return f"{head}<b>{body}{add}</b>{tail[len(add):]}"
