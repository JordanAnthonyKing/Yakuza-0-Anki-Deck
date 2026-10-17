import json,os
DATA=r"C:\Users\jordan\repos\yakuza\data"
SCR=r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\661dd7e3-534c-470c-9106-33c76f67f358\scratchpad"
b={str(r["order"]):r for r in json.load(open(os.path.join(SCR,"ab_batch.json"),encoding="utf-8"))}
o=json.load(open(os.path.join(DATA,"ab_opus.json"),encoding="utf-8"))
s=json.load(open(os.path.join(DATA,"ab_sonnet.json"),encoding="utf-8"))
for k in list(sorted(b,key=int))[:8]:
    print("JA:",b[k]["sentence"][:40])
    print("  O:",o[k]["literal"])
    print("  S:",s[k]["literal"])
