"""Extract the 'known' vocabulary set from the JLPT N5/N4 .apkg decks.
Field [4] = headword (strip trailing [n]); field [5] furigana; field [8] meaning.
Headwords can list alternatives (有る・在る) or be phrases (電話を掛ける, 頭がいい): each
alternative is added, and a phrase also adds its final word after を/が/に (掛ける, いい).
Only the N5 and N4 decks count -- the repo root also holds N3-N1 and unrelated decks.
Save data/known_words.json = {"words": [...surface...], "readings": [...]}.

Usage: python build_known.py [out.json]
"""
import zipfile, sqlite3, tempfile, os, glob, re, json, sys
import zstandard as zstd

REPO = r"C:\Users\jordan\repos\yakuza"
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "data", "known_words.json")
KNOWN_DECKS = ["*JLPT Tango N5*.apkg", "*JLPT Tango N4*.apkg"]
PHRASE = re.compile(r"^.+[をがに](.+)$")
PAREN = re.compile(r"[（(][^）)]*[）)]")
WORDLIKE = re.compile(r"[ぁ-んァ-ヶー一-龯々]{2,}|[一-龯々]")   # drops fragments like "]" or "る"

def notes(apkg):
    with zipfile.ZipFile(apkg) as z:
        raw = z.read("collection.anki21b")
    data = zstd.ZstdDecompressor().decompress(raw, max_output_size=300_000_000)
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tf.write(data); tf.close()
    con = sqlite3.connect(tf.name)
    rows = [f for (f,) in con.execute("select flds from notes")]
    con.close(); os.unlink(tf.name)
    return rows

words, readings = set(), set()
for f in sorted(p for pat in KNOWN_DECKS for p in glob.glob(os.path.join(REPO, pat))):
    n = 0
    for flds in notes(f):
        parts = flds.split("\x1f")
        if len(parts) < 6:
            continue
        hw = parts[4]
        hw = re.sub(r"\[[0-9]+\]$", "", hw).strip()          # drop disambiguation [2]
        hw = re.sub(r"<[^>]+>", "", hw)
        # the whole headword as before, plus each alternative and a phrase's final word
        if hw:
            words.add(hw)
        for alt in filter(None, (a.strip() for a in re.split(r"[・、]", PAREN.sub("", hw)))):
            m = PHRASE.match(alt)
            for w in (alt, m.group(1) if m else ""):
                if WORDLIKE.fullmatch(w):
                    words.add(w)
        # reading from field 5: strip furigana markup 漢字[かな] -> keep kana + kana-only
        rd = parts[5]
        kana = "".join(re.findall(r"[ぁ-んァ-ヶー]", re.sub(r"[^\[]+\[([^\]]+)\]", r"\1", rd)))
        if kana:
            readings.add(kana)
        for alt in re.split(r"[・、]", PAREN.sub("", rd)):
            k = "".join(re.findall(r"[ぁ-んァ-ヶー]", re.sub(r"[^\[]+\[([^\]]+)\]", r"\1", alt)))
            if len(k) >= 2:
                readings.add(k)
        n += 1
    print(f"{os.path.basename(f)}: {n} notes")

json.dump({"words": sorted(words), "readings": sorted(readings)},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print(f"known surfaces: {len(words)}, known readings: {len(readings)}")
print("sample:", sorted(words)[:15])
