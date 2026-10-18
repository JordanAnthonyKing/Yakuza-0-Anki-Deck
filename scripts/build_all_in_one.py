"""One .apkg holding every deck, so the whole set imports into Anki in a single drop.

Runs each deck builder (build_final.py per chapter, build_ch0_decks.py, build_names_deck.py)
with genanki.Package.write_to_file intercepted: each builder still writes its own deck file
as usual, and its decks and media are also collected and packed together into
data/decks/yakuza0_all.apkg. Deck names, deck ids, note GUIDs and media come from the same
builders, so importing the combined file updates the same cards as the individual decks
(the "Yakuza 0::…" hierarchy from deck_names.py groups them).

Usage: python build_all_in_one.py
"""
import os, sys, glob, re, runpy
import genanki

HERE = os.path.dirname(os.path.abspath(__file__))
DECKS = os.path.join(HERE, "..", "data", "decks")
CHAPTERS = sorted(int(re.search(r"cards_ch(\d+)_", p).group(1))
                  for p in glob.glob(os.path.join(HERE, "..", "data", "cards_ch*_*.json"))
                  if not p.endswith("cards_ch0_0.json"))

decks, media = [], set()
_write = genanki.Package.write_to_file

def _collect(self, path, *a, **k):
    decks.extend(self.decks)
    media.update(self.media_files)
    return _write(self, path, *a, **k)

genanki.Package.write_to_file = _collect
os.chdir(HERE)
sys.path.insert(0, HERE)
for ch in CHAPTERS:
    sys.argv = ["build_final.py", str(ch)]
    runpy.run_path("build_final.py", run_name="__main__")
for script in ("build_ch0_decks.py", "build_names_deck.py"):
    sys.argv = [script]
    runpy.run_path(script, run_name="__main__")
genanki.Package.write_to_file = _write

out = os.path.join(DECKS, "yakuza0_all.apkg")
genanki.Package(decks, media_files=sorted(media)).write_to_file(out)
print(f"wrote {out}: {len(decks)} decks, {sum(len(d.notes) for d in decks)} notes, "
      f"{len(media)} audio files, {os.path.getsize(out) / 1e6:.1f} MB")
