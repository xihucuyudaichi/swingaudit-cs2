"""Normalize a quarantined third-party historical snapshot; never claim official verification."""
import json, hashlib, math
from pathlib import Path
import openpyxl
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/source-audit/iftv'
def read(name):
 w=openpyxl.load_workbook(RAW/name,read_only=True,data_only=True)
 rows=list(w.active.values);return [dict(zip(rows[0],r)) for r in rows[1:]]
def build():
 seasons={}
 for year in [2024,2025]:
  records=read(f'if_sim_{year}_events.xlsx');baseline=read(f'if_sim_{year}_baseline.xlsx');opponents=read(f'hltv_opponent_{year}.xlsx')
  officials={r['选手名'].casefold():r['名次'] for r in baseline}
  opp={r['选手'].casefold():r for r in opponents}
  name_ids={}
  for r in records:name_ids.setdefault(str(r['选手名']).casefold(),set()).add(r['选手ID'])
  players={};events={}
  for index,r in enumerate(records):
   name=str(r['选手名']);name_key=name.casefold();key=name_key if len(name_ids[name_key])==1 else f"{name_key}~{r['选手ID']}";event=str(r['赛事名称'])
   player=players.setdefault(key,{'id':key,'name':name,'year':year,'events':[],'source_ids':[],'official_rank':officials.get(name_key) if len(name_ids[name_key])==1 else None,'identity_status':'source_local_id' if len(name_ids[name_key])==1 else 'ambiguous_name_split'})
   if r['选手ID'] not in player['source_ids']:player['source_ids'].append(r['选手ID'])
   item={'player_id':key,'source_player_id':r['选手ID'],'event':event,'rating':r['Rating'],'maps':r['地图数'],'adr':r['ADR'],'kpr':r['KPR'],'award':r['荣誉类型'],'award_order':r['荣誉顺位'],'team':r['队伍'],'team_place':r['队伍名次'],'tier':r['赛事级别'],'source_weight':r['赛事权重'],'row':index+2,'sheet':'data','source_file':f'if_sim_{year}_events.xlsx','source_url':f'https://github.com/bootsh-zvuat/IFTV-TOP20/blob/main/data/if_sim_{year}_events.xlsx','rating_version':None,'period_start':None,'period_end':None}
   player['events'].append(item)
   events.setdefault(event,{'name':event,'year':year,'tier':r['赛事级别'],'players':[]})['players'].append({'name':name,**item})
  for key,p in players.items():
   valid=[r for r in p['events'] if isinstance(r['rating'],(int,float)) and isinstance(r['maps'],(int,float)) and r['maps']>0]
   maps=sum(r['maps'] for r in valid);p['maps']=maps
   p['rating_estimate']=round(sum(r['rating']*r['maps'] for r in valid)/maps,4) if maps else None
   p['mvp']=sum(r['award']=='MVP' for r in p['events']);p['evp']=sum(r['award']=='EVP' for r in p['events'])
   p['opponents']=opp.get(p['name'].casefold()) if p['identity_status']!='ambiguous_name_split' else None;p['rating_note']='所收录赛事Rating按地图数加权的近似值，非官方全年Rating；未确认版本一致性'
   if p['opponents']:
    p['opponents']={**p['opponents'],'source_file':f'hltv_opponent_{year}.xlsx','sheet':'opponent','row':next(i+2 for i,r in enumerate(opponents) if r['选手'].casefold()==p['name'].casefold())}
  seasons[str(year)]={'players':list(players.values()),'events':list(events.values()),'rows':len(records)}
 result={'meta':{'source':'https://github.com/bootsh-zvuat/IFTV-TOP20','status':'third_party_unverified','retrieved_at':'2026-10-22','notice':'第三方历史数据快照，未逐项回源核验；2026实时数据未接入。'},'seasons':seasons}
 target=ROOT/'data/historical.json';target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({y:{'players':len(s['players']),'events':len(s['events']),'rows':s['rows']} for y,s in seasons.items()}))
if __name__=='__main__':build()
