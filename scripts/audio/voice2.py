import sys,re,struct,glob,json,os,collections,subprocess,wave,shutil
sys.path.insert(0,'scripts'); sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); sys.stdout.reconfigure(encoding='utf-8')
import msg_speakers as m
from cpk import index
S=os.path.dirname(os.path.abspath(__file__))
R=os.path.abspath(os.path.join(S,'..','..'))
D=R+'/data/audio'
acb=json.load(open(D+'/acb_index.json',encoding='utf-8'))
def msgs(path):
    d=open(path,'rb').read()
    if len(d)<0x24: return []
    names=m._names(d); recs,first={},len(d)
    for r in range(0x18,len(d)-12,4):
        if r>=first: break
        t,c=struct.unpack('>II',d[r:r+8])
        if 0<c<t<len(d) and c%4==0 and d[t-1]==0 and d[c:c+4]==b'\x01\x00\x00\x00' and t not in recs:
            recs[t]=c; first=min(first,t)
    starts=sorted(set(recs.values())); out=[]
    for t,c in sorted(recs.items()):
        text=m._cstr(d,t)
        if not m.JP.search(text): continue
        nxt=next((x for x in starts if x>c),c+16*24); v=None
        for k in range(c,min(nxt,len(d)-16),16):
            if d[k]==3 and d[k+1]==0x35:
                ni=struct.unpack('>H',d[k+2:k+4])[0]&0x3fff
                a,ci=struct.unpack('>HH',d[k+8:k+12]); a='%04x'%a
                cues=acb.get(a,{}).get('cues',[])
                v=dict(name=names[ni] if ni<len(names) else '',acb=a,cue=cues[ci] if ci<len(cues) else None); break
        out.append((text,v))
    return out
if sys.argv[1]=='map':
    vm={}
    for f in glob.glob('source/wdrj/msg/**/*.msg',recursive=True):
        uid=os.path.basename(f)[3:-4]
        vm[uid]=[(re.sub(r'<[^>]*>','',t),v) for t,v in msgs(f)]
    json.dump(vm,open(D+'/vmap2.json','w',encoding='utf-8'),ensure_ascii=False)
    tot=sum(len(x) for x in vm.values()); wv=sum(1 for x in vm.values() for t,v in x if v)
    ok=sum(1 for x in vm.values() for t,v in x if v and v['cue'] and v['name'].endswith(v['cue']))
    print('msgs',tot,'voiced',wv,'name/cue consistent',ok)
    sys.exit()
vm=json.load(open(D+'/vmap2.json',encoding='utf-8'))
def card_voice(c):
    s=re.sub(r'<[^>]*>','',c['sentence']).strip()
    for t,v in vm.get(c.get('uid',''),[]):
        if s and s in t: return t,v
    return None,None
if sys.argv[1]=='cov':
    per={}
    for f in glob.glob('data/cards_ch*_*.json'):
        ch=int(re.search(r'ch(\d+)',f).group(1)); n=h=found=0
        for c in json.load(open(f,encoding='utf-8')):
            n+=1; t,v=card_voice(c); found+=t is not None; h+=bool(v and v['cue'])
        per[ch]=(n,found,h)
    for ch in sorted(per): print(ch,per[ch])
    print('total',[sum(x[i] for x in per.values()) for i in range(3)])
if sys.argv[1]=='decode':
    ch=int(sys.argv[2]); G="C:/Program Files (x86)/Steam/steamapps/common/Yakuza 0/media/data/soundcpk/se.cpk"
    _,idx=index(G); f=open(G,'rb'); out=D+f'/v2_ch{ch}'; os.makedirs(out,exist_ok=True); done=set(); rows=[]
    for c in json.load(open(f'data/cards_ch{ch}_{ch}.json',encoding='utf-8')):
        t,v=card_voice(c)
        if not (v and v['cue']): continue
        a=v['acb']
        if a not in done:
            o,sz=idx[int(a,16)]; f.seek(o); wd=out+'/'+a; os.makedirs(wd,exist_ok=True)
            open(wd+f'/{a}.awb','wb').write(f.read(sz)); shutil.copy(D+f'/soundpar/{a}.acb',wd)
            subprocess.run([R+'/tools/vgmstream/vgmstream-cli.exe','-S','0','-o','?n.wav',f'{a}.awb'],cwd=wd,capture_output=True); done.add(a)
        w=out+f'/{a}/{v["cue"]}.wav'
        dur=(lambda W:W.getnframes()/W.getframerate())(wave.open(w)) if os.path.exists(w) else None
        rows.append(dict(order=c['order'],chars=len(re.sub(r'[　…！？、。!?\s（）\r\n]','',t)),dur=dur,v=v,wav=w,msg=t,s=re.sub(r'<[^>]*>','',c['sentence'])))
    json.dump(rows,open(out+'/rows.json','w',encoding='utf-8'),ensure_ascii=False,indent=0)
    ok=[r for r in rows if r['dur']]; print('rows',len(rows),'decoded',len(ok))
    cps=sorted(r['chars']/r['dur'] for r in ok); print('chars/sec p10/50/90',[round(cps[int(len(cps)*q)],1) for q in (.1,.5,.9)])
    n=len(ok); xs=[r['chars'] for r in ok]; ys=[r['dur'] for r in ok]; mx,my=sum(xs)/n,sum(ys)/n
    print('corr',round(sum((x-mx)*(y-my) for x,y in zip(xs,ys))/(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))**.5,3))
    full=sum(1 for r in ok if r['chars']/r['dur']<12); print('likely full-line (<12 chars/s)',full,'of',n)
    for r in ok[:15]: print(r['order'],r['chars'],round(r['dur'],1),r['v']['name'],r['msg'].replace('\r\n','/')[:44])
