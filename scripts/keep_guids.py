"""Keep Anki note GUIDs stable across rebuilds.

genanki's default GUID is a hash of ALL fields, so any field change (a new translation, an
accepted official line) makes Anki import the note as a DUPLICATE instead of updating the
card the learner already studies. Before rebuilding a deck, read the GUIDs out of the
existing .apkg keyed by the identifying leading fields and reuse them.
"""
import os, re, zipfile, sqlite3, tempfile
import genanki

def _key(fields, nkey):
    # brackets/whitespace dropped so the polish-layer deck (raw sentence) and the translated
    # deck (strip_orphan_brackets'd sentence) key the same note identically
    return tuple(re.sub(r"[（）()\s　]", "", f) for f in fields[:nkey])

def old_guids(apkg, nkey=2):
    """{key of first nkey fields: guid} from an existing .apkg ({} if none)."""
    if not os.path.exists(apkg):
        return {}
    with tempfile.TemporaryDirectory() as d:
        zipfile.ZipFile(apkg).extract("collection.anki2", d)
        con = sqlite3.connect(os.path.join(d, "collection.anki2"))
        rows = con.execute("select guid, flds from notes").fetchall()
        con.close()
    return {_key(f.split("\x1f"), nkey): g for g, f in rows}

def guid(old, fields, nkey=2):
    """Reuse the old GUID for this note's key, else genanki's default."""
    return old.get(_key(fields, nkey)) or genanki.guid_for(*fields)
