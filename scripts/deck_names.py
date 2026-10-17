"""Single source of truth for Anki deck names.

Every deck lives under one master deck ("Yakuza 0::…"). Anki lists subdecks alphabetically,
so zero-padded prefixes give the study order:

  00 · Game Basics        (term deck, taught first)
  00.2 · Minigame Terms   (before the story: these words are suppressed from story decks)
  00.5 · Characters & Places
  01 · Chapter 1 … 17 · Chapter 17
"00 ·" sorts before "00.2" because " " < "." — keep the space after the number.

Deck IDs are unchanged, so re-importing moves nothing and keeps review history.
"""
MASTER = "Yakuza 0"

def chapter(ch):
    return f"{MASTER}::{ch:02d} · Chapter {ch}"

GAME_BASICS = f"{MASTER}::00 · Game Basics"
MINIGAME = f"{MASTER}::00.2 · Minigame Terms"
NAMES = f"{MASTER}::00.5 · Characters & Places"
