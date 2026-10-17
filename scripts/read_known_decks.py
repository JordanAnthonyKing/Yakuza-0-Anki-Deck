"""Read vocab words from the JLPT N5/N4 .apkg decks to build the 'known' seed set.

.apkg is a zip containing a SQLite collection. Newer exports use zstd-compressed
'collection.anki21b'; a legacy uncompressed 'collection.anki2' is usually also present.
"""
import zipfile, sqlite3, tempfile, os, glob, sys

def load_db_bytes(apkg):
    with zipfile.ZipFile(apkg) as z:
        names = z.namelist()
        # Prefer legacy uncompressed DB (stdlib-only). Fall back to zstd.
        if "collection.anki2" in names:
            data = z.read("collection.anki2")
            return data, "anki2"
        if "collection.anki21b" in names:
            raw = z.read("collection.anki21b")
            try:
                import zstandard as zstd
                data = zstd.ZstdDecompressor().decompress(raw, max_output_size=200_000_000)
                return data, "anki21b(zstd)"
            except Exception as e:
                return None, f"need-zstd: {e}"
    return None, "no-db"

def dump(apkg):
    data, kind = load_db_bytes(apkg)
    print(f"\n==== {os.path.basename(apkg)}  [{kind}] ====")
    if data is None:
        print("  could not load:", kind); return
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.write(data); tf.close()
    try:
        con = sqlite3.connect(tf.name)
        n = con.execute("select count(*) from notes").fetchone()[0]
        print("  notes:", n)
        for flds, in con.execute("select flds from notes limit 4"):
            parts = flds.split("\x1f")
            print("  FIELDS(%d):" % len(parts))
            for i, p in enumerate(parts):
                print(f"    [{i}] {p[:60]!r}")
        con.close()
    finally:
        os.unlink(tf.name)

for f in sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "*.apkg"))):
    dump(f)
