"""Which JPod101 word clips the decks may use.

JPod101's data has errors, so a clip is used only once checked: data/audio/word_verify.json
(speech recognition, verify_word_audio.py) and data/audio/word_verdicts.json (the user's
listening review, gen_verify_review.py page). A human verdict wins; otherwise the clip needs
a speech-check score >= PASS. Unchecked clips are left out until the check has run.
"""
import os, json

AUDIO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "audio")
PASS = 0.75

def _load(name):
    p = os.path.join(AUDIO, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

_index, _verify, _verdicts = _load("word_audio.json"), _load("word_verify.json"), _load("word_verdicts.json")

def word_clip(word, reading):
    """The checked clip file name for this word, or None."""
    k = f"{word}|{reading}"
    f = _index.get(k)
    if not f:
        return None
    if k in _verdicts:
        return f if _verdicts[k] == "ok" else None
    v = _verify.get(k)
    return f if v and v["score"] >= PASS else None
