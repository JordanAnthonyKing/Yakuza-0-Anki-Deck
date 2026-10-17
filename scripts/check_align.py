import json, os, sys
DATA = r"C:\Users\jordan\repos\yakuza\data"
from build_align import get_msgs, midfracs, clean_txt   # reuse the real logic
rows = {x["order"]: x for x in json.load(open(os.path.join(DATA, "align_ch1.json"), encoding="utf-8"))}
for o in ([int(a) for a in sys.argv[1:]] or [0, 2, 9, 55, 63, 74]):
    x = rows[o]
    ja, en, parity = get_msgs(x["uid"])
    sent = clean_txt(x["sentence"])
    idx = next((i for i, a in enumerate(ja) if sent in a or a in sent), None)
    print(f"\n[{o}] {x['word']}  uid {x['uid']}  JA={len(ja)} EN={len(en)}  jaIdx={idx}")
    print(f"   JA: {sent[:40]}")
    if idx is not None and en:
        fj, fe = midfracs(ja), midfracs(en)
        j = min(range(len(en)), key=lambda k: abs(fe[k] - fj[idx]))
        for k in range(max(0, j-2), min(len(en), j+3)):
            print(f"   EN[{k}]{'*' if k==j else ' '} {en[k][:60]}")
