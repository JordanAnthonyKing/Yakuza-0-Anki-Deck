"""The word-first Term note type shared by the ch0, minigame and names decks (id 1607392400).

ONE definition: Anki keys note types by id, so every deck using this id must declare the
identical field list or imports conflict. English/Official are the example sentence's
literal translation and (gate-passed) official localization; blank when there's none.
"""
import os, json
import genanki
from furigana import furigana
from audio_policy import AUDIO, word_clip

MODEL = genanki.Model(
    1607392400, "Yakuza0 Term",
    fields=[{"name": n} for n in ["Word", "Reading", "Meaning", "Example", "POS", "English", "Official",
                                   "Furigana", "WordAudio"]],
    templates=[{
        "name": "Term",
        "qfmt": '<div class="word">{{Word}}</div>',
        "afmt": '<div class="word">{{furigana:Furigana}}</div>{{WordAudio}}<hr id="answer">'
                '<div class="mean">{{Meaning}}</div>'
                '{{#Example}}<div class="ex">{{Example}}</div>{{/Example}}'
                '{{#English}}<div class="eng">{{English}}</div>{{/English}}'
                '{{#Official}}<div class="official">official: {{Official}}</div>{{/Official}}'
                '<div class="pos">{{POS}}</div>',
    }],
    css=".card{font-family:'Meiryo','Yu Gothic',sans-serif;text-align:center;color:#111;background:#fff}"
        ".word{font-size:40px;font-weight:700;margin:24px}.word rt{font-size:17px;font-weight:400;color:#0a7}"
        ".read{color:#0a7;font-size:22px}.mean{margin:12px;font-size:22px}"
        ".ex{color:#555;font-size:18px;margin:10px}.pos{color:#999;font-size:14px}"
        ".eng{color:#234;font-size:16px;margin:4px 10px}"
        ".official{color:#888;font-size:14px;font-style:italic;margin:4px 10px}",
)


def extra_fields(word, reading, media, audio=True):
    """[Furigana, WordAudio] for a Term note; adds the audio file path to `media`.
    audio=False for proper nouns (names deck): JPod101 has no character names, and a
    homograph hit would voice the dictionary word, not the name."""
    wa = word_clip(word, reading) if audio else None
    if wa:
        media.append(os.path.join(AUDIO, "words", wa))
    return [furigana(word, reading), f"[sound:{wa}]" if wa else ""]
