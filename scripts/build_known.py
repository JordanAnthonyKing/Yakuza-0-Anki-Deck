"""Extract the 'known' vocabulary set from the JLPT N5/N4 .apkg decks.
Field [4] = headword (strip trailing [n]); field [5] furigana; field [8] meaning.
Save data/known_words.json = {"words": [...surface...], "readings": [...]}.
"""
import zipfile, sqlite3, tempfile, os, glob, re, json
import zstandard as zstd

REPO = r"C:\Users\jordan\repos\yakuza"

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
for f in sorted(glob.glob(os.path.join(REPO, "*.apkg"))):
    n = 0
    for flds in notes(f):
        parts = flds.split("\x1f")
        if len(parts) < 6:
            continue
        hw = parts[4]
        hw = re.sub(r"\[[0-9]+\]$", "", hw).strip()          # drop disambiguation [2]
        hw = re.sub(r"<[^>]+>", "", hw)
        # reading from field 5: strip furigana markup 漢字[かな] -> keep kana + kana-only
        rd = parts[5]
        kana = "".join(re.findall(r"[ぁ-んァ-ヶー]", re.sub(r"[^\[]+\[([^\]]+)\]", r"\1", rd)))
        if hw:
            words.add(hw)
        if kana:
            readings.add(kana)
        n += 1
    print(f"{os.path.basename(f)}: {n} notes")

json.dump({"words": sorted(words), "readings": sorted(readings)},
          open(os.path.join(REPO, "data", "known_words.json"), "w", encoding="utf-8"),
          ensure_ascii=False)
print(f"known surfaces: {len(words)}, known readings: {len(readings)}")
print("sample:", sorted(words)[:15])
