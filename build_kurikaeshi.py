"""繰り返し一粒：Songsterr/OS 都没有。旋律用 Sky1984 谱库里 DB 扒的单音光遇谱(全曲)，
和弦用 U-FRET(Dm 调，结尾升半音那段按同级数处理)，合成 mid/kurikaeshi.mid：
track0=主唱(DB 旋律) track1=贝斯根音 track2=和弦。之后 python3 make.py kurikaeshi"""
import json,struct,sys
SRC='sky1984/缲り返し一粒.txt'
MAJOR=[0,2,4,5,7,9,11]
b=open(SRC,'rb').read()
for enc in ('utf-8-sig','utf-16'):
    try: d=json.loads(b.decode(enc)); break
    except Exception: pass
d=d[0] if isinstance(d,list) else d
cols=[[k for k,_ in ns] for _,ns in d['columns']]
assert not cols[72*16], '第72小节首格应为空'
del cols[72*16]   # DB 从第72小节起整体错后一格
BPM=d['bpm']/4    # 每格=十六分音符
# 副歌第3-4小节旋律(B♭ C D | G F F)不贴 U-FRET 的 Dm Am，按旋律改为 B♭ | Dm C
# 和弦(Dm 调名) → 写进 MIDI 用 C 大调级数(Dm=vi→Am …)
CH={'Dm':(57,[57,60,64]),'Am':(52,[52,55,59]),'Bb':(53,[53,57,60]),'F':(48,[48,52,55]),
    'C':(55,[55,59,62]),'Gm':(50,[50,53,57,64]),'A7':(52,[52,59,62])}
A =[['Dm','Am'],['Bb','F']]*3+[['Dm','Am'],['Bb','C']]
A2=[['Dm','Dm'],['Bb','Bb']]+[['Dm','Am'],['Bb','F']]*2+[['Dm','Am'],['Bb','C']]
V =([['Dm','Am'],['Bb','F']]*3+[['Dm','Am'],['Bb','C']])*2
V2=[['Dm','Am'],['Bb','F']]*3+[['Dm','Am'],['Bb','C']]
B =[['Gm','Gm'],['A7','A7'],['Dm','Dm'],['F','F'],['Gm','Gm'],['A7','A7'],['Gm','A7'],['Bb','C']]
S =[['Dm','Am'],['Bb','F'],['Bb','Bb'],['Dm','C'],['Dm','Am'],['Bb','F'],['Dm','Am'],['Bb','F']]
S3=[['Dm','Am'],['Bb','F'],['Bb','Bb'],['Dm','C'],['Dm','Am'],['Bb','F'],['Dm','Am'],['Bb','Bb']]
I =[['Dm','Am'],['Bb','F'],['Dm','Am'],['Bb','C']]
BR=[['Dm','Am'],['Bb','F']]*3+[['Dm','Am'],['Bb','Bb']]
BARS=A+V+B+S+A2+V2+B+S+I+BR+S3+S+A+A+[['Dm','Dm']]
nb=(len(cols)+15)//16
assert len(BARS)==nb, (len(BARS),nb)
# 旋律：Sky 键 k → C 大调 MIDI(键0=C4)，时值=到下一个音(最多一拍)
on=[(i,k) for i,c in enumerate(cols) for k in c]
starts=sorted({i for i,_ in on})
nxt={a:b for a,b in zip(starts,starts[1:]+[len(cols)])}
voc=[(i*120,60+MAJOR[k%7]+12*(k//7),min(nxt[i]-i,4)*120) for i,k in on]
bass=[];harm=[]
for m,(c1,c2) in enumerate(BARS):
    for h,c in enumerate((c1,c2)):
        t=(m*16+h*8)*120; r,ns=CH[c]
        bass.append((t,r-12,960)); harm+=[(t,p,960) for p in ns]
if '--check' in sys.argv:   # 每小节旋律落在和弦音上的比例
    for m,(c1,c2) in enumerate(BARS):
        hit=tot=0
        for i,k in on:
            if i//16!=m: continue
            pc=(MAJOR[k%7])%12; ns={p%12 for p in CH[(c1,c2)[(i%16)//8]][1]}
            tot+=1; hit+=pc in ns
        if tot: print(f'{m:3d} {c1:>2}/{c2:<2} {hit}/{tot}', '  <-- 低' if hit/tot<0.4 else '')
def trk(notes):
    ev=sorted([(t,0x90,p,90) for t,p,l in notes]+[(t+l,0x80,p,0) for t,p,l in notes],key=lambda e:(e[0],e[1]==0x90))
    out=b'';last=0
    for t,s,p,v in ev:
        dt=t-last;last=t;vl=[dt&0x7f];dt>>=7
        while dt: vl.insert(0,(dt&0x7f)|0x80);dt>>=7
        out+=bytes(vl)+bytes([s,p,v])
    return b'MTrk'+struct.pack('>I',len(out)+4)+out+b'\x00\xff\x2f\x00'
tempo=b'\x00\xff\x51\x03'+int(60e6/BPM).to_bytes(3,'big')
t0=trk(voc); t0=b'MTrk'+struct.pack('>I',struct.unpack('>I',t0[4:8])[0]+len(tempo))+tempo+t0[8:]
open('mid/kurikaeshi.mid','wb').write(b'MThd'+struct.pack('>IHHH',6,1,3,480)+t0+trk(bass)+trk(harm))
print('mid/kurikaeshi.mid', nb,'小节', len(voc),'旋律音', f'{BPM}bpm')
