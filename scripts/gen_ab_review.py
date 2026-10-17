"""Side-by-side Opus vs Sonnet comparison page for the A/B batch (orders 90-134)."""
import os, json
from build_deck import strip_orphan_brackets

DATA = r"C:\Users\jordan\repos\yakuza\data"
SCRATCH = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\661dd7e3-534c-470c-9106-33c76f67f358\scratchpad"
OUT = os.path.join(SCRATCH, "ab_review.html")

batch = {str(r["order"]): r for r in json.load(open(os.path.join(SCRATCH, "ab_batch.json"), encoding="utf-8"))}
opus = json.load(open(os.path.join(DATA, "ab_opus.json"), encoding="utf-8"))
sonnet = json.load(open(os.path.join(DATA, "ab_sonnet.json"), encoding="utf-8"))

rows = []
for k in sorted(batch, key=int):
    b = batch[k]; o = opus.get(k, {}); s = sonnet.get(k, {})
    rows.append({
        "order": int(k), "word": b["word"], "reading": b["reading"], "meaning": b["meaning"],
        "speaker": b.get("speaker", ""),
        "sentence": strip_orphan_brackets(f'<b>{b["word"]}</b>' if b["word"] in b["sentence"] and "<b>" not in b["sentence"] else b["sentence"]),
        "o_lit": (o.get("literal") or "").strip(), "o_off": (o.get("official") or "").strip() if o.get("official_ok") else "",
        "s_lit": (s.get("literal") or "").strip(), "s_off": (s.get("official") or "").strip() if s.get("official_ok") else "",
        "o_ok": bool(o.get("official_ok")), "s_ok": bool(s.get("official_ok")),
    })

o_kept = sum(r["o_ok"] for r in rows); s_kept = sum(r["s_ok"] for r in rows)
gate_agree = sum(r["o_ok"] == r["s_ok"] for r in rows)
off_diff = sum(1 for r in rows if r["o_ok"] and r["s_ok"] and r["o_off"] != r["s_off"])
payload = json.dumps({"rows": rows}, ensure_ascii=False)

CSS = """
:root{--bg:#f4f1f0;--panel:#fffdfc;--line:#e4dee0;--ink:#211c26;--muted:#7c7486;--accent:#d11e63;
 --opus:#6c4bd8;--sonnet:#0f9d74;--none:#c77d1a;
 --jp:"Hiragino Kaku Gothic ProN","Yu Gothic","Meiryo",system-ui,sans-serif;
 --sans:system-ui,-apple-system,"Segoe UI",sans-serif;--serif:"Iowan Old Style","Palatino Linotype",Georgia,serif;
 --mono:ui-monospace,"Cascadia Code",Consolas,monospace;}
@media (prefers-color-scheme:dark){:root{--bg:#141019;--panel:#1d1824;--line:#2e2738;--ink:#ece7f2;--muted:#a097b0;
 --accent:#ff3d7f;--opus:#a78bff;--sonnet:#2fd3a4;--none:#f0a542;}}
:root[data-theme="light"]{--bg:#f4f1f0;--panel:#fffdfc;--line:#e4dee0;--ink:#211c26;--muted:#7c7486;--accent:#d11e63;--opus:#6c4bd8;--sonnet:#0f9d74;--none:#c77d1a;}
:root[data-theme="dark"]{--bg:#141019;--panel:#1d1824;--line:#2e2738;--ink:#ece7f2;--muted:#a097b0;--accent:#ff3d7f;--opus:#a78bff;--sonnet:#2fd3a4;--none:#f0a542;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);line-height:1.5;font-feature-settings:"tnum"}
.wrap{max-width:1040px;margin:0 auto;padding:32px 20px 80px}
header{border-bottom:1px solid var(--line);padding-bottom:20px;margin-bottom:22px}
.kicker{font-family:var(--mono);text-transform:uppercase;letter-spacing:.16em;font-size:11px;color:var(--accent);margin:0 0 6px}
h1{font-family:var(--serif);font-weight:600;font-size:29px;margin:0;letter-spacing:-.01em}
.tiles{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}
.tile{flex:1 1 150px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.tile .num{font-family:var(--mono);font-size:24px;font-weight:600}
.tile .lab{font-size:11px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);margin-top:2px}
.tile.o .num{color:var(--opus)} .tile.s .num{color:var(--sonnet)}
.controls{display:flex;gap:8px;margin:20px 0 4px}
.filter{font-family:var(--mono);font-size:12px;color:var(--muted);background:transparent;border:1px solid var(--line);border-radius:99px;padding:6px 13px;cursor:pointer}
.filter[aria-pressed="true"]{color:var(--bg);background:var(--ink);border-color:var(--ink)}
.filter:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.list{display:flex;flex-direction:column;gap:14px;margin-top:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card.disagree{border-color:var(--none);box-shadow:inset 3px 0 0 var(--none)}
.meta{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;margin-bottom:6px}
.ord{font-family:var(--mono);font-size:12px;color:var(--muted)}
.word{font-family:var(--jp);font-size:20px;font-weight:700}
.read{font-family:var(--jp);color:var(--sonnet);font-size:13px}
.gloss{font-size:13px;color:var(--muted)}
.spk{font-size:12px;color:var(--muted);margin-left:auto}
.badge{font-family:var(--mono);font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--none);border:1px solid var(--none);border-radius:5px;padding:1px 6px}
.sent{font-family:var(--jp);font-size:18px;line-height:1.7;margin:6px 0 12px}
.sent b{color:var(--accent);font-weight:700}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:640px){.cols{grid-template-columns:1fr}}
.col{border:1px solid var(--line);border-radius:9px;padding:10px 12px}
.col h4{margin:0 0 8px;font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.1em}
.col.opus h4{color:var(--opus)} .col.sonnet h4{color:var(--sonnet)}
.lit{font-family:var(--serif);font-size:15px}
.off{font-family:var(--serif);font-style:italic;font-size:13px;color:var(--muted);margin-top:7px;padding-top:7px;border-top:1px dashed var(--line)}
.off.no{font-family:var(--sans);font-style:normal;color:var(--none)}
.foot{margin-top:26px;color:var(--muted);font-size:13px;text-align:center}
"""

JS = """
const D=window.__DATA__;const list=document.getElementById('list');
function esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function off(v){return v?`<div class="off">official: ${esc(v)}</div>`:`<div class="off no">no official</div>`;}
function draw(f){list.innerHTML='';
 D.rows.filter(r=> f==='all' || (f==='dis'&&r.o_ok!==r.s_ok) || (f==='offdiff'&&r.o_ok&&r.s_ok&&r.o_off!==r.s_off)).forEach(r=>{
  const el=document.createElement('div');el.className='card'+(r.o_ok!==r.s_ok?' disagree':'');
  const badge=r.o_ok!==r.s_ok?'<span class="badge">gate disagree</span>':'';
  const spk=r.speaker?`<span class="spk">${esc(r.speaker)}</span>`:'';
  el.innerHTML=`<div class="meta"><span class="ord">#${r.order}</span><span class="word">${esc(r.word)}</span>
    <span class="read">${esc(r.reading)}</span><span class="gloss">${esc(r.meaning)}</span>${badge}${spk}</div>
   <div class="sent">${r.sentence}</div>
   <div class="cols">
     <div class="col opus"><h4>Opus</h4><div class="lit">${esc(r.o_lit)}</div>${off(r.o_off)}</div>
     <div class="col sonnet"><h4>Sonnet</h4><div class="lit">${esc(r.s_lit)}</div>${off(r.s_off)}</div>
   </div>`;
  list.appendChild(el);});
}
document.querySelectorAll('.filter').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.filter').forEach(x=>x.setAttribute('aria-pressed','false'));
 b.setAttribute('aria-pressed','true');draw(b.dataset.f);}));
draw('all');
"""

body = f"""<div class="wrap">
<header>
  <p class="kicker">Yakuza 0 · Model A/B</p>
  <h1>Opus vs Sonnet — Chapter 1 translations (orders 90–134)</h1>
  <div class="tiles">
    <div class="tile"><div class="num">{len(rows)}</div><div class="lab">cards (same input)</div></div>
    <div class="tile o"><div class="num">{o_kept}</div><div class="lab">Opus official kept</div></div>
    <div class="tile s"><div class="num">{s_kept}</div><div class="lab">Sonnet official kept</div></div>
    <div class="tile"><div class="num">{gate_agree}</div><div class="lab">gate agreement</div></div>
    <div class="tile"><div class="num">{off_diff}</div><div class="lab">same-keep, diff line</div></div>
  </div>
</header>
<div class="controls">
  <button class="filter" data-f="all" aria-pressed="true">All {len(rows)}</button>
  <button class="filter" data-f="dis" aria-pressed="false">Gate disagreements {len(rows)-gate_agree}</button>
  <button class="filter" data-f="offdiff" aria-pressed="false">Diff official line {off_diff}</button>
</div>
<div class="list" id="list"></div>
<p class="foot">Same 45 cards, identical inputs, ±5 alignment window. Compare literal-translation wording and each model's gate decision. Cards where the two models disagree on keeping the official line are outlined.</p>
</div>
<script>window.__DATA__={payload};</script>
<style>{CSS}</style>
<script>{JS}</script>"""
open(OUT, "w", encoding="utf-8").write(body)
print("wrote", OUT, f"| Opus kept {o_kept}, Sonnet kept {s_kept}, gate agree {gate_agree}/{len(rows)}, diff-line {off_diff}")
