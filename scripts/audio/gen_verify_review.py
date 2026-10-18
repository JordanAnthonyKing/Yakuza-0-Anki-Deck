"""Review page for word audio the speech-recognition check flagged (score < 0.75, or < 1.0
to include close matches).

Embeds each flagged JPod101 clip as a data URI beside the word, its reading and meaning,
and what Whisper heard. Verdicts are saved in the artifact's db (collection "verdicts",
doc id = clip file stem, {key, verdict: "ok"|"bad"}); copy them into
data/audio/word_verdicts.json {"word|reading": verdict}, which audio_policy.py applies.

Usage: python scripts/audio/gen_verify_review.py <out.html> [threshold]
"""
import os, sys, json, glob, base64, html, zipfile, sqlite3, tempfile

R = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = os.path.join(R, "data", "audio")
THRESH = 0.75   # gen_verify_review.py <out> [threshold]: 1.0 also lists the close matches

def meanings():
    """word|reading -> meaning, from the built decks (story: fields 1,2,3; term: 0,1,2)."""
    out = {}
    for p in glob.glob(os.path.join(R, "data", "decks", "yakuza0_*.apkg")):
        story = os.path.basename(p)[8:10] == "ch" and not p.endswith("ch0.apkg")
        with tempfile.TemporaryDirectory() as t:
            zipfile.ZipFile(p).extract("collection.anki2", t)
            con = sqlite3.connect(os.path.join(t, "collection.anki2"))
            for (f,) in con.execute("select flds from notes"):
                x = f.split("\x1f")
                w, r, m = (x[1], x[2], x[3]) if story else (x[0], x[1], x[2])
                out.setdefault(f"{w}|{r}", m)
            con.close()
    return out

def main(path, thresh=THRESH):
    idx = json.load(open(os.path.join(D, "word_audio.json"), encoding="utf-8"))
    ver = json.load(open(os.path.join(D, "word_verify.json"), encoding="utf-8"))
    mean = meanings()
    rows = []
    for k, v in sorted(ver.items(), key=lambda kv: kv[1]["score"]):
        if v["score"] >= thresh or not idx.get(k) or k not in mean:
            continue                      # k not in mean: word no longer in any deck
        f = idx[k]
        b64 = base64.b64encode(open(os.path.join(D, "words", f), "rb").read()).decode()
        w, r = k.split("|", 1)
        rows.append({"id": f[:-4], "key": k, "word": w, "reading": r, "meaning": mean[k],
                     "heard": v["heard"], "score": v["score"], "src": "data:audio/mpeg;base64," + b64})
    tpl = open(os.path.join(os.path.dirname(__file__), "verify_review.tpl.html"), encoding="utf-8").read()
    open(path, "w", encoding="utf-8").write(
        tpl.replace("/*ROWS*/[]", json.dumps(rows, ensure_ascii=False)))
    print(f"{len(rows)} flagged clips -> {path} ({os.path.getsize(path) / 1e6:.1f} MB)")

if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else THRESH)
