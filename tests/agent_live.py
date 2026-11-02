import urllib.request,json
req=urllib.request.Request('http://127.0.0.1:5188/api/agent',data=json.dumps({'year':'2025','question':'查询donk的2025年收录赛事数量与地图数，给出来源和限制。'}).encode(),headers={'Content-Type':'application/json'})
r=json.load(urllib.request.urlopen(req,timeout=180))
open('verification/agent-live.json','w',encoding='utf-8').write(json.dumps(r,ensure_ascii=False,indent=2))
print(json.dumps({'model':r['model'],'tool_calls':len(r['tools']),'answer_length':len(r['answer'])}))
