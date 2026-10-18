"""Check JPod101 word audio by ear (speech recognition), since JPod101's own data has errors
(もたもた came back as a different word).

Each clip is transcribed with Whisper large-v3 WITHOUT any hint of the expected word, the
transcript turned into kana (fugashi), and compared with the card's reading. Results go to
data/audio/word_verify.json {"word|reading": {heard, kana, score}}; low scores are what a
human should listen to. Cached: a clip is only transcribed once.

Runs in its own venv (tools/asr: faster-whisper + CUDA libs + fugashi):
  tools/asr/Scripts/python scripts/audio/verify_word_audio.py <deck>...   (same deck args as word_audio.py)
"""
import os, sys, glob, json, re, difflib, site, subprocess
sys.stdout.reconfigure(encoding="utf-8")
for sp in site.getsitepackages():                      # CUDA DLLs shipped as pip wheels
    for b in glob.glob(os.path.join(sp, "nvidia", "*", "bin")):
        os.add_dll_directory(b); os.environ["PATH"] = b + os.pathsep + os.environ["PATH"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from word_audio import D, WORDS, INDEX, key, deck_words
from faster_whisper import WhisperModel
import fugashi
import numpy as np

OUT = os.path.join(D, "word_verify.json")
tagger = fugashi.Tagger()

def hira(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)

def norm(s):
    """kana for comparison: hiragana, no punctuation/spaces, long-vowel mark dropped."""
    return re.sub(r"[^ぁ-ゖ]", "", hira(s))

def to_kana(text):
    out = ""
    for w in tagger(text):
        k = getattr(w.feature, "kana", None)
        out += k if k and k != "*" else w.surface
    return out

def load(path):
    """16 kHz mono float32 via ffmpeg (faster-whisper's own PyAV decoder breaks on new av)."""
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1",
                          "-ar", "16000", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)

def main(decks):
    idx = json.load(open(INDEX, encoding="utf-8"))
    res = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    todo = []
    for d in decks:
        for w, r in deck_words(d):
            k = key(w, r)
            if idx.get(k) and k not in res and k not in [t[0] for t in todo]:
                todo.append((k, w, r))
    print(len(todo), "clips to transcribe", flush=True)
    model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    for i, (k, w, r) in enumerate(todo):
        segs, _ = model.transcribe(load(os.path.join(WORDS, idx[k])), language="ja", beam_size=5,
                                   condition_on_previous_text=False, without_timestamps=True)
        heard = "".join(s.text for s in segs).strip()
        kana = to_kana(heard)
        score = difflib.SequenceMatcher(None, norm(kana), norm(r)).ratio()
        if re.sub(r"[。、！？!?.\s]", "", heard) == w:   # wrote the card's own word: kana guess may misread it
            score = 1.0
        res[k] = {"heard": heard, "kana": kana, "score": round(score, 2)}
        if i % 100 == 0:
            json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    sel = [(k, res[k]) for k, _, _ in todo]
    low = sorted((v["score"], k, v["heard"], v["kana"]) for k, v in sel if v["score"] < 0.75)
    print(f"{len(sel)} checked, {len(low)} below 0.75:")
    for s, k, h, kn in low:
        print(f"  {s:.2f}  {k:24} heard {h} ({kn})")

if __name__ == "__main__":
    main(sys.argv[1:])
