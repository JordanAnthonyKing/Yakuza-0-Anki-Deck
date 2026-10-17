"""Generate the Chapter-1 pilot translation review page (HTML) from the built data."""
import os, json, html
from build_deck import strip_orphan_brackets

DATA = r"C:\Users\jordan\repos\yakuza\data"
OUT = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\661dd7e3-534c-470c-9106-33c76f67f358\scratchpad\ch1_review.html"

cards = {c["order"]: c for c in json.load(open(os.path.join(DATA, "cards_ch1_1.json"), encoding="utf-8"))}
polish = json.load(open(os.path.join(DATA, "gloss_polish_ch1.json"), encoding="utf-8"))
trans = {}
for i in (1, 2):
    trans.update(json.load(open(os.path.join(DATA, f"translate_ch1_part{i}.json"), encoding="utf-8")))

rows = []
for key in sorted(trans, key=lambda k: int(k)):
    o = int(key); c = cards[o]; t = trans[key]
    rows.append({
        "order": o, "word": c["word"], "reading": c["reading"],
        "pos": c["pos"], "speaker": c.get("speaker", ""),
        "sentence": strip_orphan_brackets(c["sentence"]),  # contains <b>..</b>
        "meaning": (polish.get(c["word"]) or c["meaning"]).strip(),
        "literal": (t.get("literal") or "").strip(),
        "official": (t.get("official") or "").strip() if t.get("official_ok") else "",
        "ok": bool(t.get("official_ok")),
    })

n = len(rows); n_off = sum(r["ok"] for r in rows)
stats = {"total": n, "literal": sum(1 for r in rows if r["literal"]),
         "official": n_off, "nooff": n - n_off}
payload = json.dumps({"rows": rows, "stats": stats}, ensure_ascii=False)

CSS = """
:root{
  --bg:#f4f1f0; --panel:#fffdfc; --line:#e4dee0; --ink:#211c26; --muted:#7c7486;
  --accent:#d11e63; --kept:#0f9d74; --none:#c77d1a;
  --jp:"Hiragino Kaku Gothic ProN","Yu Gothic","Meiryo",system-ui,sans-serif;
  --sans:system-ui,-apple-system,"Segoe UI",sans-serif;
  --serif:"Iowan Old Style","Palatino Linotype",Georgia,"Times New Roman",serif;
  --mono:ui-monospace,"Cascadia Code","SFMono-Regular",Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#141019; --panel:#1d1824; --line:#2e2738; --ink:#ece7f2; --muted:#a097b0;
  --accent:#ff3d7f; --kept:#2fd3a4; --none:#f0a542;
}}
:root[data-theme="light"]{--bg:#f4f1f0;--panel:#fffdfc;--line:#e4dee0;--ink:#211c26;--muted:#7c7486;--accent:#d11e63;--kept:#0f9d74;--none:#c77d1a;}
:root[data-theme="dark"]{--bg:#141019;--panel:#1d1824;--line:#2e2738;--ink:#ece7f2;--muted:#a097b0;--accent:#ff3d7f;--kept:#2fd3a4;--none:#f0a542;}

*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);line-height:1.5;
  font-feature-settings:"tnum";-webkit-font-smoothing:antialiased}
.wrap{max-width:940px;margin:0 auto;padding:32px 20px 80px}
header{border-bottom:1px solid var(--line);padding-bottom:20px;margin-bottom:22px}
.kicker{font-family:var(--mono);text-transform:uppercase;letter-spacing:.16em;font-size:11px;color:var(--accent);margin:0 0 6px}
h1{font-family:var(--serif);font-weight:600;font-size:30px;margin:0;letter-spacing:-.01em;text-wrap:balance}
h1 .sub{color:var(--muted);font-style:italic;font-weight:400}
.tiles{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}
.tile{flex:1 1 130px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.tile .num{font-family:var(--mono);font-size:26px;font-weight:600;letter-spacing:-.02em}
.tile .lab{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin-top:2px}
.tile.k .num{color:var(--kept)} .tile.n .num{color:var(--none)}
.controls{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0 4px;align-items:center}
.filter{font-family:var(--mono);font-size:12px;color:var(--muted);background:transparent;border:1px solid var(--line);
  border-radius:99px;padding:6px 13px;cursor:pointer}
.filter[aria-pressed="true"]{color:var(--bg);background:var(--ink);border-color:var(--ink)}
.filter:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.list{display:flex;flex-direction:column;gap:12px;margin-top:16px}
.card{display:grid;grid-template-columns:64px 1fr;gap:0;background:var(--panel);border:1px solid var(--line);
  border-left:3px solid var(--kept);border-radius:12px;overflow:hidden}
.card.nooff{border-left-color:var(--none)}
.rail{padding:14px 0 14px 14px}
.ord{font-family:var(--mono);font-size:12px;color:var(--muted)}
.body{padding:14px 16px 14px 12px;min-width:0}
.meta{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;margin-bottom:8px}
.word{font-family:var(--jp);font-size:22px;font-weight:700}
.read{font-family:var(--jp);color:var(--kept);font-size:14px}
.pos{font-family:var(--mono);font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);
  border:1px solid var(--line);border-radius:5px;padding:1px 6px}
.spk{font-size:12px;color:var(--muted);margin-left:auto}
.gloss{font-size:14px;color:var(--muted);margin-bottom:10px}
.sent{font-family:var(--jp);font-size:19px;line-height:1.7;margin-bottom:12px}
.sent b{color:var(--accent);font-weight:700}
.tr{display:grid;grid-template-columns:76px 1fr;gap:10px;align-items:baseline;padding:6px 0;border-top:1px dashed var(--line)}
.tr .tag{font-family:var(--mono);font-size:10px;text-transform:uppercase;letter-spacing:.08em;padding-top:3px}
.tr.lit .tag{color:var(--ink)} .tr.off .tag{color:var(--kept)} .tr.non .tag{color:var(--none)}
.tr .val{font-family:var(--serif);font-size:16px}
.tr.off .val{font-style:italic;color:var(--muted)}
.tr.non .val{font-family:var(--sans);font-size:13px;color:var(--none)}
.foot{margin-top:26px;color:var(--muted);font-size:13px;text-align:center}
"""

JS = """
const D=window.__DATA__;const list=document.getElementById('list');
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function draw(f){
  list.innerHTML='';
  D.rows.filter(r=>f==='all'||(f==='off'&&r.ok)||(f==='non'&&!r.ok)).forEach(r=>{
    const el=document.createElement('div');el.className='card'+(r.ok?'':' nooff');
    const spk=r.speaker?`<span class="spk">${esc(r.speaker)}</span>`:'';
    const off=r.ok
      ?`<div class="tr off"><span class="tag">official</span><span class="val">${esc(r.official)}</span></div>`
      :`<div class="tr non"><span class="tag">official</span><span class="val">no faithful match — rejected by gate</span></div>`;
    el.innerHTML=`<div class="rail"><div class="ord">#${r.order}</div></div>
      <div class="body">
        <div class="meta"><span class="word">${esc(r.word)}</span><span class="read">${esc(r.reading)}</span>
          <span class="pos">${esc(r.pos)}</span>${spk}</div>
        <div class="gloss">${esc(r.meaning)}</div>
        <div class="sent">${r.sentence}</div>
        <div class="tr lit"><span class="tag">literal</span><span class="val">${esc(r.literal)}</span></div>
        ${off}
      </div>`;
    list.appendChild(el);
  });
}
document.querySelectorAll('.filter').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('.filter').forEach(x=>x.setAttribute('aria-pressed','false'));
  b.setAttribute('aria-pressed','true');draw(b.dataset.f);
}));
draw('all');
"""

s = stats
body = f"""<div class="wrap">
<header>
  <p class="kicker">Yakuza 0 · Deck QA</p>
  <h1>Chapter 1 pilot — <span class="sub">translation &amp; official-line review</span></h1>
  <div class="tiles">
    <div class="tile"><div class="num">{s['total']}</div><div class="lab">cards</div></div>
    <div class="tile"><div class="num">{s['literal']}</div><div class="lab">literal EN</div></div>
    <div class="tile k"><div class="num">{s['official']}</div><div class="lab">official kept</div></div>
    <div class="tile n"><div class="num">{s['nooff']}</div><div class="lab">no official</div></div>
  </div>
</header>
<div class="controls">
  <button class="filter" data-f="all" aria-pressed="true">All {s['total']}</button>
  <button class="filter" data-f="off" aria-pressed="false">Official kept {s['official']}</button>
  <button class="filter" data-f="non" aria-pressed="false">No official {s['nooff']}</button>
</div>
<div class="list" id="list"></div>
<p class="foot">Literal = Opus translation (always shown). Official = SEGA localization, shown only when the gate judged it a faithful rendering (reordering allowed). The target word is highlighted.</p>
</div>
<script>window.__DATA__={payload};</script>
<style>{CSS}</style>
<script>{JS}</script>"""

open(OUT, "w", encoding="utf-8").write(body)
print("wrote", OUT, f"({n} rows, {n_off} official)")
