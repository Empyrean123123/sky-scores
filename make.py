"""用法: python3 make.py <歌key...>        生成琴谱到桌面(见 songs.py)
      python3 make.py --search 歌名       在 Songsterr 搜谱
      python3 make.py --tracks <songId>   看某份谱的轨道(找人声/主奏/贝斯)"""
import os,sys,json,importlib,subprocess
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE); sys.path.insert(0,HERE)
import arrange, ssget
from songs import SONGS
DESK=os.path.expanduser('~/Desktop/')   # 新做/改好的放桌面；用户会把之前的版本收进 ~/Desktop/New Folder With Items/
if not os.path.isdir(DESK): DESK=os.path.join(HERE,'output/'); os.makedirs(DESK,exist_ok=True)   # 云端没有桌面
ARCHIVE=os.path.expanduser('~/Desktop/New Folder With Items/')
REF=os.path.join(HERE,'template.txt')   # 格式模板(KiLLKiSS 的头部字段)
DEFAULTS={k:getattr(arrange,k) for k in ('PLANS','OFFBEAT_LV','GAP','KEYSEG','REPEAT_MIN','REPEAT_LV','TOPWIN','SKYLINE','SUSTAIN_COVERS','OS_BPM','OS_OFFSET','VOCAL_TOP','VOCAL_OCT','MELFLOOR_FIX','DRUM','FAITHFUL','DRUMFILL','VOCAL_ACCENT','FAITHFUL_PLUS','DRUM_GROOVE','ARPEGGIO','GROOVE_THICK','DRUM_SID','DRUM_MOFF','LEAD_MEAS','VOCAL_FILL_GAP','VOCAL_SID','VOCAL_O','FAITHFUL_NOBASS','VOCAL_MOFF','MASTER_TRACK')}
FIELDS=['name','author','transcribedBy','isComposed','bpm','bitsPerPage','pitchLevel','isEncrypted','songNotes']
def curl(u): return subprocess.run(['curl','-s',u],capture_output=True).stdout
def make(key):
    c=SONGS[key]
    sid=c['sid']
    if isinstance(sid,str) and sid.startswith('mid:'): pass
    elif isinstance(sid,str) and sid.startswith('os:'):
        p=f'os/{sid[3:]}.bin'
        if not os.path.exists(p): os.makedirs('os',exist_ok=True); open(p,'wb').write(curl(f'https://onlinesequencer.net/app/api/get_proto.php?id={sid[3:]}'))
    elif not os.path.exists(f"ss_{sid}/0.json"): ssget.get(sid)
    for k,v in DEFAULTS.items(): setattr(arrange,k,v)
    for k,v in c.get('opts',{}).items(): setattr(arrange,k,v)
    lv=lambda m: next(l for a,b,l in c['levels'] if a<=m<=b)
    tmp=os.path.join(HERE,f".out_{key}.txt")
    arrange.arrange(c['sid'],c['vocal'],c['leads'],c['bass'],c['title'],tmp,REF,harm=c['harm'],level=lv)
    d=json.loads(open(tmp,encoding='utf-16').read()); d[0]['author']=c['author']
    dst=DESK+c['title']+'.txt'
    open(dst,'w',encoding='utf-16').write(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n')
    b=open(dst,'rb').read(); s=json.loads(b.decode('utf-16'))[0]; n=s['songNotes']; ts=[x['time'] for x in n]
    ok=b[:2]==b'\xff\xfe' and list(s)==FIELDS and ts==sorted(ts) and len(n)==len({(x['time'],x['key']) for x in n}) and all(0<=int(x['key'][4:])<=14 for x in n)
    print(f'  → {dst}  {len(n)}音  格式{"OK" if ok else "有问题!"}')
if __name__=='__main__':
    a=sys.argv[1:]
    if not a: print(__doc__, '\n已配置:', ', '.join(f'{k}({v["title"]})' for k,v in SONGS.items()))
    elif a[0]=='--search':
        import urllib.parse
        for s in json.loads(curl('https://www.songsterr.com/api/songs?size=20&pattern='+urllib.parse.quote(' '.join(a[1:])))):
            print(s['songId'],'|',s['title'],'|',s['artist'])
    elif a[0]=='--tracks':
        m=json.loads(curl(f'https://www.songsterr.com/api/meta/{a[1]}'))
        print(m['title'],'|',m['artist']); [print(f'  {i}: {t.get("instrument")} | {t.get("name")} | views {t.get("views")}') for i,t in enumerate(m['tracks'])]
    else:
        for k in a: make(k)
