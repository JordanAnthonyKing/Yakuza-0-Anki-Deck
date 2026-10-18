import sys,glob,os,json,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); sys.stdout.reconfigure(encoding='utf-8')
from criutf import utf
out={}; bad=0
for f in sorted(glob.glob(sys.argv[1]+'/*.acb')):
    try:
        h=utf(open(f,'rb').read())[0]
        cues=[r['CueName'] for r in utf(h['CueNameTable'])] if h.get('CueNameTable') else []
        out[os.path.basename(f)[:-4]]=dict(name=h.get('Name'),cues=cues,stream=bool(h.get('StreamAwbAfs2Header') or h.get('StreamAwbHash')))
    except Exception as e: bad+=1
print(len(out),'bad',bad)
names=[v['name'] for v in out.values()]
print(names[:5], [n for n in names if n and 'c01_160' in n][:5])
print(sorted(set(re.sub(r'\d','9',n or '') for n in names), key=lambda s:-sum(1 for n in names if re.sub(r'\d','9',n or '')==s))[:25])
json.dump(out,open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False)
