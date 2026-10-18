"""Word audio from JapanesePod101 (the endpoint Yomitan uses by default).

The endpoint is looked up by (kanji, kana) and answers a miss with a fixed "audio not
available" clip, recognised by the md5 of a nonsense query. Single source by design: a word
JPod101 doesn't have gets no audio. Results are cached in data/audio/word_audio.json
({"word|reading": file or null}), so each word is requested once, ever.

Usage: python scripts/audio/word_audio.py <deck>...   deck = a chapter number, a cards json
       stem such as cards_ch0_0, or an .apkg path (Word, Reading = its first two fields;
       used for the term decks) -> data/audio/words/y0w_<md5>.mp3
"""
import os, sys, json, hashlib, time, urllib.request, urllib.parse, zipfile, sqlite3, tempfile

sys.stdout.reconfigure(encoding="utf-8")
R = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = os.path.join(R, "data", "audio")
WORDS = os.path.join(D, "words")
INDEX = os.path.join(D, "word_audio.json")
URL = "https://assets.languagepod101.com/dictionary/japanese/audiomp3.php?"

def key(word, reading):
    return f"{word}|{reading}"

def file_name(word, reading):
    return "y0w_" + hashlib.md5(key(word, reading).encode("utf-8")).hexdigest()[:16] + ".mp3"

def fetch(word, reading, tries=4):
    q = urllib.parse.urlencode({"kanji": word, "kana": reading})
    req = urllib.request.Request(URL + q, headers={"User-Agent": "Mozilla/5.0"})
    for t in range(tries):
        try:
            return urllib.request.urlopen(req, timeout=20).read()
        except Exception:
            if t == tries - 1:
                raise
            time.sleep(5 * 2 ** t)              # the endpoint drops connections when busy

def load_index():
    return json.load(open(INDEX, encoding="utf-8")) if os.path.exists(INDEX) else {}

def deck_words(d):
    """[(word, reading)] of a deck argument (see usage)."""
    if d.endswith(".apkg"):
        with tempfile.TemporaryDirectory() as t:
            zipfile.ZipFile(d).extract("collection.anki2", t)
            con = sqlite3.connect(os.path.join(t, "collection.anki2"))
            rows = [f.split("")[:2] for (f,) in con.execute("select flds from notes")]
            con.close()
        return [tuple(r) for r in rows]
    stem = f"cards_ch{d}_{d}" if d.isdigit() else d
    return [(c["word"], c["reading"])
            for c in json.load(open(os.path.join(R, "data", stem + ".json"), encoding="utf-8"))]

def main(decks):
    os.makedirs(WORDS, exist_ok=True)
    idx = load_index()
    words = []
    for d in decks:
        for w, r in deck_words(d):
            if key(w, r) not in idx and (w, r) not in words:
                words.append((w, r))
    if not words:
        print("all words already cached"); return
    miss_md5 = hashlib.md5(fetch("ぬぬぬぬぬぬ", "ぬぬぬぬぬぬ")).hexdigest()
    for i, (w, r) in enumerate(words):
        try:
            data = fetch(w, r)
        except Exception as e:                  # network error: leave uncached, retry next run
            print("error", w, r, e); continue
        if hashlib.md5(data).hexdigest() == miss_md5:
            idx[key(w, r)] = None
        else:
            name = file_name(w, r)
            open(os.path.join(WORDS, name), "wb").write(data)
            idx[key(w, r)] = name
        if i % 25 == 0:
            json.dump(idx, open(INDEX, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        time.sleep(0.4)                         # be polite to a free endpoint
    json.dump(idx, open(INDEX, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    got = [idx.get(key(w, r)) for w, r in words]
    print(f"fetched {len(words)} new words: {sum(bool(g) for g in got)} with audio, "
          f"{sum(g is None for g in got)} not on JPod101")

if __name__ == "__main__":
    main(sys.argv[1:])
