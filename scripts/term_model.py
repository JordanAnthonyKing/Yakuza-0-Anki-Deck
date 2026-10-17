"""The word-first Term note type shared by the ch0, minigame and names decks (id 1607392400).

ONE definition: Anki keys note types by id, so every deck using this id must declare the
identical field list or imports conflict. English/Official are the example sentence's
literal translation and (gate-passed) official localization; blank when there's none.
"""
import genanki

MODEL = genanki.Model(
    1607392400, "Yakuza0 Term",
    fields=[{"name": n} for n in ["Word", "Reading", "Meaning", "Example", "POS", "English", "Official"]],
    templates=[{
        "name": "Term",
        "qfmt": '<div class="word">{{Word}}</div>',
        "afmt": '{{FrontSide}}<hr id="answer"><div class="read">{{Reading}}</div>'
                '<div class="mean">{{Meaning}}</div>'
                '{{#Example}}<div class="ex">{{Example}}</div>{{/Example}}'
                '{{#English}}<div class="eng">{{English}}</div>{{/English}}'
                '{{#Official}}<div class="official">official: {{Official}}</div>{{/Official}}'
                '<div class="pos">{{POS}}</div>',
    }],
    css=".card{font-family:'Meiryo','Yu Gothic',sans-serif;text-align:center;color:#111;background:#fff}"
        ".word{font-size:40px;font-weight:700;margin:24px}"
        ".read{color:#0a7;font-size:22px}.mean{margin:12px;font-size:22px}"
        ".ex{color:#555;font-size:18px;margin:10px}.pos{color:#999;font-size:14px}"
        ".eng{color:#234;font-size:16px;margin:4px 10px}"
        ".official{color:#888;font-size:14px;font-style:italic;margin:4px 10px}",
)
