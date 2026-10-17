"""Do msg files embed scene/substory codes we can use for chapter tagging?
Scan every .msg for ASCII tokens like a01_010 / STID_* / SUB_A01 / talk ids."""
import os, re, glob, collections

WDR = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\wdrj\msg"

pat_scene = re.compile(rb"[aAfFcCbB][0-9]{2}[_-][0-9]{3}")
pat_stid  = re.compile(rb"STID_[A-Z0-9_]+")
pat_sub   = re.compile(rb"(SUB|SHP|NJM)_A[0-9]{2}[A-Z0-9_]*")
pat_any_ascii = re.compile(rb"[\x20-\x7e]{4,}")

files = glob.glob(os.path.join(WDR, "**", "*.msg"), recursive=True)
n_scene=n_stid=n_sub=0
scene_examples=[]; sub_examples=[]; ascii_sample=[]
allcodes=collections.Counter()
for p in files:
    d=open(p,"rb").read()
    s=pat_scene.findall(d); t=pat_stid.findall(d); u=pat_sub.findall(d)
    if s: n_scene+=1; scene_examples += [(os.path.basename(p), x.decode()) for x in s[:1]]
    if t: n_stid+=1
    if u: n_sub+=1; sub_examples += [(os.path.basename(p), x.decode()) for x in u[:1]]
    for c in s+t+u: allcodes[c.decode()]+=1
    if len(ascii_sample)<25:
        for a in pat_any_ascii.findall(d):
            a=a.decode()
            if not a.startswith("[") : ascii_sample.append((os.path.basename(p),a))
            if len(ascii_sample)>=25: break

print(f"total msg: {len(files)}")
print(f"files with scene code (aNN_NNN): {n_scene}")
print(f"files with STID_ code: {n_stid}")
print(f"files with SUB/SHP/NJM code: {n_sub}")
print("scene examples:", scene_examples[:15])
print("sub examples:", sub_examples[:15])
print("top embedded codes:", allcodes.most_common(20))
print("\nsample ascii tokens inside msgs (non-tag):")
for f,a in ascii_sample[:25]: print("  ",f,repr(a))
