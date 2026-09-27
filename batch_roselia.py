"""批量: Songsterr 谱 → 自动识别轨道/段落/转调 → 生成 → 审计"""
import sys,os,json,collections,io,contextlib
sys.path.insert(0,'.')
import ssget, make, arrange
from ssparse import load
MAJOR=[0,2,4,5,7,9,11]
CANDS=[(452756,'FIRE BIRD'),(674485,'Determination Symphony'),(2344853,'軌跡'),(5309010,'陽だまりロードナイト'),
 (3356060,'紫炎'),(3235974,'Sing Alive'),(4570052,'Steadfast Spirits'),(3394086,'“UNIONS” Road'),(6221326,'ZEAL of proud'),
 (5381031,'Talk to My Tone'),(4017195,'Grateful Melting'),(4865565,'熱色スターマイン'),(4974402,'Original Call'),
 (6948261,'Neo-Aspect'),(7036581,'LOUDER'),(6719127,'約束'),(6056973,'Fear Nothing'),(6306327,'Proud of oneself'),
 (4242830,'残酷な天使のテーゼ'),(5158077,'Red fraction'),(3606770,'深愛'),(3902166,'魂のルフラン'),(4532817,'ファタール'),
 (4960113,'This game'),(5743115,'HONEY'),(5775201,'KING'),(7109021,'転生林檎')]
def tracks(sid):
    out=[]; i=0
    while os.path.exists(f'ss_{sid}/{i}.json'):
        out.append((i,json.load(open(f'ss_{sid}/{i}.json')))); i+=1
    return out
def roles(sid):
    tr=tracks(sid); r={'vocal':None,'drum':None,'bass':None,'piano':[],'lead':[],'guitar':[],'other':[]}
    cnt=lambda d: sum(1 for m in d.get('measures',[]) for v in m['voices'] for b in v['beats'] for x in b['notes'] if 'fret' in x)
    vocs=[]
    for i,d in tr:
        ins=d.get('instrument',''); nm=(d.get('name') or '')
        if 'tuning' not in d or 'Drum' in ins:
            if r['drum'] is None and cnt(d)>50: r['drum']=i
            continue
        n=cnt(d)
        if n==0: continue
        if 'ocal' in nm or 'Voice' in ins or ('Sax' in ins and not nm): vocs.append((('ack' in nm.lower() or 'chorus' in nm.lower()), -n, i)); continue
        if 'Bass' in ins and 'Synth' not in ins:
            if r['bass'] is None: r['bass']=i
            continue
        if 'Piano' in ins or 'Keyboard' in nm or 'rinko' in nm.lower() or 'Rinko' in nm or 'Organ' in ins or 'Harpsichord' in ins: r['piano'].append((i,n)); continue
        if 'Guitar' in ins:
            (r['lead'] if ('lead' in nm.lower() or 'solo' in nm.lower()) else r['guitar']).append((i,n)); continue
        r['other'].append((i,n))
    if vocs: r['vocal']=sorted(vocs)[0][2]
    return r
if __name__=='__main__':
    for sid,title in CANDS:
        if not os.path.exists(f'ss_{sid}/0.json'):
            try: ssget.get(sid)
            except Exception as e: print(sid,title,'下载失败',e); continue
        r=roles(sid)
        print(f"{sid} {title:22} 人声{r['vocal']} 鼓{r['drum']} 贝斯{r['bass']} 钢琴{r['piano']} 主奏{r['lead']} 吉他{r['guitar']} 其他{r['other']}")

THICK2={0:{0:2,1:-1,2:2,3:-1},1:{0:2,1:-2,2:2,3:-2},2:{0:3,1:-2,2:3,3:-2}}
SKIP={6056973:'没有人声轨',5743115:'没有贝斯和鼓，吉他也不完整',5775201:'吉他只扒了一小段',4570052:'吉他只扒了一小段'}
def auto_config(sid,title,author='Roselia'):
    r=roles(sid); T=f"ss_{sid}/{r['vocal']}.json"
    _,voc,mk,ms=load(T,T)
    pitched=[r['bass']]+[i for i,_ in r['piano']+r['lead']+r['guitar']+r['other']]
    alln=[]; per={}
    for i in pitched:
        per[i]=load(f'ss_{sid}/{i}.json',T)[1]; alln+=per[i]
    allv=voc+alln
    # 分段转调检测(8 小节窗口)
    def best_sh(notes):
        c=collections.Counter(p%12 for _,p,_,_ in notes); tot=sum(c.values()) or 1
        sc={sh:sum(v for pc,v in c.items() if (pc+sh)%12 in MAJOR)/tot for sh in range(12)}
        return sc
    glob=best_sh(allv)
    vsc=best_sh(voc); vtop=max(vsc.values())
    cands=[sh for sh,v in vsc.items() if v>=vtop-0.01]          # 优先让主唱落在白键上
    # 在全白键候选里挑主唱折叠最少的
    vp=[p for _,p,_,_ in voc]
    def folds(sh):
        best=min(sum(1 for p in vp if not 60<=p+sh+o<=84) for o in range(-48,49,12)); return best
    sh0=min(cands,key=lambda s:(folds(s),s))
    sh0=((sh0+6)%12)-6
    nm=len(ms); keyseg=[(0,sh0)]; cur=sh0; W=8
    wins=[]
    for w in range(0,nm,W):
        seg=[x for x in allv if w<=x[3]<w+W]
        wins.append((w,best_sh(seg) if len(seg)>=40 else None))
    k=0
    while k<len(wins):
        w,sc=wins[k]
        if sc and sc[cur%12]<0.85:
            b=max(sc,key=sc.get)
            # 新调要持续 >=16 小节(2 个窗口)且都 >=0.95、旧调都 <0.85
            run=[x for x in wins[k:k+2] if x[1]]
            if sc[b]>=0.95 and len(run)==2 and all(x[1][b]>=0.95 and x[1][cur%12]<0.85 for x in run):
                cur=((b+6)%12)-6; keyseg.append((w,cur)); k+=2; continue
        k+=1
    # 转调只有在主唱白键比例明显提升(>=3%)时才保留
    if len(keyseg)>1:
        def vfit(ks):
            def f(m):
                r=ks[0][1]
                for a_,b_ in ks:
                    if m>=a_: r=b_
                return r
            return sum(1 for s_,p,l,m in voc if (p+f(m))%12 in MAJOR)/len(voc)
        if vfit(keyseg)-vfit([(0,sh0)])<0.03: keyseg=[(0,sh0)]
    # 段落档位: 伴奏+鼓密度
    acc=collections.Counter(x[3] for i in pitched if i!=r['bass'] for x in per[i])
    dc=collections.Counter()
    if r['drum'] is not None:
        dd=json.load(open(f"ss_{sid}/{r['drum']}.json"))
        for mi,m in enumerate(dd['measures']):
            for v in m['voices']:
                for b in v['beats']:
                    if not b.get('rest'): dc[mi]+=len(b['notes'])
    vals=sorted(acc[m] for m,_,_ in ms if acc[m]); hi=vals[int(len(vals)*0.7)] if vals else 1
    lv=[2 if acc[m]>=hi and dc[m]>=8 else 1 if (acc[m]>=hi*0.4 or dc[m]>=8) else 0 for m,_,_ in ms]
    for i in range(1,len(lv)-1):
        if lv[i-1]==lv[i+1]!=lv[i]: lv[i]=lv[i-1]
    levels=[];a=0
    for i in range(1,len(lv)+1):
        if i==len(lv) or lv[i]!=lv[a]: levels.append((a,i-1 if i<len(lv) else 999,lv[a])); a=i
    piano=max(r['piano'],key=lambda x:x[1])[0] if r['piano'] else None
    leads=[i for i,n in sorted(r['lead'],key=lambda x:-x[1])]+([piano] if piano is not None else [])+[i for i,_ in r['other']]
    harm=[i for i,_ in r['guitar']+r['lead']+r['piano']+r['other']]
    opts=dict(PLANS=THICK2,OFFBEAT_LV=2,SKYLINE=7,MELFLOOR_FIX=True,KEYSEG=keyseg)
    if r['drum'] is not None: opts.update(DRUM=r['drum'],DRUMFILL=True)
    if piano is not None and dict(r['piano'])[piano]>=150: opts.update(FAITHFUL=[piano],FAITHFUL_PLUS=True)
    return dict(title=title,author=author,sid=sid,vocal=r['vocal'],leads=leads[:3],bass=r['bass'],harm=harm,levels=levels,opts=opts),ms,voc

def audit(key,c):
    for kk,v in make.DEFAULTS.items(): setattr(arrange,kk,v)
    for kk,v in c['opts'].items(): setattr(arrange,kk,v)
    T=f"ss_{c['sid']}/{c['vocal']}.json"; _,voc,_,ms=load(T,T); mst={m:(s,b) for m,s,b in ms}
    qt=lambda s,mi: round(mst[mi][0]+round((s-mst[mi][0])/(60/mst[mi][1]/4))*(60/mst[mi][1]/4),4)
    with contextlib.redirect_stdout(io.StringIO()):
        out=arrange.arrange(c['sid'],c['vocal'],c['leads'],c['bass'],c['title'],'/dev/null',make.REF,harm=c['harm'],level=lambda m: next(l for a,b,l in c['levels'] if a<=m<=b))
    qs={qt(s,m) for s,p,l,m in voc}
    return sum(1 for t in qs if out.get(t)),len(qs)

def run(cands=None,author='Roselia',outjson='roselia_batch.json',prefix='ros_',skip=None):
    rows=[]; cfgs={}
    skip=SKIP if skip is None else skip
    for sid,title in (cands or CANDS):
        if sid in skip: rows.append((title,'跳过: '+skip[sid])); continue
        if not os.path.exists(f'ss_{sid}/0.json'): ssget.get(sid)
        c,ms,voc=auto_config(sid,title,author)
        vm=len({x[3] for x in voc}); dur=ms[-1][1]
        key=prefix+str(sid); make.SONGS[key]=c; cfgs[key]=c
        buf=io.StringIO()
        with contextlib.redirect_stdout(buf): make.make(key)
        o=buf.getvalue(); import re
        n=re.search(r"(\d+)音  格式(\S+)",o)
        have,tot=audit(key,c)
        ks=c['opts']['KEYSEG']
        def f(m):
            r=ks[0][1]
            for a_,b_ in ks:
                if m>=a_: r=b_
            return r
        vw=sum(1 for s_,p,l,m in voc if (p+f(m))%12 in MAJOR)/len(voc)
        rows.append((title,f"主唱白键{vw:.0%} {n.group(1)}音 {int(dur//60)}:{int(dur%60):02d} 主唱{have}/{tot} 人声小节{vm}/{len(ms)} 移调{c['opts']['KEYSEG']} 钢琴{'叠加' if c['opts'].get('FAITHFUL') else '-'} 格式{n.group(2)}"))
    json.dump({k:v for k,v in cfgs.items()},open(outjson,'w'),ensure_ascii=False,default=list)
    for t,s in rows: print(f'{t:24} {s}')
