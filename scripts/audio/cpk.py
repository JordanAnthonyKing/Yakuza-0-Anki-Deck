import sys,struct; sys.path.insert(0,sys.argv[0].rsplit('/',1)[0] if '/' in sys.argv[0] else '.')
from criutf import utf
def index(path):
    f=open(path,'rb'); hdr=f.read(0x10000)
    h=utf(hdr[0x10:])[0]
    f.seek(h['ItocOffset']); it=f.read(h['ItocSize'])
    info=utf(it[0x10:])[0]
    ents={}
    for k in ('DataL','DataH'):
        if info.get(k):
            for r in utf(info[k]): ents[r['ID']]=(r['FileSize'],r['ExtractSize'])
    align=h['Align']; off=h['ContentOffset']; out={}
    for i in sorted(ents):
        out[i]=(off,ents[i][0]); off+=ents[i][0]
        if off%align: off+=align-off%align
    return h,out
if __name__=='__main__':
    h,idx=index(sys.argv[1]); print({k:v for k,v in h.items() if not isinstance(v,bytes)}); print(len(idx), min(idx), max(idx))
    for i in list(idx)[:3]: print(i,idx[i])
    if len(sys.argv)>3:
        f=open(sys.argv[1],'rb')
        for i in sys.argv[3:]:
            o,s=idx[int(i,16)]; f.seek(o); d=f.read(s); open(f'{sys.argv[2]}/{i}.awb','wb').write(d); print(i,s,d[:4])
