"""Rebuild the Chapter 1 story deck with polished glosses + gated English translations.

Applies gloss_polish_ch1.json (meaning) and translate_ch1_part*.json (literal English +
official localization when the gate passed) onto cards_ch1_1.json. Card back now shows a
literal learner translation and, when it passed the gate, the official localized line.

Usage: python build_final.py <ch>          # full deck for chapter <ch> (untranslated cards keep blank fields)
       python build_final.py <ch> subset   # only cards that have a translation (pilot review)
"""
import os, re, json, glob, sys
import genanki
from build_deck import DATA, strip_orphan_brackets
from keep_guids import old_guids, guid
from furigana import furigana
from audio_policy import word_clip

lo = hi = next((int(a) for a in sys.argv[1:] if a.isdigit()), 1)
subset = "subset" in sys.argv

cards = json.load(open(os.path.join(DATA, f"cards_ch{lo}_{hi}.json"), encoding="utf-8"))
polish = json.load(open(os.path.join(DATA, f"gloss_polish_ch{lo}.json"), encoding="utf-8"))
trans = {}                                   # canonical per-chapter range files
for p in sorted(glob.glob(os.path.join(DATA, "translate", f"ch{lo}", "*.json"))):
    trans.update(json.load(open(p, encoding="utf-8")))
print(f"cards {len(cards)}, polished {len(polish)}, translations {len(trans)}")

# audio layer (scripts/audio/): full text box + game voice clip per card, JPod101 word audio
AUD = os.path.join(DATA, "audio")
_sp = os.path.join(AUD, f"sentence_ch{lo}.json")
sent_audio = json.load(open(_sp, encoding="utf-8")) if os.path.exists(_sp) else {}
media = set()

MODEL = genanki.Model(
    1607392320, "Yakuza0 i+1 (translated)",
    fields=[{"name": n} for n in ["Sentence", "Word", "Reading", "Meaning",
                                   "English", "Official", "POS", "Chapter", "Speaker", "UID",
                                   "FullLine", "WordAudio", "SentenceAudio", "Furigana"]],
    templates=[{
        "name": "Recognition",
        "qfmt": '<div class="sent">{{Sentence}}</div><div class="spk">{{Speaker}} · Ch.{{Chapter}}</div>',
        "afmt": '{{FrontSide}}<hr id="answer"><div class="word">{{furigana:Furigana}}</div>'
                '{{WordAudio}}<div class="mean">{{Meaning}}</div>'
                '<div class="pos">{{POS}}</div>'
                '<div class="eng">{{English}}</div>'
                '{{#Official}}<div class="official">official: {{Official}}</div>{{/Official}}'
                '{{#SentenceAudio}}<div class="full">{{FullLine}}</div>{{SentenceAudio}}{{/SentenceAudio}}',
    }],
    css=".card{font-family:'Meiryo','Yu Gothic',sans-serif;font-size:22px;text-align:center;color:#111;background:#fff}"
        ".sent{font-size:26px;margin:14px}.spk{color:#888;font-size:14px}"
        ".word{font-size:34px;font-weight:700;margin-top:12px}.word rt{font-size:15px;font-weight:400;color:#0a7}.read{color:#0a7;font-size:20px}"
        ".mean{margin:8px;font-size:20px}.pos{color:#999;font-size:14px} b{color:#c00}"
        ".eng{margin-top:14px;font-size:19px;color:#234}"
        ".official{margin-top:8px;font-size:16px;color:#888;font-style:italic}"
        ".full{margin:18px auto 6px;padding:10px 14px;max-width:34em;font-size:20px;line-height:1.6;"
        "border-top:1px solid #ddd;color:#444}"
        ".full .hl{background:#fff1a8;color:#111}.full .hl b{background:#ffc94d;color:#111;font-weight:700}"
        ".nightMode .full{color:#bbb;border-color:#444}.nightMode .full .hl{background:#5a4d12;color:#eee}"
        ".nightMode .full .hl b{background:#a0700a;color:#fff}",
)

out = os.path.join(DATA, "decks"); os.makedirs(out, exist_ok=True)
path = os.path.join(out, f"yakuza0_ch{lo}" + ("_pilot" if subset else "") + ".apkg")
old = old_guids(path)                        # key (Sentence, Word) -> guid already in Anki

from deck_names import chapter as chapter_deck
deck = genanki.Deck(2059400110 + lo, chapter_deck(lo) + (" (pilot)" if subset else ""))
n_eng = n_off = added = 0
for c in cards:
    key = str(c["order"])
    g = polish.get(c["word"])
    meaning = g.strip() if g and g.strip() else c["meaning"]
    t = trans.get(key)
    if subset and not t:
        continue
    english = official = ""
    if t:
        english = (t.get("literal") or "").strip(); n_eng += bool(english)
        if t.get("official_ok"):
            official = (t.get("official") or "").strip(); n_off += bool(official)
    sa = sent_audio.get(key, {})
    wa = word_clip(c["word"], c["reading"])
    for m in (sa.get("clip"), wa):
        if m:
            media.add(m)
    fields = [strip_orphan_brackets(c["sentence"]), c["word"], c["reading"], meaning, english, official,
              c["pos"], str(c["chapter"]), c.get("speaker", ""), c["uid"],
              sa.get("full", ""), f"[sound:{wa}]" if wa else "",
              f'[sound:{sa["clip"]}]' if sa.get("clip") else "", furigana(c["word"], c["reading"])]
    # a card whose Word was corrected after import carries its original guid
    deck.add_note(genanki.Note(model=MODEL, fields=fields, guid=c.get("guid") or guid(old, fields)))
    added += 1

genanki.Package(deck, media_files=sorted(
    os.path.join(AUD, "clips" if m.startswith("y0v_") else "words", m) for m in media)).write_to_file(path)
print(f"wrote {path}: {added} cards, {n_eng} with literal EN, {n_off} with official EN, "
      f"{len(media)} audio files")
