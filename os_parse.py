import struct,collections,sys
def varint(b,i):
    v=s=0
    while True:
        x=b[i];i+=1;v|=(x&0x7f)<<s;s+=7
        if x<0x80:return v,i
def msg(b):
    i=0;out=[]
    while i<len(b):
        k,i=varint(b,i);f,w=k>>3,k&7
        if w==0:v,i=varint(b,i)
        elif w==5:v=struct.unpack('<f',b[i:i+4])[0];i+=4
        elif w==1:v=struct.unpack('<d',b[i:i+8])[0];i+=8
        elif w==2:l,i=varint(b,i);v=b[i:i+l];i+=l
        out.append((f,v))
    return out
def load(p):
    top=msg(open(p,'rb').read());settings={};notes=[]
    for f,v in top:
        if f==1: settings=dict(msg(v))
        elif f==2:
            d=dict(msg(v));notes.append((d.get(2,0.0),d.get(1,0),d.get(3,1.0),d.get(4,0),d.get(5,1.0)))
    return settings,notes
if __name__=='__main__':
    s,n=load(sys.argv[1]);print(s,len(n))
    print('instruments',collections.Counter(x[3] for x in n))
    print('pitch range',min(x[1] for x in n),max(x[1] for x in n),'len',max(x[0] for x in n))
    for ins in sorted(set(x[3] for x in n)):
        ps=[x[1] for x in n if x[3]==ins];print(ins,len(ps),min(ps),max(ps),sum(ps)/len(ps))
