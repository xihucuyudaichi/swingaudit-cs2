import json,openpyxl
from pathlib import Path
p=Path('data/source-audit/iftv/if_sim_2024_events.xlsx');w=openpyxl.load_workbook(p,read_only=True,data_only=True);headers=next(w.active.values);print(json.dumps(list(headers),ensure_ascii=True))
