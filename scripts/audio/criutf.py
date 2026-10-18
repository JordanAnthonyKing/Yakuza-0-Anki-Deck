import struct
def utf(b):
    assert b[:4]==b'@UTF', b[:4]
    size=struct.unpack('>I',b[4:8])[0]; t=b[8:8+size]
    _,rows_off,str_off,data_off,name_off,ncol,rowlen,nrows=struct.unpack('>HHIIIHHI',t[:24])
    def cstr(o): e=t.index(b'\0',str_off+o); return t[str_off+o:e].decode('utf-8','replace')
    def read(ty,p):
        f={0:'>B',1:'>b',2:'>H',3:'>h',4:'>I',5:'>i',6:'>Q',7:'>q',8:'>f'}
        if ty in f: s=struct.calcsize(f[ty]); return struct.unpack(f[ty],t[p:p+s])[0],s
        if ty==0xA: return cstr(struct.unpack('>I',t[p:p+4])[0]),4
        if ty==0xB: o,l=struct.unpack('>II',t[p:p+8]); return t[data_off+o:data_off+o+l],8
        raise ValueError(ty)
    cols=[];p=24
    for _ in range(ncol):
        fl=t[p]; nm=cstr(struct.unpack('>I',t[p+1:p+5])[0]); p+=5
        st,ty=fl&0xF0,fl&0x0F; const=None
        if st==0x30: const,s=read(ty,p); p+=s
        cols.append((nm,st,ty,const))
    rows=[]
    for r in range(nrows):
        p=rows_off+r*rowlen; row={}
        for nm,st,ty,const in cols:
            if st==0x50: row[nm],s=read(ty,p); p+=s
            elif st==0x30: row[nm]=const
            else: row[nm]=None
        rows.append(row)
    return cols and rows
