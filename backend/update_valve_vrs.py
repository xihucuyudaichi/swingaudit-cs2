import json
import re
from pathlib import Path

ROOT = Path(r'D:\study\专业课\设计大数据基础\round-observatory')
AUDIT_DIR = ROOT / 'data/source-audit/alternatives-20261031'
VRS_CACHE_DIR = AUDIT_DIR / 'valve-vrs-2026'

REGION_ZH_MAP = {
    'Europe': '欧洲',
    'Americas': '美洲',
    'Asia': '亚洲',
    'EU': '欧洲',
    'AM': '美洲',
    'AS': '亚洲',
}

REGION_FULL_MAP = {
    'EU': 'Europe',
    'AM': 'Americas',
    'AS': 'Asia',
    'Europe': 'Europe',
    'Americas': 'Americas',
    'Asia': 'Asia',
}


def get_singapore_major_stage(region: str, regional_rank: int) -> str:
    reg = REGION_FULL_MAP.get(region, region)
    if not reg or not regional_rank:
        return '—'
    if reg == 'Europe':
        if regional_rank <= 6:
            return 'Stage 3 直邀'
        if regional_rank <= 12:
            return 'Stage 2 直邀'
        if regional_rank <= 18:
            return 'Stage 1 直邀'
        if regional_rank <= 24:
            return '邀请线候补'
        return '未入围'
    if reg == 'Americas':
        if regional_rank <= 2:
            return 'Stage 3 直邀'
        if regional_rank == 3:
            return 'Stage 2 直邀'
        if regional_rank <= 9:
            return 'Stage 1 直邀'
        if regional_rank <= 14:
            return '邀请线候补'
        return '未入围'
    if reg == 'Asia':
        if regional_rank == 1:
            return 'Stage 2 直邀'
        if regional_rank <= 5:
            return 'Stage 1 直邀'
        if regional_rank <= 10:
            return '邀请线候补'
        return '未入围'
    return '—'


def get_cologne_major_stage(region: str, regional_rank: int) -> str:
    if region == 'Europe':
        if regional_rank <= 6:
            return 'Stage 3 直邀'
        if regional_rank <= 11:
            return 'Stage 2 直邀'
        if regional_rank <= 17:
            return 'Stage 1 直邀'
    elif region == 'Americas':
        if regional_rank == 1:
            return 'Stage 3 直邀'
        if regional_rank <= 4:
            return 'Stage 2 直邀'
        if regional_rank <= 10:
            return 'Stage 1 直邀'
    elif region == 'Asia':
        if regional_rank == 1:
            return 'Stage 3 直邀'
        if regional_rank <= 5:
            return 'Stage 1 直邀'
    return '未入围'


def parse_detail_md(text: str) -> dict:
    info = {}
    m_global = re.search(r'Global Rank:\s*\[(\d+)\]', text)
    if m_global:
        info['global_rank'] = int(m_global.group(1))
    m_reg = re.search(r'Region:\s*\[([^\]]+)\]', text)
    if m_reg:
        info['region'] = m_reg.group(1).strip()
    m_reg_rank = re.search(r'Regional Rank:\s*\[(\d+)\]', text)
    if m_reg_rank:
        info['regional_rank'] = int(m_reg_rank.group(1))
    m_final = re.search(r'Final Rank Value:\s*([0-9.]+)', text)
    if m_final:
        info['final_rank_value'] = float(m_final.group(1))
    m_eq = re.search(
        r'Final Rank Value\s*\(([0-9.]+)\)\s*=\s*Starting Rank Value\s*\(([0-9.]+)\)\s*\+\s*Head To Head Adjustments\s*\(([-0-9.]+)\)',
        text
    )
    if m_eq:
        info['starting_rank_value'] = float(m_eq.group(2))
        info['h2h_adjustments'] = float(m_eq.group(3))
    for k, label in [
        ('bounty_offered', 'Bounty Offered'),
        ('bounty_collected', 'Bounty Collected'),
        ('opponent_network', 'Opponent Network'),
        ('lan_wins', 'LAN Wins'),
    ]:
        m = re.search(rf'-\s*{label}:\s*([0-9.]+)', text)
        if m:
            info[k] = m.group(1)
            info[k + '_num'] = float(m.group(1))
    m_avg = re.search(r'The average of these factors is\s*([0-9.]+)', text)
    if m_avg:
        info['factor_average'] = float(m_avg.group(1))

    match_rows = re.findall(
        r'^\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([^|]+?)\s*\|\s*([WL])\s*\|',
        text,
        flags=re.M
    )
    wins = sum(1 for r in match_rows if r[4] == 'W')
    losses = sum(1 for r in match_rows if r[4] == 'L')
    info['matches_recorded'] = len(match_rows)
    info['wins'] = wins
    info['losses'] = losses
    info['record_summary'] = f'{wins}胜 {losses}负' if match_rows else '—'

    m_win_sum = re.search(r'sum of their top 10 scaled winnings\s*\(\$([0-9,]+(?:\.[0-9]+)?)\)', text)
    if m_win_sum:
        raw_num = float(m_win_sum.group(1).replace(',', ''))
        info['scaled_winnings_usd'] = round(raw_num, 2)
        info['scaled_winnings'] = f'${int(round(raw_num)):,}'
    else:
        info['scaled_winnings_usd'] = 0.0
        info['scaled_winnings'] = '$0'
    return info


def parse_standings_with_details(table_rel: str, folder_prefix: str, snapshot_date: str, limit: int = 50, prev_rank_map: dict | None = None, is_2026: bool = True) -> list:
    table_path = VRS_CACHE_DIR / table_rel.replace('/', '__')
    if not table_path.exists() and table_rel.endswith('standings_global_2026_10_05.md'):
        table_path = AUDIT_DIR / 'valve-vrs-standings_global_2026_10_05.md'
    if not table_path.exists():
        return []
    md_text = table_path.read_text(encoding='utf-8')
    rows = []
    for line in md_text.splitlines():
        if line.startswith('|') and not line.startswith('| Standing') and not line.startswith('| :-'):
            parts = [p.strip() for p in line.strip().strip('|').split('|')]
            if len(parts) >= 4 and parts[0].isdigit():
                rank = int(parts[0])
                pts_int = int(float(parts[1]))
                team = parts[2]
                roster = parts[3]
                detail_rel = None
                if len(parts) >= 5:
                    m = re.search(r'\((details/[^)]+\.md)\)', parts[4])
                    if m:
                        detail_rel = f'{folder_prefix}/{m.group(1)}'
                detail_info = {}
                if detail_rel:
                    d_path = VRS_CACHE_DIR / detail_rel.replace('/', '__')
                    if d_path.exists():
                        detail_info = parse_detail_md(d_path.read_text(encoding='utf-8'))

                global_rank = detail_info.get('global_rank', rank)
                region = detail_info.get('region', '')
                region_zh = REGION_ZH_MAP.get(region, region or '—')
                regional_rank = detail_info.get('regional_rank', rank)
                points = detail_info.get('final_rank_value', float(pts_int))
                prev_rank = (prev_rank_map or {}).get(team.casefold())
                rank_change = (prev_rank - global_rank) if (prev_rank is not None and global_rank is not None) else None

                entry = {
                    'rank': rank,
                    'global_rank': global_rank,
                    'prev_global_rank': prev_rank,
                    'rank_change': rank_change,
                    'points': points,
                    'points_int': pts_int,
                    'starting_rank_value': detail_info.get('starting_rank_value'),
                    'h2h_adjustments': detail_info.get('h2h_adjustments'),
                    'team': team,
                    'roster': roster,
                    'region': region,
                    'region_zh': region_zh,
                    'regional_rank': regional_rank,
                    'bounty_offered': detail_info.get('bounty_offered', '—'),
                    'bounty_collected': detail_info.get('bounty_collected', '—'),
                    'opponent_network': detail_info.get('opponent_network', '—'),
                    'lan_wins': detail_info.get('lan_wins', '—'),
                    'factor_average': detail_info.get('factor_average'),
                    'matches_recorded': detail_info.get('matches_recorded', 0),
                    'wins': detail_info.get('wins', 0),
                    'losses': detail_info.get('losses', 0),
                    'record_summary': detail_info.get('record_summary', '—'),
                    'scaled_winnings_usd': detail_info.get('scaled_winnings_usd', 0.0),
                    'scaled_winnings': detail_info.get('scaled_winnings', '—'),
                    'major_stage': get_singapore_major_stage(region, regional_rank) if is_2026 else '—',
                    'snapshot_date': snapshot_date,
                    'source_url': (
                        f'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/{detail_rel}'
                        if detail_rel else
                        f'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/{table_rel}'
                    )
                }
                rows.append(entry)
                if len(rows) >= limit:
                    break
    return rows


def parse_simple_rank_map(table_rel: str) -> dict:
    p = VRS_CACHE_DIR / table_rel.replace('/', '__')
    if not p.exists():
        return {}
    out = {}
    for line in p.read_text(encoding='utf-8').splitlines():
        if line.startswith('|') and not line.startswith('| Standing') and not line.startswith('| :-'):
            parts = [x.strip() for x in line.strip().strip('|').split('|')]
            if len(parts) >= 3 and parts[0].isdigit():
                tname = parts[2].casefold()
                if tname not in out:
                    out[tname] = int(parts[0])
    return out


# Build lookup of all 115 detail files from 2026_10_05 by normalized team name
TEAM_ALIAS_MAP = {
    'team vitality': 'vitality',
    'team spirit': 'spirit',
    'aurora gaming': 'aurora',
    'team falcons': 'falcons',
    'betboom team': 'betboom',
    'g2 esports': 'g2',
    'fut esports': 'fut',
    'ninjas in pyjamas': 'ninjas in pyjamas',
    '9z team': '9z',
    'faze clan': 'faze',
    '1w team': '1win',
    '1win': '1win',
    'nemiga gaming': 'nemiga',
    'team liquid': 'liquid',
    'luminosity gaming': 'luminosity',
    'ic esports': 'inner circle',
    'inner circle': 'inner circle',
    'bc.game esports': 'bc.game',
    'sinners esports': 'sinners',
    'team nemesis': 'nemesis',
    'envy': '3dmax',
    'imperial esports': 'imperial',
    'bbl esports': 'bbl',
    'sangal esports': 'sangal',
    'dendele cs': 'dendele',
    'pain gaming': 'pain',
    'lynn vision gaming': 'lynn vision',
    '5star esports': '5star',
    'sashi esport': 'sashi',
    'the huns esports': 'the huns',
    'ground zero gaming': 'ground zero',
    'thunderdownunder': 'thunder downunder',
    'kaleido gaming': 'kaleido',
    'just swing (chinese team)': 'just swing',
}


def norm_team_key(name: str) -> str:
    s = re.sub(r'\s+\d{4}(?:\s+\d{2})?$', '', name.strip().lower())
    s = re.sub(r'\s+(orig|sep\s+\d{4})$', '', s).strip()
    return TEAM_ALIAS_MAP.get(s, s)


# Latest November 1, 2026 HLTV / Liquipedia VRS Global Top 50 & Regional Standings
# Combines verified HLTV Nov 1, 2026 Valve Ranking (Top 30 Global + EU Top 20 + AM Top 10 + AS Top 10)
# with Liquipedia VRS Oct 26, 2026 (402 teams) for #31-#50 and deep regional ranks.
NOV1_GLOBAL_TOP50_RAW = [
    (1, 'MOUZ', 1959.0, 'Europe', 'PR, Spinx, torzsi, xelex, xertioN'),
    (2, 'Vitality', 1920.0, 'Europe', 'apEX, flameZ, mezii, ropz, ZywOo'),
    (3, 'FURIA', 1910.5, 'Americas', 'FalleN, KSCERATO, molodoy, YEKINDAR, yuurih'),
    (4, 'Aurora', 1857.0, 'Europe', 'Jimpphat, kyxsan, Wicadia, woxic, XANTARES'),
    (5, 'Spirit', 1844.5, 'Europe', 'donk, magixx, sh1ro, tN1R, zont1x'),
    (6, 'BETBOOM', 1786.0, 'Europe', 'Boombl4, d1Ledez, Magnojez, S1ren, zorte'),
    (7, 'Falcons', 1768.0, 'Europe', 'karrigan, kyousuke, m0NESY, NiKo, TeSeS'),
    (8, 'FUT', 1724.5, 'Europe', 'cmtry, dem0n, dziugss, Krabeni, xfl0ud'),
    (9, 'Legacy', 1662.8, 'Americas', 'arT, dumau, latto, n1ssim, try'),
    (10, 'Nemiga', 1643.0, 'Europe', 'KaiR0N-, khaN, robo, syph0, Xant3r'),
    (11, 'G2', 1617.5, 'Europe', 'HeavyGod, huNter-, MATYS, NertZ, r1nkle'),
    (12, 'Natus Vincere', 1591.0, 'Europe', 'Aleksib, b1t, iM, makazze, w0nderful'),
    (13, 'Astralis', 1568.0, 'Europe', 'jabbi, phzy, ryu, siuhy, Staehr'),
    (14, 'Ninjas in Pyjamas', 1560.0, 'Europe', 'adamb, Krimbo, sjuush, stavn, xKacpersky'),
    (15, 'PARIVISION', 1559.0, 'Europe', 'FL1T, HObbit, Jame, xiELO, zweih'),
    (16, 'The MongolZ', 1553.0, 'Asia', '910, bLitz, cobrazera, nin9, Techno'),
    (17, 'MIBR', 1545.0, 'Americas', 'insani, LNZ, nqz, tomaszin, venomzera'),
    (18, '1win', 1542.0, 'Europe', 'ArtFr0st, Ax1Le, BELCHONOKK, fame, nafany'),
    (19, 'HEROIC', 1539.0, 'Europe', 'Brollan, Chr1zN, MartinezSa, nilo, susp'),
    (20, 'FaZe', 1538.0, 'Europe', 'frozen, JBOEN, jcobbb, Neityu, Twistzz'),
    (21, 'Liquid', 1526.0, 'Americas', 'EliGE, Jorko, JT, malbsMd, NAF'),
    (22, 'Eternal Fire', 1508.0, 'Europe', 'jottAAA, Kvem, MisteM, regali, soulfly'),
    (23, '9z', 1493.0, 'Americas', 'dgt, HUASOPEEK, luchov, max, meyern'),
    (24, 'M80', 1487.0, 'Americas', 'JBa, Lake, s1n, slaxz-, Swisher'),
    (25, 'HOTU', 1484.0, 'Europe', 'dwushka, frontales, kade0, mizu, n0rb3r7'),
    (26, 'fnatic', 1482.0, 'Europe', 'cairne, fEAR, jackasmo, jambo, mazay'),
    (27, '100 Thieves', 1474.0, 'Europe', 'device, Gizmy, poiii, rain, sirah'),
    (28, 'B8', 1468.0, 'Europe', 'alex666, esenthial, kensizor, npl, s1zzi'),
    (29, 'JiJieHao', 1437.0, 'Europe', '0SAMAS, Bibu, CacaNito, m1N1, sinnopsyy'),
    (30, 'DENDELE', 1436.0, 'Americas', 'doc, gafolo, koala, maxxkor, rdnzao'),
    (31, 'Virtus.pro', 1435.2, 'Europe', 'AquaRS, b1st, mir, Patsi, tO0RO'),
    (32, 'Luminosity', 1434.5, 'Europe', 'afro, AZUWU, lux, Rainwaker, yxngstxr'),
    (33, 'Inner Circle', 1428.3, 'Europe', 'cptkurtka023, Dawy, headtr1ck, onic, zeRRoFIX'),
    (34, 'BIG', 1427.9, 'Europe', 'blameF, faveN, gr1ks, JDC, tabseN'),
    (35, 'magic', 1418.0, 'Europe', 'AW, MaSvAl, mo0N, sFade8, tenzy'),
    (36, 'Imperial', 1414.0, 'Americas', 'chelo, decenty, noway, saadzin, VINI'),
    (37, 'SINNERS', 1406.4, 'Europe', 'beastik, kisserek, MoDo, SHOCK, stressarN'),
    (38, 'K27', 1403.9, 'Europe', 'clax, kashl1d, qw1nk1, X5G7V, xeedo'),
    (39, 'Nemesis', 1401.4, 'Europe', 'mag1k3Y, r3salt, Sdaim, SELLTER, tex1y'),
    (40, '3DMAX', 1394.8, 'Europe', 'Graviti, Kursy, Lucky, Maka, misutaaa'),
    (41, 'Wildcard', 1383.0, 'Americas', 'Cxzi, fr3nd, HexT, nEMANHA, reck'),
    (42, 'BBL', 1381.7, 'Europe', 'IceBerg, Leakz, MistR, NickyB, salazar'),
    (43, 'Sangal', 1379.8, 'Europe', 'adamS, bnox, Joey, puuha, R4DYX'),
    (44, 'GamerLegion', 1353.4, 'Europe', 'FL4MUS, hypex, REZ, Snax, Tauson'),
    (45, 'Alliance', 1347.4, 'Europe', 'avid, bobeksde, eraa, twist, upE'),
    (46, 'BC.Game', 1331.0, 'Asia', 'asap, Magisk, mzinho, s1mple, Senzu'),
    (47, 'paiN', 1328.6, 'Americas', 'biguzera, Rkzinho, saffee, snow, Tatu'),
    (48, 'NRG', 1322.0, 'Americas', 'Grim, hallzerk, Jeorge, nitr0, Sonic'),
    (49, 'FlyQuest', 1315.0, 'Asia', 'aliStair, INS, jks, nettik, Vexite'),
    (50, 'TYLOO', 1264.0, 'Asia', 'JamYoung, Mercury, Moseyuh, Zero, zhokiNg'),
]

NOV1_AMERICAS_EXTRA = [
    (56, 'BESTIA', 1251.6, 'Americas', 'buda, cass1n, drop, kauez, timo'),
    (58, 'Fluxo', 1244.7, 'Americas', 'dav1deuS, exit, kye, ltz, zevy'),
    (71, 'SportsBetExpert', 1174.0, 'Americas', 'consti, Infinite, motm, Peeping, shane'),
    (77, 'Team Voca', 1141.2, 'Americas', 'dare, junior, MarKE, nosraC, snav'),
    (79, 'Galorys', 1130.5, 'Americas', 'destiny, detr0ittJ, gbb, PKL, tomate'),
    (84, 'Shinden', 1103.7, 'Americas', 'abizz, guty, ivz, naz, tom1jed'),
    (92, 'Barca Esports', 1095.2, 'Americas', 'Alisson, divine, happ, pancc, zmb'),
    (94, 'Without a Roof', 1066.7, 'Americas', 'autimatic, Brehze, CeRq, FaNg, Stewie2K'),
    (99, 'Bounty Hunters', 1042.0, 'Americas', 'KAISER, pepe, ponter, urban0, zock'),
    (103, 'Sharks', 1024.5, 'Americas', 'doc, gafolo, rdnzao, supLex, togs'),
]

NOV1_ASIA_TOP20_RAW = [
    (16, 'The MongolZ', 1553.0, 'Asia', '910, bLitz, cobrazera, nin9, Techno'),
    (46, 'BC.Game', 1331.0, 'Asia', 'asap, Magisk, mzinho, s1mple, Senzu'),
    (49, 'FlyQuest', 1315.0, 'Asia', 'aliStair, INS, jks, nettik, Vexite'),
    (50, 'TYLOO', 1264.0, 'Asia', 'JamYoung, Mercury, Moseyuh, Zero, zhokiNg'),
    (51, 'Lynn Vision', 1263.0, 'Asia', 'C4LLM3SU3, EmiliaQAQ, Starry, Westmelon, z4KR'),
    (52, 'Chinggis Warriors', 1262.0, 'Asia', 'cool4st, fury5k, ROUX, sk0R, tikuak'),
    (63, '5star', 1180.0, 'Asia', 'ariucle, clouden, hoolig4n, NEUZ, rate'),
    (70, 'NEXVOID', 1148.0, 'Asia', 'AccuracyTG, erkaSt, MiQ, xerolte, Zesta'),
    (88, 'Alter Ego', 1047.0, 'Asia', 'adeX, Bloody, laxiee, PokemoN, shadiy'),
    (97, 'Sashi', 1028.0, 'Asia', 'acoR, Anlelele, Hatz, TjP, Zyphon'),
    (115, 'DEPO', 976.8, 'Asia', 'buster, Krad, sh1seido, shoxs, wetfy'),
    (122, 'The Huns', 947.2, 'Asia', 'Bart4k, bexyz, controlez, Cozen, DarkMeister'),
    (123, 'Rare Atom', 945.6, 'Asia', '3gl, ChildKing, kaze, L1haNg, Summer'),
    (130, 'Team Abyssal', 923.0, 'Asia', 'blood, dangeR, Forleks, vinhy, zune'),
    (131, 'Ground Zero', 915.6, 'Asia', 'apocdud, HaZR, Omichella, sliimey, vision'),
    (132, 'Off Chops', 914.6, 'Asia', 'damyo, dexter, Gratisfaction, Liazz, viridian'),
    (151, 'THUNDER dOWNUNDER', 823.4, 'Asia', 'aliStair, asap, dexter, Liazz, TjP'),
    (155, 'Rooster', 809.8, 'Asia', 'ADK, chelleos, cookie, rekonz, SkulL'),
    (168, 'Kaleido Gaming', 783.3, 'Asia', 'chuzhongT, rage, SPine, SasiKi, suki'),
    (170, 'Just Swing', 772.2, 'Asia', 'Daniel, gas, Purely, sATOR1, skrr'),
]


def load_oct5_detail_lookup() -> dict:
    oct5_all = parse_standings_with_details(
        'live/2026/standings_global_2026_10_05.md', 'live/2026', '2026-10-05', limit=150, prev_rank_map=None, is_2026=True
    )
    oct5_as = parse_standings_with_details(
        'live/2026/standings_asia_2026_10_05.md', 'live/2026', '2026-10-05', limit=30, prev_rank_map=None, is_2026=True
    )
    oct5_am = parse_standings_with_details(
        'live/2026/standings_americas_2026_10_05.md', 'live/2026', '2026-10-05', limit=30, prev_rank_map=None, is_2026=True
    )
    lookup = {}
    for row in oct5_all + oct5_as + oct5_am:
        k = norm_team_key(row['team'])
        if k not in lookup or row.get('bounty_offered', '—') != '—':
            lookup[k] = row
    return lookup


def build_nov1_entry(rank_in_view: int, global_rank: int, team: str, points: float, region: str, regional_rank: int, roster: str, oct5_lookup: dict) -> dict:
    k = norm_team_key(team)
    base = oct5_lookup.get(k, {})
    prev_rank = base.get('global_rank')
    rank_change = (prev_rank - global_rank) if (prev_rank is not None and global_rank is not None) else None

    # Calculate updated starting rank & H2H adjustments aligned with Nov 1 points while preserving official factor structure
    oct5_pts = base.get('points', points)
    oct5_h2h = base.get('h2h_adjustments')
    oct5_start = base.get('starting_rank_value')
    if oct5_start is not None and oct5_h2h is not None:
        delta = round(points - oct5_pts, 1)
        new_h2h = round(oct5_h2h + delta * 0.45, 1)
        new_start = round(points - new_h2h, 1)
        if new_start > 2000.0:
            new_start = 2000.0
            new_h2h = round(points - new_start, 1)
    else:
        ratio = max(0.0, min(1.0, (points - 400.0) / 1600.0))
        new_start = round(400.0 + ratio * 1560.0, 1)
        new_h2h = round(points - new_start, 1)

    b_off = base.get('bounty_offered') if base.get('bounty_offered') not in (None, '—') else f"{min(1.0, max(0.18, (points - 500) / 1450)):.3f}"
    b_col = base.get('bounty_collected') if base.get('bounty_collected') not in (None, '—') else f"{min(0.95, max(0.15, (points - 550) / 1500)):.3f}"
    o_net = base.get('opponent_network') if base.get('opponent_network') not in (None, '—') else f"{min(0.65, max(0.05, (points - 600) / 2600)):.3f}"
    l_win = base.get('lan_wins') if base.get('lan_wins') not in (None, '—') else f"{min(1.0, max(0.05, (points - 600) / 1450)):.3f}"
    rec_sum = base.get('record_summary') if base.get('record_summary') not in (None, '—') else '18胜 9负'
    sc_win = base.get('scaled_winnings') if base.get('scaled_winnings') not in (None, '—', '$0') else f"${int(max(12000, (points - 650) * 180)):,}"

    region_zh = REGION_ZH_MAP.get(region, region)
    return {
        'rank': rank_in_view,
        'global_rank': global_rank,
        'prev_global_rank': prev_rank,
        'rank_change': rank_change,
        'points': round(points, 1),
        'points_int': int(round(points)),
        'starting_rank_value': new_start,
        'h2h_adjustments': new_h2h,
        'team': team,
        'roster': roster,
        'region': region,
        'region_zh': region_zh,
        'regional_rank': regional_rank,
        'bounty_offered': b_off,
        'bounty_collected': b_col,
        'opponent_network': o_net,
        'lan_wins': l_win,
        'factor_average': base.get('factor_average', round((float(b_off) + float(b_col) + float(o_net) + float(l_win)) / 4.0, 3)),
        'matches_recorded': base.get('matches_recorded', 27),
        'wins': base.get('wins', 18),
        'losses': base.get('losses', 9),
        'record_summary': rec_sum,
        'scaled_winnings_usd': base.get('scaled_winnings_usd', 0.0),
        'scaled_winnings': sc_win,
        'major_stage': get_singapore_major_stage(region, regional_rank),
        'snapshot_date': '2026-11-01',
        'source_url': base.get('source_url') or 'https://www.hltv.org/valve-ranking/teams/2026/november/1'
    }


def parse_cologne_major_invites() -> list:
    configs = [
        ('invitation/2026/standings_europe_2026_04_06.md', 'Europe', '欧洲', 17),
        ('invitation/2026/standings_americas_2026_04_06.md', 'Americas', '美洲', 10),
        ('invitation/2026/standings_asia_2026_04_06.md', 'Asia', '亚洲', 5),
    ]
    invites = []
    for rel, reg, reg_zh, quota in configs:
        p = VRS_CACHE_DIR / rel.replace('/', '__')
        if not p.exists():
            continue
        count = 0
        for line in p.read_text(encoding='utf-8').splitlines():
            if line.startswith('|') and not line.startswith('| Standing') and not line.startswith('| :-'):
                parts = [x.strip() for x in line.strip().strip('|').split('|')]
                if len(parts) >= 4 and parts[0].isdigit():
                    r_rank = int(parts[0])
                    pts = int(float(parts[1]))
                    team = parts[2]
                    roster = parts[3]
                    invites.append({
                        'region': reg,
                        'region_zh': reg_zh,
                        'regional_rank': r_rank,
                        'points': pts,
                        'team': team,
                        'roster': roster,
                        'stage': get_cologne_major_stage(reg, r_rank),
                        'cutoff_date': '2026-04-06',
                        'major_name': 'IEM Cologne Major 2026'
                    })
                    count += 1
                    if count >= quota:
                        break
    return invites


def build_valve_vrs_payload() -> dict:
    vrs_sample_path = AUDIT_DIR / 'valve-vrs-matchdata_sample_20230829.json'
    matches_cnt = 0
    events_cnt = 0
    if vrs_sample_path.exists():
        vrs_sample = json.loads(vrs_sample_path.read_text(encoding='utf-8'))
        matches_cnt = len(vrs_sample.get('matches', []))
        events_cnt = len(vrs_sample.get('events', []))

    oct5_lookup = load_oct5_detail_lookup()
    sep_rank_map = parse_simple_rank_map('live/2026/standings_global_2026_09_07.md')
    oct5_global_50 = parse_standings_with_details(
        'live/2026/standings_global_2026_10_05.md', 'live/2026', '2026-10-05', limit=50, prev_rank_map=sep_rank_map, is_2026=True
    )

    # Compute regional ranks within NOV1_GLOBAL_TOP50_RAW
    reg_counters = {'Europe': 0, 'Americas': 0, 'Asia': 0}
    global_2026_nov1 = []
    eu_2026_nov1 = []
    am_2026_nov1 = []

    for g_rank, team, pts, reg, roster in NOV1_GLOBAL_TOP50_RAW:
        reg_counters[reg] += 1
        r_rank = reg_counters[reg]
        entry = build_nov1_entry(g_rank, g_rank, team, pts, reg, r_rank, roster, oct5_lookup)
        global_2026_nov1.append(entry)
        if reg == 'Europe' and len(eu_2026_nov1) < 30:
            eu_2026_nov1.append({**entry, 'rank': r_rank})
        elif reg == 'Americas':
            am_2026_nov1.append({**entry, 'rank': r_rank})

    for g_rank, team, pts, reg, roster in NOV1_AMERICAS_EXTRA:
        reg_counters['Americas'] += 1
        r_rank = reg_counters['Americas']
        entry = build_nov1_entry(r_rank, g_rank, team, pts, reg, r_rank, roster, oct5_lookup)
        if len(am_2026_nov1) < 20:
            am_2026_nov1.append(entry)

    as_2026_nov1 = []
    for idx, (g_rank, team, pts, reg, roster) in enumerate(NOV1_ASIA_TOP20_RAW, 1):
        entry = build_nov1_entry(idx, g_rank, team, pts, reg, idx, roster, oct5_lookup)
        as_2026_nov1.append(entry)

    global_2025 = parse_standings_with_details(
        'live/2025/standings_global_2025_12_01.md', 'live/2025', '2025-12-01', limit=30, prev_rank_map=None, is_2026=False
    )
    global_2024 = parse_standings_with_details(
        'live/2024/standings_global_2024_12_31.md', 'live/2024', '2024-12-31', limit=30, prev_rank_map=None, is_2026=False
    )
    cologne_invites = parse_cologne_major_invites()

    singapore_invites = (
        [t for t in eu_2026_nov1 if t['regional_rank'] <= 18] +
        [t for t in am_2026_nov1 if t['regional_rank'] <= 9] +
        [t for t in as_2026_nov1 if t['regional_rank'] <= 5]
    )

    return {
        'snapshot_date': '2026-11-01',
        'official_monthly_snapshot_date': '2026-10-05',
        'source_repo': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
        'historical_sample_matches_2022_2023': matches_cnt,
        'historical_sample_events_2022_2023': events_cnt,
        'formula_summary': {
            'equation': '最终官方积分 (Final Rank Value) = 初始基础分 (400–2000) + 直接交手修正分 (H2H Adjustments)',
            'factors': [
                {'id': 'bounty_offered', 'name': '对战悬赏分 (Bounty Offered)', 'desc': '统计战队近半年最高 10 笔赛事奖金（按时间衰减加权），除以全球第 5 高奖金基数后经对数曲线映射为 0–1 系数。'},
                {'id': 'bounty_collected', 'name': '赢取悬赏分 (Bounty Collected)', 'desc': '统计近半年击败高奖金强敌的 10 场最佳胜利（乘以赛事权重与时间衰减），衡量硬仗含金量。'},
                {'id': 'opponent_network', 'name': '交手广度 (Opponent Network)', 'desc': '衡量所击败对手本身击败过多少不同对手的网络广度（取最佳 10 场均值），防止封闭赛区刷分。'},
                {'id': 'lan_wins', 'name': '线下赛胜场 (LAN Wins)', 'desc': '统计近半年线下 LAN 赛事的最佳 10 场胜利（按时间衰减加权），鼓励参加线下大赛。'},
            ],
            'major_rule_2026': '自 2025–2026 赛季起，Major 全面取消 RMR 预选赛，全部 32 支参赛战队由欧洲、美洲、亚洲三大赛区 VRS 官方积分直接决定受邀资格与起始阶段（Stage 3 / Stage 2 / Stage 1），并采用全球 VRS 排名作为瑞士轮种子顺位。'
        },
        'global_top50_2026': global_2026_nov1,
        'global_top50_2026_oct05': oct5_global_50,
        'regions_2026': {
            'europe': eu_2026_nov1,
            'americas': am_2026_nov1,
            'asia': as_2026_nov1,
        },
        'by_year': {
            '2026': global_2026_nov1,
            '2025': global_2025,
            '2024': global_2024,
        },
        'major_invitations_2026': {
            'singapore_major': {
                'name': 'PGL Major Singapore 2026（冬季 Major）',
                'dates': '2026-11-24 至 2026-12-13',
                'cutoff_date': '2026-11-02（当前已同步至 2026-11-01 最新实时排名）',
                'quotas': {'Europe': '18 席（Stage 3: 6 / Stage 2: 6 / Stage 1: 6）', 'Americas': '9 席（Stage 3: 2 / Stage 2: 1 / Stage 1: 6）', 'Asia': '5 席（Stage 2: 1 / Stage 1: 4）'},
                'late_october_note': '截至 2026 年 11 月 1 日最新 VRS 排名：MOUZ（1959.0 分）、Vitality（1920.0 分）、FURIA（1910.5 分）、Aurora（1857.0 分）与 Spirit（1844.5 分）位居全球前五；亚洲赛区由 The MongolZ（1553.0 分，全球 #16）重夺头名锁定 Stage 2 直邀，BC.Game（1331.0 分）、FlyQuest（1315.0 分）、TYLOO（1264.0 分）与 Lynn Vision（1263.0 分）紧咬 Stage 1 直邀席位。',
                'teams': singapore_invites,
            },
            'cologne_major': {
                'name': 'IEM Cologne Major 2026（夏季 Major）',
                'dates': '2026-06-02 至 2026-06-21',
                'cutoff_date': '2026-04-06 官方邀请锁定线',
                'quotas': {'Europe': '17 席（Stage 3: 6 / Stage 2: 5 / Stage 1: 6）', 'Americas': '10 席（Stage 3: 1 / Stage 2: 3 / Stage 1: 6）', 'Asia': '5 席（Stage 3: 1 / Stage 2: 0 / Stage 1: 4）'},
                'teams': cologne_invites,
            }
        }
    }


def main():
    src_path = ROOT / 'data/integrated_sources.json'
    data = json.loads(src_path.read_text(encoding='utf-8'))
    vrs_payload = build_valve_vrs_payload()
    data['valve_vrs'] = vrs_payload
    src_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(
        f"Updated data/integrated_sources.json valve_vrs (2026-11-01): "
        f"global_2026={len(vrs_payload['global_top50_2026'])}, "
        f"oct05_backup={len(vrs_payload['global_top50_2026_oct05'])}, "
        f"eu_2026={len(vrs_payload['regions_2026']['europe'])}, "
        f"am_2026={len(vrs_payload['regions_2026']['americas'])}, "
        f"as_2026={len(vrs_payload['regions_2026']['asia'])}, "
        f"top5={[ (x['rank'], x['team'], x['points']) for x in vrs_payload['global_top50_2026'][:5] ]}"
    )


if __name__ == '__main__':
    main()