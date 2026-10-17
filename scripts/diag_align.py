"""Diagnose alignment drift for one card's file: print JA and EN message lists side by
side with indices so we can see where counts diverge and whether length-proportional
alignment would fix the offset. Usage: python diag_align.py <order>
"""
import os, re, glob, json, sys

BASE = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad"
DATA = r"C:\Users\jordan\repos\yakuza\data"
JP = re.compile(r"[぀-ヿ一-龯ｦ-ﾟ]")
ENW = re.compile(r"[A-Za-z]{2,}"); VOW = re.compile(r"[aeiouAEIOU]")

def clean_txt(s, ja=True):
    s = re.sub(r"<[^>]*>", "", s); s = re.sub(r"[\r\n]+", "" if ja else " ", s)
    s = s.replace("�", "").strip()
    if not ja:
        s = re.sub(r"^\d+\s*", "", s); s = re.sub(r"\s{2,}", " ", s)
    return s

def messages(path, ja):
    out = []
    for part in open(path, "rb").read().split(b"\x00"):
        s = clean_txt(part.decode("utf-8", "replace"), ja)
        if not s: continue
        if ja:
            if JP.search(s): out.append(s)
        elif ENW.search(s) and VOW.search(s) and (len(s) >= 4 or " " in s):
            out.append(s)
    return out

order = int(sys.argv[1])
rows = {r["order"]: r for r in json.load(open(os.path.join(DATA, "align_ch1.json"), encoding="utf-8"))}
uid = rows[order]["uid"]
sent = rows[order]["sentence"]
jp = next(p for p in glob.glob(os.path.join(BASE, "wdrj", "msg", "**", f"uid{uid}.msg"), recursive=True))
ep = jp.replace(os.sep+"wdrj"+os.sep, os.sep+"wdr"+os.sep)
ja, en = messages(jp, True), messages(ep, False)
print(f"order {order} uid {uid}: JA msgs={len(ja)}  EN msgs={len(en)}  target=[{sent[:30]}]\n")
ji = next((i for i,a in enumerate(ja) if sent in a or a in sent), None)
print(f"JA target index = {ji}\n")
for i in range(max(len(ja), len(en))):
    a = ja[i][:34] if i < len(ja) else ""
    e = en[i][:44] if i < len(en) else ""
    mark = " <== target" if i == ji else ""
    print(f"  [{i:2}] {a:36} | {e}{mark}")
