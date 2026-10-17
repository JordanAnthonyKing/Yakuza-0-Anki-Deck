"""Parse the Yakuza 0 English transcript into chapter -> [(speaker, line)] and save JSON."""
import re, html, json, os

HTML = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\transcript.html"
OUT  = r"C:\Users\jordan\repos\yakuza\data\transcript_chapters.json"
raw = open(HTML, encoding="utf-8", errors="replace").read()

# Split on body anchors <a name="chN">
anchors = list(re.finditer(r'<a name="ch(\d+)">', raw))
chapters = {}
for i, a in enumerate(anchors):
    num = int(a.group(1))
    start = a.end()
    end = anchors[i+1].start() if i+1 < len(anchors) else len(raw)
    seg = raw[start:end]
    # dialogue: <b>Speaker:</b> text  (until next <b> or <br><br> or stage direction)
    seg2 = re.sub(r'<br\s*/?>', '\n', seg, flags=re.I)
    lines = []
    # capture bold speaker then following text up to next bold tag
    for mm in re.finditer(r'<b>\s*(.*?)\s*</b>(.*?)(?=<b>|\Z)', seg2, re.S):
        spk = html.unescape(re.sub(r'<[^>]+>', '', mm.group(1))).strip().rstrip(':').strip()
        line = html.unescape(re.sub(r'<[^>]+>', '', mm.group(2)))
        line = re.sub(r'\s+', ' ', line).strip()
        if line:
            lines.append((spk, line))
    # also keep the raw stripped chapter text for bag-of-words matching
    ctext = html.unescape(re.sub(r'<[^>]+>', ' ', seg2))
    ctext = re.sub(r'\s+', ' ', ctext).strip()
    chapters[num] = {"lines": lines, "text": ctext}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(chapters, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print("chapters:", sorted(int(k) for k in chapters))
for c in sorted(chapters, key=int):
    d = chapters[c]
    spks = [s for s,_ in d["lines"]]
    from collections import Counter
    top = [f"{s}({n})" for s,n in Counter(spks).most_common(6)]
    print(f"  ch{int(c):02}: {len(d['lines']):4} lines, {len(d['text'].split()):6} words | speakers: {top}")
print("\nCh1 first 6 lines:")
for s,l in chapters[1]["lines"][:6]:
    print(f"   {s}: {l[:70]}")
