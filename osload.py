"""Online Sequencer proto → 与 ssparse.load 相同的格式 [(start_s, pitch, dur_s, measure)]
时间单位: OS 的 1 step = 十六分音符; 4/4 拍; offset=第一小节从第几个 step 开始"""
import collections
from os_parse import load as osl
def load_os(path, ins, bpm=None, offset=0):
    s,n=osl(path); bpm=bpm or s.get(1,110); st=60/bpm/4
    ins=set(ins) if isinstance(ins,(list,tuple,set)) else {ins}
    notes=sorted((( t-offset)*st, p, max(l,0.25)*st, int((t-offset)//16)) for t,p,l,i,v in n if i in ins and t>=offset-1e-6)
    L=max(t for t,*_ in n); nm=int((L-offset)//16)+2
    ms=[(m, m*16*st, bpm) for m in range(nm)]
    return {'name':str(ins),'tuning':[]}, notes, [], ms
def best_offset(path, ins):
    """贝斯/和弦起音最常落在的 16 分位置 → 视为小节第 1 拍(取模 16 的众数, 只看 0/4/8/12)"""
    s,n=osl(path); ins=set(ins)
    c=collections.Counter(int(round(t))%16 for t,p,l,i,v in n if i in ins)
    return max(range(16), key=lambda o: c[o]*2 + c[(o+8)%16] + 0.5*(c[(o+4)%16]+c[(o+12)%16]))
