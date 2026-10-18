"""Audio for every deck in one go, then rebuild them all.

Story chapters: game voice clips (sentence_audio.py) + JPod101 word audio; term decks
(Chapter 0, minigame): word audio only. The names deck gets furigana but no audio. Word fetches are cached, so a rerun only
fetches words it hasn't asked about before. New chapters get the same via the pipeline's
sentence-audio / word-audio stages.

Usage: python scripts/audio/build_all_audio.py
"""
import os, sys, glob, re, subprocess

R = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PY, SCRIPTS = sys.executable, os.path.join(R, "scripts")
CHAPTERS = sorted(int(re.search(r"cards_ch(\d+)_", p).group(1))
                  for p in glob.glob(os.path.join(R, "data", "cards_ch*_*.json"))
                  if not p.endswith("cards_ch0_0.json"))
TERM_DECKS = [os.path.join(R, "data", "decks", f"yakuza0_{n}.apkg") for n in ("ch0", "minigame")]

def run(*args):
    print(">", *args, flush=True)
    subprocess.run([PY, *args], cwd=SCRIPTS, check=True)

for ch in CHAPTERS:
    run("audio/sentence_audio.py", str(ch))
run("audio/word_audio.py", *map(str, CHAPTERS), *TERM_DECKS)
run("audio/verify_stage.py", *map(str, CHAPTERS), *TERM_DECKS)
run("build_all_in_one.py")                # rebuilds every deck + the combined yakuza0_all.apkg
