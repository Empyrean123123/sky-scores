import json,gzip,subprocess,os,sys
def curl(u): return subprocess.run(['curl','-s',u],capture_output=True).stdout
def get(sid):
    m=json.loads(curl(f'https://www.songsterr.com/api/meta/{sid}'))
    os.makedirs(f'ss_{sid}',exist_ok=True)
    for i,t in enumerate(m['tracks']):
        b=curl(f"https://dqsljvtekg760.cloudfront.net/{sid}/{m['revisionId']}/{m['image']}/{i}.json")
        if b[:2]==b'\x1f\x8b': b=gzip.decompress(b)
        open(f'ss_{sid}/{i}.json','wb').write(b)
    return m
if __name__=='__main__':
    for s in sys.argv[1:]: get(int(s)); print('ok',s)
