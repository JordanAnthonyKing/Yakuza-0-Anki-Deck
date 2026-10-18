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
