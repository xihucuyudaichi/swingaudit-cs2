from pathlib import Path
p=Path('src/main.jsx');s=p.read_text(encoding='utf-8');s="import LiveResearch from './LiveResearch';\n"+s
s=s.replace("const nav=[['/','观察室'],","const nav=[['/live','真实研究'],['/','观察室'],")
s=s.replace("let page;if(path==='/')", "let page;if(path==='/live')page=<LiveResearch/>;else if(path==='/')")
s=s.replace('交互演示 · 虚构数据 · Agent 尚未连接',"{path==='/live'?'真实Agent · 第三方历史快照 · 非实时数据':'交互演示 · 虚构数据 · 真实服务见「真实研究」'}")
p.write_text(s,encoding='utf-8')
