"""Songsterr part JSON → [(start_s, pitch, dur_s, measure)]; 连音线合并"""
import json
from fractions import Fraction as F
def tempo_map(d):
    t=d.get('automations',{}).get('tempo',[])
    return sorted((a['measure'],a.get('position',0),a['bpm']) for a in t)
def load(path, tempo_src=None):
    d=json.load(open(path)); tm=tempo_map(json.load(open(tempo_src)) if tempo_src else d)
    tun=d['tuning']; notes=[]; open_ties={}
    sec=0.0; markers=[]; sig=[4,4]; bpm=tm[0][2] if tm else 120; mstarts=[]
    for mi,m in enumerate(d['measures']):
        sig=m.get('signature',sig); mlen=F(sig[0],sig[1])  # 以全音符为单位
        for a in tm:
            if a[0]==mi: bpm=a[2]
        whole=240/bpm   # 一个全音符的秒数
        mstarts.append((mi,sec,bpm))
        if 'marker' in m: markers.append((mi,sec,m['marker']['text']))
        for v in m['voices']:
            pos=F(0)
            for b in v['beats']:
                du=F(*b['duration'])   # Songsterr 的 duration 已含附点/连音缩放
                if b.get('graceNote'): du=F(0)
                if not b.get('rest'):
                    for n in b['notes']:
                        if n.get('rest') or n.get('dead') or 'fret' not in n: continue
                        p=tun[n['string']]+n['fret']; st=sec+float(pos)*whole; dl=float(du)*whole
                        if n.get('tie') and p in open_ties:
                            k=open_ties[p]; notes[k]=(notes[k][0],p,st+dl-notes[k][0],notes[k][3]); continue
                        open_ties[p]=len(notes); notes.append((st,p,dl,mi))
                pos+=du
        sec+=float(mlen)*whole
    return d,notes,markers,mstarts
