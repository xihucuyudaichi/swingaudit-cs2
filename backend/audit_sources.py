from pathlib import Path
import urllib.request,json,hashlib,openpyxl
root=Path('data/source-audit/iftv');root.mkdir(exist_ok=True)
files=[f'if_sim_{y}_{t}.xlsx' for y in [2024,2025] for t in ['events','baseline']]+[f'hltv_opponent_{y}.xlsx' for y in [2024,2025]]
manifest=[]
for name in files:
 url='https://raw.githubusercontent.com/bootsh-zvuat/IFTV-TOP20/main/data/'+name
 target=root/name
 if not target.exists():target.write_bytes(urllib.request.urlopen(url,timeout=40).read())
 b=target.read_bytes();sheets=[]
 wb=openpyxl.load_workbook(target,read_only=True,data_only=True)
 for ws in wb:
  rows=list(ws.iter_rows(values_only=True));sheets.append({'sheet':ws.title,'rows':len(rows)-1,'headers':rows[0],'sample':rows[1:3]})
 manifest.append({'file':name,'url':url,'sha256':hashlib.sha256(b).hexdigest(),'sheets':sheets})
 print(name,json.dumps(sheets,ensure_ascii=False,default=str))
(root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
