import json,collections,sys,bisect
# 各档伴奏: 拍->和弦音数(0=仅根音,-1=根音,-2=根+五度)
PLANS={0:{0:1,2:0},1:{0:2,2:1},2:{0:3,1:-1,2:3,3:-1}}
OFFBEAT_LV=9
GAP=4
VOCAL_MOFF=0; MASTER_TRACK=0   # 借人声时人声谱需后移的小节数；伴奏谱取速度用的轨
FAITHFUL_NOBASS=False   # 如实模式不带贝斯(只要钢琴等)
VOCAL_O=None   # 强制主唱整体八度偏移(不让程序自动选)
VOCAL_SID=None   # 人声从另一份 Songsterr 谱借(小节须一一对应)
VOCAL_FILL_GAP=False   # VOCAL_ACCENT 段里，连续5个十六分后空一格的，补上第6个(不换气)
LEAD_MEAS={}   # {主奏轨号:(起小节,止小节)} 限定某条主奏只在这些小节补旋律(如贝斯 solo)
DRUM_SID=None; DRUM_MOFF=0   # 从另一份 Songsterr 谱借鼓(如 OS 来源的歌)，及小节偏移
GROOVE_THICK=0   # 鼓律动加厚: 中/满档时军鼓镲和弦多加N个音、底鼓加五度
SAMEKEY_MIN=0.07   # 同一个键两次按下的最短间隔(秒)，用户实测约 70ms
ARPEGGIO=False   # 全曲用八分音符分解和弦(钢琴式)伴奏
DRUM_GROOVE=False   # 普通小节的伴奏也跟鼓: 底鼓=根音, 军鼓=和弦, 镲=满和弦
FAITHFUL_PLUS=False   # 如实照搬之外再叠加按拍子的和弦(更厚)
DBG_ACC=False
VOCAL_ACCENT=[]   # [(起小节,止小节)] 这些小节只放主唱(含和声声部)，不加任何伴奏
DRUMFILL=False   # 把鼓的长串加花(>=4连打)和鼓独奏弹成音
FAITHFUL=[]   # 节奏吉他等轨道号: 伴奏如实照搬这些轨+贝斯的节奏和音高(不套固定格子)
DRUM=None   # 鼓轨号: 设了就让齐奏重音/停顿/底鼓连打处的伴奏跟鼓走
VOCAL_OCT=[]   # [(起小节,止小节,八度偏移)] 分段升降旋律八度
MELFLOOR_FIX=False
OS_BPM=None; OS_OFFSET=0; VOCAL_TOP=False
KEYSEG=[]   # [(起始小节, 移调)] 转调用
REPEAT_MIN=0; REPEAT_LV=(0,)   # 同音精简：会删主唱的音，用户明确不要，别开
TOPWIN=1.0   # 伴奏避让旋律的时间窗(拍)
SKYLINE=99   # 主奏每拍只保留距最高音N半音以内的音
SUSTAIN_COVERS=True   # False: 人声长音拖着的拍也允许主奏进来
from ssparse import load
MAJOR=[0,2,4,5,7,9,11]
def white(p): return p if p%12 in MAJOR else p-1
def key_of(p): return (p//12-5)*7+MAJOR.index(p%12)
CRASH={49,52,55,57}; KICK={35,36}; SNARE={37,38,40}
def drum_hits(sid):
    """鼓轨 → {小节: [(拍内位置, {鼓号})]}；Songsterr 或 OS(DRUM=乐器号, GM 鼓号)"""
    if isinstance(sid,str) and sid[:3] in ('os:','mid') and not DRUM_SID and sid.startswith('os:'):
        from os_parse import load as osl
        _s,_n=osl(f'os/{sid[3:]}.bin'); res=collections.defaultdict(lambda: collections.defaultdict(set))
        for t,p,l,i,v in _n:
            if i==DRUM and t>=OS_OFFSET:
                tt=t-OS_OFFSET; res[int(tt//16)+DRUM_MOFF][round((tt%16)/4,4)].add(int(p))
        return {m:sorted(h.items()) for m,h in res.items()}
    from fractions import Fraction as F
    d=json.load(open(f'ss_{DRUM_SID or sid}/{DRUM}.json')); res={}
    for mi,m in enumerate(d['measures']):
        hits=collections.defaultdict(set)
        for v in m['voices']:
            pos=F(0)
            for bt in v['beats']:
                if not bt.get('rest'):
                    for n in bt['notes']:
                        if 'fret' in n: hits[float(pos*4)].add(n['fret'])
                pos+=F(*bt['duration'])
        if hits: res[mi+DRUM_MOFF]=sorted(hits.items())
    return res
def drum_patterns(sid):
    """{小节: (类型, [拍内位置])}；只标出齐奏重音(kime)/停顿(stop)/底鼓连打(roll)"""
    res={}
    for mi,hs in drum_hits(sid).items():
        hits=dict(hs)
        if not hits: continue
        crash=[p for p,h in hits.items() if h&CRASH]; kick=[p for p,h in hits.items() if h&KICK]; snare=[p for p,h in hits.items() if h&SNARE]
        if len(crash)>=3 and any(p%1 for p in crash) and len(hits)<=8: res[mi]=('kime',sorted(crash))
        elif len(hits)<=3: res[mi]=('stop',sorted(hits))
        elif len(kick)>=8 and len(snare)<=1: res[mi]=('roll',sorted(set(round(p*2)/2 for p in kick)))
    # 连续 3 小节以上的"连打"是双踩律动而不是加花，去掉
    rolls=sorted(m for m,v in res.items() if v[0]=='roll'); run=[]
    for m in rolls+[None]:
        if m is not None and run and m==run[-1]+1: run.append(m); continue
        if len(run)>=3:
            for x in run: del res[x]
        run=[m] if m is not None else []
    return res
def arrange(sid, vocal, leads, bass, name, dst, ref, harm=(), level=lambda m:1):
    if isinstance(sid,str) and sid.startswith('mid:'):   # 本地 MIDI 文件 mid/<名>.mid，轨道号=MIDI track 序号
        from midload import load_mid
        P=f"mid/{sid[4:]}.mid"; get=lambda t: load_mid(P,t)
    elif isinstance(sid,str) and sid.startswith('os:'):   # Online Sequencer: 轨道号=乐器号(可为列表)
        from osload import load_os
        P=f"os/{sid[3:]}.bin"; get=lambda t: load_os(P,t,OS_BPM,OS_OFFSET)
    else:
        S=f'ss_{sid}/'; T=f'ss_{VOCAL_SID or sid}/{vocal}.json'; get=lambda t: load(S+f'{t}.json',T)
    if VOCAL_SID and not str(sid).startswith('os:'):
        if VOCAL_MOFF:   # 人声谱和伴奏谱差 N 小节：以伴奏谱的小节为准，人声整体后移
            T2=S+f'{MASTER_TRACK}.json'; _,_,_,ms=load(T2,T2)
            _,voc0,_,_=load(T,T)
            mst0={m:(st_,b_) for m,st_,b_ in ms}
            voc=[]
            for s0,p,l,m0 in voc0:
                m1=m0+VOCAL_MOFF
                if m1 in mst0: voc.append((s0+sum(4*60/mst0[k][1] for k in range(VOCAL_MOFF)),p,l,m1))
            T=T2; get=lambda t: load(S+f'{t}.json',T)
        else:
            _,voc,_,ms=load(T,T)
    else:
        _,voc,_,ms=get(vocal)
    voc_raw=list(voc)
    if VOCAL_TOP:   # 人声轨有和声/八度时只留最高音
        top={}
        for x in voc: top[round(x[0],3)]=max(top.get(round(x[0],3),x),x,key=lambda y:y[1])
        voc=sorted(top.values())
    L=[get(t)[1] for t in leads]; _,bs,_,_=get(bass)
    mst={mi:(st,b) for mi,st,b in ms}
    def q(s,mi,div=4):   # 量化到本小节速度的 1/div 拍
        st,b=mst[mi]; u=60/b/div; return st+round((s-st)/u)*u
    # 1) 调：让最多的音落在白键上
    cnt=collections.Counter(p%12 for n in [voc,bs]+L for _,p,_,_ in n)
    SH=max(range(-6,6),key=lambda sh:(sum(c for pc,c in cnt.items() if (pc+sh)%12 in MAJOR),-abs(sh)))
    def shf(mi):   # 分段移调(转调)
        r=SH
        for m0,sh in KEYSEG:
            if mi>=m0: r=sh
        return r
    vp=[p+shf(m) for _,p,_,m in voc]
    O=max(range(-36,37,12),key=lambda o:(sum(62<=p+o<=84 for p in vp),-sum(p+o<60 or p+o>84 for p in vp)))
    if VOCAL_O is not None: O=VOCAL_O
    # 2) 人声覆盖的拍（有音在响的拍不补乐器）
    def beat_id(s,mi): st,b=mst[mi]; return (mi,int((s-st)/(60/b)+1e-6))
    covered=set()
    for s,p,l,mi in voc:
        st,b=mst[mi]; bl=60/b; k=0
        while s+k*bl < s+(max(l,bl*0.99) if SUSTAIN_COVERS else bl*0.99)-1e-6:
            t=s+k*bl; m2=max(m for m in mst if mst[m][0]<=t+1e-6); covered.add(beat_id(t,m2)); k+=1
    # 只在连续空 >=4 拍的地方用乐器补旋律，短换气不补
    allb=[(mi,k) for mi,st,b in ms for k in range(4)]
    run=[];blocked=set(covered)
    for bid in allb+[None]:
        if bid is not None and bid not in covered: run.append(bid); continue
        if len(run)<GAP: blocked|=set(run)
        run=[]
    covered=blocked
    rh=collections.defaultdict(set); src=collections.Counter()
    prev=None
    for s,p,l,mi in voc:
        if REPEAT_MIN and prev and prev[1]==p and s-prev[0] < REPEAT_MIN*60/mst[mi][1]-1e-6 and level(mi) in REPEAT_LV: continue
        prev=(s,p)
        p=white(p+shf(mi)+O+sum(o for a,b,o in VOCAL_OCT if a<=mi<=b))
        while p<60:p+=12
        while p>84:p-=12
        rh[round(q(s,mi),4)].add(p); src['vocal']+=1
    filled=set()
    for ti,n in enumerate(L):
        by=collections.defaultdict(list)
        rng_=LEAD_MEAS.get(leads[ti])
        for s,p,l,mi in n:
            if rng_ and not (rng_[0]<=mi<=rng_[1]): continue
            bid=beat_id(s,mi)
            if bid in covered or (bid in filled and ti>0 and bid not in by_owner.get(ti,set())): continue
            by[(round(q(s,mi),4),bid)].append(p)
        own=set(b for _,b in by); by_owner={ti:own}
        # 天际线：每拍只留靠近该拍最高音的音(去掉低音持续音)
        bmax=collections.defaultdict(int)
        for (t,bid),ps in by.items(): bmax[bid]=max(bmax[bid],max(ps))
        by={k:ps for k,ps in by.items() if max(ps)>=bmax[k[1]]-SKYLINE}
        mtop=collections.defaultdict(list)
        for (t,bid),ps in by.items(): mtop[bid[0]].append(max(ps)+shf(bid[0])+O)
        octs=(-24,-12,0,12,24,36) if leads[ti] in LEAD_MEAS else (-24,-12,0,12)
        moct={m:max(octs,key=lambda o:(sum(64<=p+o<=79 for p in v),-abs(o))) for m,v in mtop.items()}
        for (t,bid),ps in by.items():
            if bid in filled: continue
            p=max(ps)+shf(bid[0])+O+moct[bid[0]]
            while p>81:p-=12
            while p<60:p+=12
            rh[t].add(white(p)); src[f'lead{leads[ti]}']+=1
        filled|=own
    # 3) 伴奏：贝斯根音 + 和弦(从和声轨统计) + 慢板分解
    H=[get(t)[1] for t in harm]
    evs=[(s0,s0+max(l,0.05),p) for n in H+[bs] for s0,p,l,_ in n]
    evs.sort()
    bass_at=sorted((q(s0,mi,2),p) for s0,p,l,mi in bs)
    out=collections.defaultdict(set)
    for t,ps in rh.items(): out[t]|={key_of(p) for p in ps}
    mel=sorted((t,min(key_of(p) for p in ps)) for t,ps in rh.items())
    import bisect
    mt=[x[0] for x in mel]
    def mel_floor(t0,t1):   # 这段时间内(含正在响的前一音)旋律最低键
        i=max(bisect.bisect_right(mt,t0)-1,0); j=bisect.bisect_right(mt,t1)
        if MELFLOOR_FIX:   # 只看窗口内的音 + 1.5 秒内的前一个音(修正:前奏被后面的旋律挡住)
            ks=[mel[k][1] for k in range(i,j) if mel[k][0]>=t0-1.5]
        else:
            ks=[mel[k][1] for k in range(i,max(j,i+1))] if mel else []
        return min(ks) if ks else 15
    i=0; last=None; ev_i=0; acc_n=0
    drum=drum_patterns(sid) if DRUM is not None else {}
    dgroove=drum_hits(sid) if (DRUM is not None and DRUM_GROOVE) else {}
    bat=[x[0] for x in bass_at]
    def chord_at(t,mi,bl,win):
        """返回 (bassk, pool, rpc, others)；无和声返回 None"""
        j_=bisect.bisect_right(bat,t+1e-6)-1; last=bass_at[j_] if j_>=0 else None
        if last is None or t-last[0]>4*bl:
            lows=[p for s0,e0,p in evs if s0<t+win and e0>t]
            if not lows: return None
            r=white(min(lows)+shf(mi))
        else: r=white(last[1]+shf(mi))
        while r<60:r+=12
        while r>71:r-=12
        w=collections.Counter()
        for s0,e0,p in evs:
            if s0>t+win: break
            if e0>t and s0<t+win: w[white(p+shf(mi))%12]+=min(e0,t+win)-max(s0,t)
        rpc=r%12; ch=[pc for pc,_ in w.most_common() if pc!=rpc][:3]
        ch=sorted(ch,key=lambda pc:(0 if (pc-rpc)%12 in (3,4) else 1 if (pc-rpc)%12==7 else 2))[:2]
        if not ch: ch=[white(r+7)%12]
        top=mel_floor(t-0.05,t+win*TOPWIN)
        pcs={rpc}|set(ch)
        pool=[k for k in range(0,15) if k<top-1 and [0,2,4,5,7,9,11][k%7]%12 in pcs]
        low=[k for k in pool if [0,2,4,5,7,9,11][k%7]==rpc]
        bassk=low[0] if low else (pool[0] if pool else None)
        if bassk is None: return None
        others=[k for k in pool if [0,2,4,5,7,9,11][k%7]!=rpc]
        return bassk,pool,rpc,others
    def ch_n(c,n):
        bassk,pool,rpc,others=c
        return sorted(set([bassk]+others[-n:])) if n else [bassk]
    faith=collections.defaultdict(lambda: collections.defaultdict(list))   # 小节 -> 时刻 -> [(音高,是否贝斯)]
    if FAITHFUL:
        for t_ in FAITHFUL:
            for s0,p,l,m0 in get(t_)[1]: faith[m0][round(q(s0,m0),4)].append((p,False))
        if not FAITHFUL_NOBASS:
            for s0,p,l,m0 in bs: faith[m0][round(q(s0,m0),4)].append((p,True))
    def fold_under(p,top):
        """把音高折进 [C4, 旋律下方两键) 内，尽量靠上；放不下返回 None"""
        p=white(p)
        while p<60: p+=12
        while p>=60+12 and key_of(p)>=top-1: p-=12
        return key_of(p) if key_of(p)<top-1 else None
    # 跟主唱分组的段落: 伴奏只在每组起音(前面有空拍的主唱音)砸和弦
    accent_meas={m for a,b_,in_ in [(a,b_,0) for a,b_ in VOCAL_ACCENT] for m in range(a,b_+1)}
    if accent_meas:
        vt=sorted({round(q(s0,m0),4) for s0,p,l,m0 in voc if m0 in accent_meas})
        for mi_ in sorted(accent_meas):
            st_,b_=mst[mi_]; bl_=60/b_; u=bl_/4
            for k,t in enumerate(vt):
                if not (st_-1e-3<=t<st_+4*bl_-1e-3): continue
                if k>0 and t-vt[k-1]<u*1.5: continue       # 不是组首
                pass
        # 不换气段：主唱每组之间空一格的地方补一个同组音(扒谱漏记)
        if VOCAL_FILL_GAP:
            vv=sorted({round(q(s0,m0),4) for s0,p,l,m0 in voc_raw if m0 in accent_meas})
            fills=[]
            for k in range(len(vv)-1):
                mi_=max(m for m in mst if mst[m][0]<=vv[k]+1e-3); u=60/mst[mi_][1]/4
                if vv[k+1]-vv[k]>=2*u-u*0.2 and k>=4 and all(abs(vv[k-j]-vv[k-j-1]-u)<u*0.2 for j in range(4)):
                    fills.append((vv[k],round(vv[k]+u,4)))
            _fill_src=dict(fills)
        # 只放主唱：把主唱轨在这些小节的全部声部(含三度和声)放进来
        for s0,p,l,m0 in voc_raw:
            if m0 in accent_meas:
                pp=white(p+shf(m0)+O+sum(o for a,b2,o in VOCAL_OCT if a<=m0<=b2))
                while pp<60: pp+=12
                while pp>84: pp-=12
                out[round(q(s0,m0),4)].add(key_of(pp))
        if VOCAL_FILL_GAP:
            for a_,b_ in _fill_src.items(): out[b_]|=set(out[a_])
    for mi,st,b in ms:
        bl=60/b
        if mi in accent_meas: continue
        if mi in faith:   # 如实照搬节奏吉他+贝斯
            for t,ps in sorted(faith[mi].items()):
                top=mel_floor(t-0.05,t+bl*0.5); sh=shf(mi)
                gk=sorted({k for p,isb in ps if not isb for k in [fold_under(p+sh,top)] if k is not None})
                bk=[k for p,isb in ps if isb for k in [fold_under(p+sh,min(top,8))] if k is not None]
                ks=set(gk[-3:])|set(bk[:1])
                if ks: out[t]|=ks; acc_n+=len(ks)
            if not FAITHFUL_PLUS: continue
        dp=drum.get(mi)
        if dp:   # 跟鼓走: 齐奏重音/停顿/底鼓连打
            kind,hits=dp
            for pos in hits:
                t=st+pos*bl
                c=chord_at(t,mi,bl,bl*0.5)
                if not c: continue
                ks=ch_n(c,3) if kind=='kime' else ch_n(c,2) if kind=='stop' else ([c[0]] if pos>0 else ch_n(c,2))
                out[round(t,4)]|=set(ks); acc_n+=len(ks)
            continue
        if DRUM_GROOVE and DRUM is not None and mi in dgroove:   # 伴奏节奏=鼓的节奏
            lv=level(mi); last8=None
            for pos,h in dgroove[mi]:
                t=st+pos*bl
                ks=set()
                crash=h&{49,52,55,57}; snare=h&{37,38,40}; kick=h&{35,36}
                if not (crash or snare or kick): continue
                c=chord_at(t,mi,bl,bl*0.5)
                if not c: continue
                g=GROOVE_THICK if lv>=1 else 0
                if crash: ks|=set(ch_n(c,(3 if lv>=1 else 2)+g))
                if snare: ks|=set(ch_n(c,(2 if lv>=1 else 1)+g))
                if kick:
                    # 快速连踩(间隔<=八分之一拍*2)在根音/五度/八度之间换键，避开单键连按上限
                    bassk,pool_,rpc_,others_=c
                    alts=[bassk]+[k for k in pool_ if k>bassk and ([0,2,4,5,7,9,11][k%7]-rpc_)%12 in (7,0)][:2]
                    fast = last8 is not None and pos-last8[0] <= 0.26
                    idx = (last8[1]+1)%len(alts) if fast else 0
                    ks.add(alts[idx]); last8=(pos,idx)
                    if GROOVE_THICK and lv>=1 and not fast:   # 加厚: 底鼓再加五度
                        f5=[k for k in pool_ if k>alts[idx] and ([0,2,4,5,7,9,11][k%7]-rpc_)%12==7][:1]
                        ks|=set(f5)
                if ks: out[round(t,4)]|=ks; acc_n+=len(ks)
            continue
        for bt in range(4):
            t=st+bt*bl
            c=chord_at(t,mi,bl,bl)
            if not c: continue
            bassk,pool,rpc,others=c
            lv=level(mi)
            if b<100 or ARPEGGIO:   # 慢板/钢琴式分解
                seq=ch_n(c,3); seq=seq if len(seq)>1 else seq*2
                steps=[0,1] if (lv>=1 or ARPEGGIO) else [0]
                for h in steps:
                    tt=round(t+h*bl/2,4); out[tt].add(seq[(bt*len(steps)+h)%len(seq)]); acc_n+=1
            if not (b<100) or ARPEGGIO:
                plan=PLANS[lv]
                if bt in plan:
                    ks=ch_n(c,plan[bt]) if plan[bt]>=0 else [bassk]
                    if plan[bt]==-2: ks=[bassk]+[k for k in pool if k>bassk and ([0,2,4,5,7,9,11][k%7]-rpc)%12==7][:1]
                    out[round(t,4)]|=set(ks); acc_n+=len(ks)
                if lv>=OFFBEAT_LV: out[round(t+bl/2,4)].add(bassk); acc_n+=1
    if DRUMFILL and DRUM is not None:
        TOMS=[50,48,47,45,43,41]; lastc=None; nfill=0
        for mi,st,b in ms:
            hs=drum_hits(sid).get(mi,[])
            if not hs: continue
            bl=60/b
            pitched=len({t for t in out if st-1e-6<=t<st+4*bl-1e-6})
            mark=set()
            if pitched<4:   # 其他乐器几乎停了：整小节鼓都弹出来
                mark={k for k,(p,h) in enumerate(hs) if h-{42,44,46,51,53,59}}
            run=[]
            for k,(p,h) in enumerate(hs+[(1e9,set())]):
                if h&({38,37,40}|set(TOMS)) and (not run or p-hs[run[-1]][0]<=0.26): run.append(k); continue
                if len(run)>=4: mark|=set(run)
                run=[k] if h&({38,37,40}|set(TOMS)) else []
            runpos={}; cnt_=0
            for k in sorted(mark):
                cnt_ = cnt_+1 if k-1 in mark else 0; runpos[k]=cnt_
            for k in sorted(mark):
                p,h=hs[k]; t=st+p*bl
                # 和旋律撞上(同时起音)就不要
                jm=bisect.bisect_left(mt,t-bl*0.125)
                if jm<len(mt) and mt[jm]<=t+bl*0.125: continue
                c=chord_at(t,mi,bl,bl*0.5) or lastc
                if not c: continue
                lastc=c; bassk,pool,rpc,others=c
                tones=sorted(set(pool)) or [bassk]
                ks=set()
                if h&{36,35}: ks.add(bassk)
                if h&{38,37,40}:   # 连打里的军鼓沿和弦音往上走
                    ks.add(tones[(len(tones)//2 + runpos.get(k,0)) % len(tones)])
                for tm in TOMS:
                    if tm in h: ks.add(tones[(len(tones)-1-TOMS.index(tm)*len(tones)//len(TOMS) - runpos.get(k,0)) % len(tones)])
                if h&{49,52,55,57}: ks|=set(ch_n(c,3))
                mtop=mel_floor(t-bl*0.5,t)            # 正在响的旋律音：加花只能在它下面
                ks={x for x in ks if x<mtop-1}
                if ks: out[round(t,4)]|=ks; nfill+=1
        src['鼓加花']=nfill
    # 同键最短间隔：伴奏音若离上次按同一个键不足 SAMEKEY_MIN 秒，挪到八度同名键；挪不开就去掉。主唱不动
    if SAMEKEY_MIN:
        melk={}
        for s0,p,l,m0 in voc:
            tq=round(q(s0,m0),4); pp=white(p+shf(m0)+O+sum(o for a,b2,o in VOCAL_OCT if a<=m0<=b2))
            while pp<60: pp+=12
            while pp>84: pp-=12
            melk.setdefault(tq,set()).add(key_of(pp))
        lastp={}; moved=dropped=0
        for t in sorted(out):
            mk=melk.get(t,set()); top_=min(mk) if mk else 15
            new=set(mk)
            for k in sorted(out[t]-mk):
                if t-lastp.get(k,-9)>=SAMEKEY_MIN-1e-6 and k not in new: new.add(k); continue
                alt=[a for a in (k-7,k+7,k-14,k+14) if 0<=a<=14 and (a<top_ or not mk) and a not in new and t-lastp.get(a,-9)>=SAMEKEY_MIN-1e-6]
                if alt: new.add(alt[0]); moved+=1
                else: dropped+=1
            out[t]=new
            for k in new: lastp[k]=t
        src['同键挪八度']=moved; src['同键去掉']=dropped
    ts=sorted(t for t in out if out[t]); t0=ts[0]
    refd=json.loads(open(ref,encoding='utf-16').read())[0]
    song=dict(refd); main_bpm=collections.Counter(b for _,_,b in ms).most_common(1)[0][0]
    song.update(name=name,author='Ave Mujica',transcribedBy='Claude',bpm=main_bpm*4,
        songNotes=[{"time":round((t-t0)*1000)+450,"key":f"1Key{k}"} for t in ts for k in sorted(out[t])])
    open(dst,'w',encoding='utf-16').write(json.dumps([song],ensure_ascii=False,separators=(',',':'))+'\n')
    ns=song['songNotes']; ks=collections.Counter(n['key'] for n in ns)
    print(f'{dst}\n  移调{SH:+d} 旋律八度{O:+d}  {len(ns)}音  {ns[-1]["time"]/1000:.0f}s  来源{dict(src)}  最多同按{max(len(v) for v in out.values())}')
    return out
