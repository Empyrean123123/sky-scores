"""每首歌的配置。新增歌曲：在 SONGS 里加一项，然后 python3 make.py <key>
字段: sid=Songsterr songId, vocal/leads/bass/harm=轨道号, levels=[(起小节,止小节,档位0稀/1中/2满)]
      opts=覆盖 arrange.py 顶部参数(PLANS/OFFBEAT_LV/GAP/KEYSEG/...)"""
THIN ={0:{0:1,2:0},1:{0:2,2:1},2:{0:3,1:-1,2:3,3:-1}}
THICK={0:{0:2,2:1},1:{0:2,1:-1,2:2,3:-1},2:{0:3,1:-2,2:3,3:-2}}          # Ave Mujica 两首用的
THICK2={0:{0:2,1:-1,2:2,3:-1},1:{0:2,1:-2,2:2,3:-2},2:{0:3,1:-2,2:3,3:-2}}  # 主歌每拍都有根音

SONGS={
 'kuro': dict(title='黒のバースデイ', author='Ave Mujica', sid=568642, vocal=0, leads=[7], bass=3, harm=[1,2,4,7,8],
   levels=[(0,7,0),(8,15,1),(16,31,0),(32,45,1),(46,61,2),(62,69,1),(70,85,0),(86,99,1),(100,115,2),(116,123,0),(124,155,2),(156,999,1)],
   opts=dict(PLANS=THICK,OFFBEAT_LV=2,DRUM=9,DRUM_GROOVE=True,DRUMFILL=True,MELFLOOR_FIX=True,FAITHFUL=[7],FAITHFUL_PLUS=True)),
 'musica': dict(title='天球(そら)のMúsica', author='Ave Mujica', sid=1233412, vocal=0, leads=[4,1], bass=3, harm=[1,2,4,5,6,7,8],
   levels=[(0,6,0),(7,18,2),(19,26,0),(27,34,1),(35,46,1),(47,78,2),(79,89,1),(90,106,0),(107,122,1),(123,134,1),(135,142,0),(143,162,1),(163,194,2),(195,999,0)],
   opts=dict(PLANS=THICK,OFFBEAT_LV=2,GAP=3,SUSTAIN_COVERS=False,DRUM=9,DRUM_GROOVE=True,DRUMFILL=True,MELFLOOR_FIX=True)),
 'shoujo': dict(title='少女A', author='椎名もた', sid=583260, vocal=0, leads=[3], bass=2, harm=[1,3],
   levels=[(0,3,0),(4,11,1),(12,27,0),(28,35,1),(36,51,2),(52,55,1),(56,63,0),(64,71,1),(72,104,2),(105,108,1),(109,999,1)],
   opts=dict(PLANS=THICK2,OFFBEAT_LV=2,SKYLINE=7,KEYSEG=[(0,3),(89,4)],DRUM=4,DRUM_GROOVE=True,DRUMFILL=True,MELFLOOR_FIX=True)),
 'god': dict(title='God knows...', author='涼宮ハルヒ(CV.平野綾)', sid=26140, vocal=0, leads=[2], bass=4, harm=[1,2,3],
   levels=[(0,16,2),(17,40,0),(41,58,2),(59,74,1),(75,98,0),(99,116,2),(117,134,1),(135,152,2),(153,167,1),(168,999,2)],
   opts=dict(PLANS=THICK2,OFFBEAT_LV=2,SKYLINE=7,DRUM=5)),
 'lost': dict(title='ロストワンの号哭', author='Neru', sid=1407111, vocal=0, leads=[2], bass=4, harm=[1,2,3],
   levels=[(0,17,1),(18,25,0),(26,33,1),(34,41,0),(42,49,1),(50,65,2),(66,73,1),(74,81,0),(82,89,1),(90,121,2),(122,999,1)],
   opts=dict(PLANS=THICK2,OFFBEAT_LV=0,SKYLINE=7,TOPWIN=0.4,DRUM=5)),
 'nonbreath': dict(title='ノンブレス・オブリージュ', author='ピノキオピー', sid='os:5435558', vocal=30, leads=[34,7], bass=47, harm=[20,14,13,46],
   levels=[(0,5,1),(6,21,0),(22,29,1),(30,53,2),(54,60,1),(61,69,0),(70,77,1),(78,101,2),(102,116,2),(117,999,1)],
   opts=dict(PLANS=THICK2,OFFBEAT_LV=2,SKYLINE=7,VOCAL_TOP=True,OS_BPM=148,VOCAL_OCT=[(6,29,12)],MELFLOOR_FIX=True,VOCAL_ACCENT=[(102,116)],VOCAL_FILL_GAP=True)),
 'aizokusei': dict(title='愛属性', author='ピノキオピー', sid='os:4919194', vocal=55, leads=[26,17], bass=48, harm=[52,58,54],
   levels=[(0,4,1),(5,11,0),(12,21,1),(22,36,2),(37,45,0),(46,54,1),(55,61,2),(62,70,0),(71,80,1),(81,96,2),(97,999,0)],
   opts=dict(PLANS=THICK2,OFFBEAT_LV=2,SKYLINE=7,VOCAL_TOP=True,OS_BPM=145,MELFLOOR_FIX=True,VOCAL_OCT=[(5,11,12),(37,45,12)])),
 'yobanashi': dict(title='夜咄ディセイブ', author='じん', sid=4230331, vocal=4, leads=[0], bass=2, harm=[0,1],
   levels=[(0,11,1),(12,19,0),(20,23,1),(24,31,0),(32,38,1),(39,47,2),(48,54,1),(55,62,0),(63,68,1),(69,78,2),(79,84,0),(85,93,2),(94,999,1)],
   opts=dict(PLANS=THICK2,OFFBEAT_LV=2,SKYLINE=7,MELFLOOR_FIX=True,DRUM=3,FAITHFUL=[1],DRUMFILL=True)),
 'kishi': dict(title='起死開戦', author='millsage', sid=4651609, vocal=0, leads=[1,4], bass=3, harm=[2,4],
   levels=[(0,8,1),(9,17,1),(18,25,0),(26,33,1),(34,45,0),(46,49,1),(50,67,2),(68,76,1),(77,84,0),(85,92,1),(93,111,1),(112,116,1),(117,134,2),(135,999,2)],
   opts=dict(PLANS=THICK2,OFFBEAT_LV=2,SKYLINE=7,MELFLOOR_FIX=True,DRUM=5)),
 'arpeggio': dict(title='Arpeggio', author='Ichika Nito', sid=496297, vocal=0, leads=[], bass=0, harm=[],   # 独奏吉他：整把吉他直接搬，不加伴奏
   levels=[(0,999,0)], opts=dict(PLANS={0:{},1:{},2:{}},MELFLOOR_FIX=True)),
 'kamippoina': dict(title='神っぽいな', author='ピノキオピー', sid=4999192, vocal=4, leads=[0], bass=2, harm=[0,1],
   levels=[(0,5,1),(6,11,1),(12,23,0),(24,28,1),(29,41,0),(42,45,2),(46,53,1),(54,61,1),(62,71,0),(72,79,1),(80,88,1),(89,93,2),(94,99,1),(100,999,2)],
   opts=dict(PLANS=THICK2,OFFBEAT_LV=0,SKYLINE=7,MELFLOOR_FIX=True,DRUM=3,DRUM_GROOVE=True,DRUMFILL=True)),
 'keitai': dict(title='携帯恋話', author='まふまふ', sid=4768574, vocal=4, leads=[0], bass=2, harm=[0,1],
   levels=[(0,6,1),(7,15,1),(16,31,0),(32,39,0),(40,43,1),(44,59,2),(60,67,1),(68,83,0),(84,92,1),(93,100,1),(101,112,0),(113,116,1),(117,136,2),(137,999,1)],
   opts=dict(PLANS=THICK2,OFFBEAT_LV=2,SKYLINE=7,MELFLOOR_FIX=True,DRUM=3)),
 'torinouta': dict(title='鳥の詩', author='Lia', sid=4545598, vocal=4, leads=[0], bass=2, harm=[0,1],
   levels=[(0, 22, 0), (23, 29, 1), (30, 39, 2), (40, 84, 1), (85, 89, 2), (90, 109, 1), (110, 112, 2), (113, 134, 1), (135, 142, 0), (143, 174, 1), (175, 999, 0)],
   opts=dict(PLANS=THICK2,OFFBEAT_LV=2,SKYLINE=7,MELFLOOR_FIX=True,DRUM=3,KEYSEG=[(0,-2)],ARPEGGIO=True)),
 'plottwist': dict(title='첫 만남은 계획대로 되지 않아', author='TWS', sid=6926581, vocal=4, leads=[0], bass=2, harm=[1],
   levels=[(0,18,0),(19,23,0),(24,28,1),(29,35,2),(36,36,0),(37,42,1),(43,47,0),(48,52,1),(53,59,2),(60,61,0),(62,999,2)],
   opts=dict(PLANS=THICK2,OFFBEAT_LV=2,SKYLINE=7,MELFLOOR_FIX=True,DRUM=3,FAITHFUL=[1],FAITHFUL_PLUS=True,DRUM_GROOVE=True,DRUMFILL=True)),
 'megitsune': dict(title='メギツネ', author='BABYMETAL', sid=389612, vocal=0, leads=[7,10,2], bass=5, harm=[2,3,12,13],
   levels=[(0,17,1),(18,25,0),(26,33,1),(34,42,1),(43,58,2),(59,66,1),(67,78,0),(79,86,1),(87,94,1),(95,111,1),(112,127,2),(128,135,2),(136,999,1)],
   opts=dict(PLANS=THICK2,OFFBEAT_LV=2,SKYLINE=7,MELFLOOR_FIX=True,DRUM=6,DRUMFILL=True,DRUM_GROOVE=True)),
 'r': dict(title='R', author='Roselia', sid=6941071, vocal=4, leads=[0,2], bass=2, harm=[1],
   levels=[(0, 7, 0), (8, 11, 1), (12, 13, 0), (14, 21, 1), (22, 30, 2), (31, 32, 1), (33, 35, 2), (36, 36, 1), (37, 44, 0), (45, 54, 1), (55, 58, 0), (59, 80, 1), (81, 83, 0), (84, 138, 1), (139, 141, 0), (142, 144, 1), (145, 148, 0), (149, 164, 1), (165, 172, 0), (173, 176, 1), (177, 179, 0), (180, 180, 1), (181, 198, 2), (199, 201, 0), (202, 202, 1), (203, 211, 2), (212, 212, 1), (213, 999, 0)],
   opts=dict(PLANS=THICK2,OFFBEAT_LV=2,SKYLINE=7,MELFLOOR_FIX=True,DRUM=3,DRUMFILL=True,DRUM_GROOVE=True,LEAD_MEAS={2:(0,7)})),
}
# 钢琴版：伴奏如实照搬谱源里的钢琴轨(用户在光遇里弹钢琴)
import copy as _copy
def _piano(key,track,plus=False):
    c=_copy.deepcopy(SONGS[key]); c['title']+='(钢琴版)'
    c['opts']['FAITHFUL']=[track]
    if plus: c['opts']['FAITHFUL_PLUS']=True
    else:
        for k in ('DRUM_GROOVE','DRUMFILL'): c['opts'].pop(k,None)
    SONGS[key+'_piano']=c
# 愛属性(改进版): 移调 -5(主唱白键 91%、折叠 9 个)、读 OS 鼓 ins31
_ai=_copy.deepcopy(SONGS['aizokusei']); _ai['title']+='(改进版)'
_ai['opts'].update(KEYSEG=[(0,-5),(21,-1),(38,-5),(54,-1)],VOCAL_O=0,VOCAL_OCT=[(5,11,12),(37,45,12),(71,80,-12)],DRUM=31,DRUMFILL=True)
SONGS['aizokusei_v2']=_ai
# 已试过: _piano('kishi',4); _piano('nonbreath',46) —— 用户觉得和原版差不多，未采用
# 黒のバースデイ 的钢琴叠加版已转正(见上面 kuro 的 FAITHFUL)
# 无呼吸义务(鼓版: 借 MyGO 718498 的鼓, DRUM=5,DRUM_SID=718498) 试过，用户觉得差不多，未采用


def _fixjson(c):
    c['levels']=[tuple(x) for x in c['levels']]; o=c['opts']
    o['KEYSEG']=[tuple(x) for x in o.get('KEYSEG',[])]
    if 'PLANS' in o: o['PLANS']={int(k):{int(b):v for b,v in d.items()} for k,d in o['PLANS'].items()}
    return c
# Roselia 批量(batch_roselia.py 自动生成的配置)
import json as _json, os as _os
_p=_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),'roselia_batch.json')
if _os.path.exists(_p):
    for _k,_c in _json.load(open(_p)).items():
        SONGS[_k]=_fixjson(_c)
for _f in ('bluswing_batch.json',):
    _pp=_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),_f)
    if _os.path.exists(_pp):
        for _k,_c in _json.load(open(_pp)).items(): SONGS[_k]=_fixjson(_c)
_p2=_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),'extra_songs.json')
if _os.path.exists(_p2):
    for _k,_c in _json.load(open(_p2)).items():
        SONGS[_k]=_fixjson(_c)
# 自己做的新歌放 local_songs.json(格式同 extra_songs.json)，不进仓库
_p3=_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),'local_songs.json')
if _os.path.exists(_p3):
    for _k,_c in _json.load(open(_p3,encoding='utf-8')).items():
        SONGS[_k]=_fixjson(_c)
