"""MIDI 文件 → 与 ssparse.load 相同格式 [(start_s, pitch, dur_s, measure)]；轨道号=MIDI track 序号；按 4/4 分小节"""
import struct, bisect
def _read(path):
    data=open(path,'rb').read(); assert data[:4]==b'MThd'
    _,ntrk,div=struct.unpack('>HHH',data[8:14]); pos=14; tracks=[]; tempos=[]
    for ti in range(ntrk):
        ln=struct.unpack('>I',data[pos+4:pos+8])[0]; p,end=pos+8,pos+8+ln; pos=end; tick=0; st=0; on={}; notes=[]
        def vlq():
            nonlocal p
            v=0
            while True:
                b=data[p]; p+=1; v=(v<<7)|(b&0x7f)
                if not b&0x80: return v
        while p<end:
            tick+=vlq(); b=data[p]
            if b&0x80: st=b; p+=1
            if st==0xFF:
                t=data[p]; p+=1; l=vlq()
                if t==0x51: tempos.append((tick,int.from_bytes(data[p:p+3],'big')))
                p+=l
            elif st in (0xF0,0xF7): p+=vlq()
            else:
                hi=st&0xF0
                if hi in (0xC0,0xD0): p+=1; continue
                a,v=data[p],data[p+1]; p+=2
                if hi==0x90 and v>0: on[(a,st&15)]=tick
                elif hi in (0x80,0x90):
                    t0=on.pop((a,st&15),None)
                    if t0 is not None: notes.append((t0,a,tick-t0))
        tracks.append(sorted(notes))
    tempos=sorted(tempos) or [(0,500000)]
    if tempos[0][0]>0: tempos=[(0,500000)]+tempos
    # 同一 tick 多个 tempo 取最后一个
    tm={}
    for t,u in tempos: tm[t]=u
    return tracks,sorted(tm.items()),div
def load_mid(path, track, offset_beats=0):
    tracks,tempos,div=_read(path)
    ticks=[t for t,_ in tempos]; acc=[0.0]
    for i in range(1,len(tempos)): acc.append(acc[-1]+(tempos[i][0]-tempos[i-1][0])*tempos[i-1][1]/div/1e6)
    def sec(tk):
        i=bisect.bisect_right(ticks,tk)-1; return acc[i]+(tk-tempos[i][0])*tempos[i][1]/div/1e6
    bar=4*div; o=int(offset_beats*div)
    trs=track if isinstance(track,(list,tuple)) else [track]
    notes=sorted((sec(t),p,max(sec(t+d)-sec(t),0.05),int((t-o)//bar)) for tr in trs for t,p,d in tracks[tr] if t>=o)
    notes=[(s-sec(o),p,l,m) for s,p,l,m in notes]
    last=max((t+d for tr in tracks for t,p,d in tr),default=0); nm=int((last-o)//bar)+2
    ms=[]
    for m in range(nm):
        tk=o+m*bar; i=bisect.bisect_right(ticks,tk)-1
        ms.append((m, sec(tk)-sec(o), round(60e6/tempos[i][1],3)))
    return {'name':str(track),'tuning':[]}, notes, [], ms
