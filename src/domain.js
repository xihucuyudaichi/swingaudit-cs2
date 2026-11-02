export const metrics = {overall:'整体 Rating',vs_top5:'vs Top 5',vs_top10:'vs Top 10',vs_top20:'vs Top 20',big_events:'大型赛事',elite_events:'精英赛事',super_elite:'超级精英赛事',big_playoffs:'大型赛淘汰赛',elite_playoffs:'精英赛淘汰赛',grand_finals:'决赛'};
export const defaultScope = {season:'2026',metric:'overall'};
export const fmt = v => v == null ? '—' : Number(v).toFixed(2);
export function stat(data,id,metric='overall',season='2026') {return season==='2026'?data.stats.find(s=>s.player_id===id && s.metric_id===metric):undefined;}
export function compare(data,a,b,scope) {
  const x=stat(data,a,scope.metric,scope.season),y=stat(data,b,scope.metric,scope.season);
  if(a===b)return {status:'conflict',text:'请选择两位不同选手。'};
  if(x?.value==null || y?.value==null)return {status:'missing',text:'当前快照缺少该范围的同口径统计，暂不计算差值。'};
  return {status:'ready',x,y,delta:x.value-y.value,text:`${metrics[scope.metric]} 相差 ${fmt(Math.abs(x.value-y.value))}；样本分别为 ${x.maps} / ${y.maps} 图。`};
}
export function simulate(data,eventId,weight,changes) {
  const event=data.events.find(e=>e.event_id===eventId);
  if(!event)throw Error('请选择有效赛事。');
  if(!Number.isFinite(Number(weight)) || Number(weight)<0 || Number(weight)>2)throw Error('研究权重应在 0–2 之间。');
  if(new Set(changes.map(c=>c.playerId)).size!==changes.length)throw Error('同一选手有多条修改，请合并后重试。');
  if(changes.filter(c=>c.award==='MVP').length>1)throw Error('同届赛事只能有一位 MVP，请修改荣誉设置。');
  for(const c of changes){if(!data.players.some(p=>p.player_id===c.playerId))throw Error('选手不在演示候选池中。');if(!Number.isFinite(Number(c.score))||c.score===''||Number(c.score)<0||Number(c.score)>20)throw Error('表现分应在 0–20 之间。');}
  const rows=data.rankings.baseline.map(p=>{
    const old=data.event_contributions.find(c=>c.player_id===p.player_id&&c.event_id===eventId);
    const change=changes.find(c=>c.playerId===p.player_id);
    const delta=(change?Number(change.score):Number(old?.raw_perf_score||0))*Number(weight)-Number(old?.weighted_honor_pts||0);
    return {...p,base_rank:p.rank,base_total:Number(p.total_honor),delta:Math.round(delta*1000)/1000,total_honor:Math.round((Number(p.total_honor)+delta)*1000)/1000};
  }).sort((a,b)=>b.total_honor-a.total_honor||a.base_rank-b.base_rank);
  rows.forEach((r,i)=>{r.rank=i>0&&r.total_honor===rows[i-1].total_honor?rows[i-1].rank:i+1;r.rank_change=r.base_rank-r.rank;});
  return rows;
}
export function verifyClaim(data,text,scope){
 const names=data.players.filter(p=>text.toUpperCase().includes(p.handle));
 if(names.length!==2 || !/rating/i.test(text))return {kind:'insufficient',summary:'证据不足：本地演示只核对两位虚构选手的 Rating 比较。其他说法需要真实 Agent 与数据接入。',claims:[{title:'原始主张',verdict:'证据不足',body:text}],ids:names.map(p=>p.player_id)};
 const ordered=[...names].sort((a,b)=>text.toUpperCase().indexOf(a.handle)-text.toUpperCase().indexOf(b.handle));
 const [a,b]=ordered;const c=compare(data,a.player_id,b.player_id,scope);
 if(c.status!=='ready')return {kind:'insufficient',summary:c.text,claims:[{title:'同口径数据比较',verdict:'证据不足',body:c.text}],ids:ordered.map(p=>p.player_id)};
 const higher=/更高|高于|比.+高/.test(text),lower=/更低|低于|比.+低/.test(text);
 const supported=higher?c.delta>0:lower?c.delta<0:null;
 const fact={title:`${a.handle} 与 ${b.handle} 的 ${metrics[scope.metric]}`,verdict:supported==null?'证据不足':supported?'支持':'不支持',body:`当前演示值为 ${fmt(c.x.value)} 与 ${fmt(c.y.value)}，对应 ${c.x.maps} 与 ${c.y.maps} 张地图。${supported==null?'原句未明确比较方向，只提供原值。':''}`};
 const inference={title:'单一统计能否确定年度排名？',verdict:'证据不足',body:'整体 Rating 不能单独推出年度名次。还需考虑赛事荣誉、对手范围、高压表现和样本覆盖；当前混合预测模型尚未连接。'};
 return {kind:'checked',summary:supported===true?'数值比较有据可查，排名推断仍需更多证据。':supported===false?'当前数据不支持这个数值方向，排名也不能由单项统计确定。':'已找到两位选手，请明确你希望核对的比较方向。',claims:[fact,...(/排名|名次|更强|必然|肯定/.test(text)?[inference]:[])],ids:ordered.map(p=>p.player_id)};
}
export function csv(rows){return '\uFEFF'+rows.map(row=>row.map(v=>'"'+String(v??'').replaceAll('"','""')+'"').join(',')).join('\r\n');}
