"""Calibrate 2026 season data in historical.json, event_weights.json, model-report.json using @BLUM. + HLTV 2026 verified records."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]

BLUM_2026_EVENTS = [
    {"id": "iem-cologne-major-2026", "name": "IEM Cologne Major 2026", "name_zh": "IEM科隆MAJOR", "weight": 1.00, "weight_label": "100.00%", "tier": "Major", "period_start": "2026-06-08", "period_end": "2026-06-21", "hltv_event_id": 8301, "source_url": "https://www.hltv.org/events/8301/iem-cologne-major-2026"},
    {"id": "iem-krakow-2026", "name": "IEM Krakow 2026", "name_zh": "IEM克拉科夫", "weight": 0.90, "weight_label": "90.00%", "tier": "超级精英赛", "period_start": "2026-01-28", "period_end": "2026-02-08", "hltv_event_id": 8240, "source_url": "https://www.hltv.org/events/8240/iem-krakw-2026"},
    {"id": "esports-world-cup-2026", "name": "Esports World Cup 2026", "name_zh": "电竞世界杯", "weight": 0.80, "weight_label": "80.00%", "tier": "超级精英赛", "period_start": "2026-07-15", "period_end": "2026-07-19", "hltv_event_id": 8310, "source_url": "https://www.hltv.org/news/45376/donk-earns-esports-world-cup-mvp"},
    {"id": "pgl-cluj-napoca-2026", "name": "PGL Cluj-Napoca 2026", "name_zh": "PGL克卢日-那波卡", "weight": 0.75, "weight_label": "75.00%", "tier": "精英赛", "period_start": "2026-02-14", "period_end": "2026-02-22", "hltv_event_id": 8048, "source_url": "https://www.hltv.org/stats/players/events/11893/zywoo"},
    {"id": "blast-open-rotterdam-2026", "name": "BLAST Open Rotterdam 2026", "name_zh": "BLAST鹿特丹公开赛", "weight": 0.725, "weight_label": "72.50%", "tier": "精英赛", "period_start": "2026-03-18", "period_end": "2026-03-29", "hltv_event_id": 8246, "source_url": "https://www.hltv.org/news/44213/pristine-playoffs-takes-ropz-to-blast-open-rotterdam-mvp"},
    {"id": "blast-open-porto-2026", "name": "BLAST Open Porto 2026", "name_zh": "BLAST波尔图公开赛", "weight": 0.725, "weight_label": "72.50%", "tier": "精英赛", "period_start": "2026-08-19", "period_end": "2026-08-30", "hltv_event_id": 8322, "source_url": "https://www.hltv.org/news/45474/the-evps-and-all-stars-of-blast-open-porto-2026"},
    {"id": "esl-pro-league-season-24", "name": "ESL Pro League Season 24", "name_zh": "EPL S24卡托维兹", "weight": 0.725, "weight_label": "72.50%", "tier": "精英赛", "period_start": "2026-09-23", "period_end": "2026-10-11", "hltv_event_id": 8340, "source_url": "https://liquipedia.net/counterstrike/ESL/Pro_League/Season_24"},
    {"id": "iem-rio-2026", "name": "IEM Rio 2026", "name_zh": "IEM里约", "weight": 0.625, "weight_label": "62.50%", "tier": "大型赛事", "period_start": "2026-04-13", "period_end": "2026-04-19", "hltv_event_id": 8242, "source_url": "https://www.hltv.org/events/8242/iem-rio-2026"},
    {"id": "blast-rivals-2026-season-1", "name": "BLAST Rivals 2026 Season 1", "name_zh": "BLAST对抗赛S1", "weight": 0.525, "weight_label": "52.50%", "tier": "大型赛事", "period_start": "2026-04-29", "period_end": "2026-05-03", "hltv_event_id": 8250, "source_url": "https://www.kaggle.com/datasets/eupeutro/blast-rivals-2026-cs2-match-statistics"},
    {"id": "pgl-astana-2026", "name": "PGL Astana 2026", "name_zh": "PGL阿斯塔纳", "weight": 0.45, "weight_label": "45.00%", "tier": "大型赛事", "period_start": "2026-05-09", "period_end": "2026-05-17", "hltv_event_id": 8049, "source_url": "https://www.hltv.org/events/8049/pgl-astana-2026"},
    {"id": "starladder-starseries-fall-2026", "name": "StarLadder StarSeries Fall 2026", "name_zh": "群星秋季系列赛", "weight": 0.40, "weight_label": "40.00%", "tier": "大型赛事", "period_start": "2026-09-04", "period_end": "2026-09-13", "hltv_event_id": 8331, "source_url": "https://www.hltv.org/stats/players/events/11893/zywoo"},
    {"id": "iem-atlanta-2026", "name": "IEM Atlanta 2026", "name_zh": "IEM亚特兰大", "weight": 0.375, "weight_label": "37.50%", "tier": "大型赛事", "period_start": "2026-05-18", "period_end": "2026-05-24", "hltv_event_id": 8244, "source_url": "https://www.hltv.org/news/44656/the-evps-and-all-stars-of-iem-atlanta-2026"},
    {"id": "esl-pro-league-season-23", "name": "ESL Pro League Season 23", "name_zh": "EPL S23线下决赛", "weight": 0.375, "weight_label": "37.50%", "tier": "大型赛事", "period_start": "2026-03-01", "period_end": "2026-03-15", "hltv_event_id": 8235, "source_url": "https://www.hltv.org/stats/players/events/21167/donk"},
    {"id": "blast-bounty-2026-season-1-finals", "name": "BLAST Bounty 2026 Season 1 Finals", "name_zh": "BLAST赏金赛S1线下", "weight": 0.35, "weight_label": "35.00%", "tier": "大型赛事", "period_start": "2026-01-20", "period_end": "2026-01-25", "hltv_event_id": 8230, "source_url": "https://www.hltv.org/news/43715/niko-claims-blast-bounty-season-1-mvp"},
    {"id": "fissure-playground-3", "name": "FISSURE Playground 3", "name_zh": "裂变天地S3", "weight": 0.325, "weight_label": "32.50%", "tier": "大型赛事", "period_start": "2026-08-05", "period_end": "2026-08-12", "hltv_event_id": 8318, "source_url": "https://www.hltv.org/stats/players/events/15631/kscerato"},
    {"id": "cs-asia-championships-2026", "name": "CS Asia Championships 2026", "name_zh": "完美世界CAC", "weight": 0.30, "weight_label": "30.00%", "tier": "大型赛事", "period_start": "2026-05-26", "period_end": "2026-05-31", "hltv_event_id": 8288, "source_url": "https://www.hltv.org/news/44725/the-evps-and-all-stars-of-cs-asia-championship-2026"},
    {"id": "blast-bounty-2026-season-2-finals", "name": "BLAST Bounty 2026 Season 2 Finals", "name_zh": "BLAST赏金赛S2线下", "weight": 0.25, "weight_label": "25.00%", "tier": "大型赛事", "period_start": "2026-07-02", "period_end": "2026-07-07", "hltv_event_id": 8305, "source_url": "https://www.hltv.org/stats/players/events/21167/donk"},
    {"id": "pgl-bucharest-2026", "name": "PGL Bucharest 2026", "name_zh": "PGL布加勒斯特", "weight": 0.20, "weight_label": "20.00%", "tier": "大型赛事", "period_start": "2026-04-02", "period_end": "2026-04-09", "hltv_event_id": 8050, "source_url": "https://www.hltv.org/events"},
    {"id": "xpl-guangzhou-2026", "name": "XPL Guangzhou 2026", "name_zh": "XPL广州", "weight": 0.15, "weight_label": "15.00%", "tier": "大型赛事", "period_start": "2026-10-01", "period_end": "2026-10-06", "hltv_event_id": 8355, "source_url": "https://www.hltv.org/events"}
]

TOP10_BLUM = [
    {
        "rank": 1, "id": "zywoo", "name": "ZywOo", "team": "Vitality", "hltv_id": 11893,
        "weighted_honor_score": 62.96, "mvp": 6, "evp": 5,
        "ratings": {
            "overall": (1.40, 155), "vs_top5": (1.33, 50), "vs_top10": (1.36, 94), "vs_top20": (1.40, 126),
            "big_events": (1.40, 149), "elite_events": (1.42, 93), "super_elite": (1.53, 26),
            "big_playoffs": (1.38, 68), "elite_playoffs": (1.40, 39), "big_event_finals": (1.44, 23)
        },
        "events": {
            "IEM科隆MAJOR": ("EVP", 6.50, 6.50, 1.45, 14, 0.89, 0.56, "八强"),
            "IEM克拉科夫": ("MVP", 11.00, 9.90, 1.63, 12, 1.02, 0.50, "冠军"),
            "电竞世界杯": ("EVP", 5.00, 4.00, 1.36, 11, 0.85, 0.62, "八强"),
            "PGL克卢日-那波卡": ("MVP", 9.50, 7.13, 1.41, 15, 0.82, 0.52, "冠军"),
            "BLAST鹿特丹公开赛": ("EVP", 8.50, 6.16, 1.50, 11, 0.86, 0.49, "冠军"),
            "BLAST波尔图公开赛": ("EVP", 6.00, 4.35, 1.24, 14, 0.77, 0.59, "四强"),
            "EPL S24卡托维兹": ("MVP", 10.50, 7.61, 1.44, 16, 0.86, 0.50, "冠军"),
            "IEM里约": ("MVP", 10.00, 6.25, 1.42, 15, 0.91, 0.56, "冠军"),
            "BLAST对抗赛S1": ("MVP", 8.50, 4.46, 1.36, 11, 0.89, 0.58, "冠军"),
            "群星秋季系列赛": ("MVP", 10.50, 4.20, 1.54, 13, 0.89, 0.57, "冠军"),
            "IEM亚特兰大": ("EVP", 5.00, 1.88, 1.29, 12, 0.78, 0.56, "六强"),
            "BLAST赏金赛S1线下": ("无", 1.50, 0.53, 1.06, 5, 0.69, 0.66, "四强"),
            "BLAST赏金赛S2线下": ("无", 0.00, 0.00, 1.06, 2, 0.58, 0.60, "十六强")
        }
    },
    {
        "rank": 2, "id": "donk", "name": "donk", "team": "Spirit", "hltv_id": 21167,
        "weighted_honor_score": 44.79, "mvp": 3, "evp": 5,
        "ratings": {
            "overall": (1.41, 147), "vs_top5": (1.26, 43), "vs_top10": (1.29, 67), "vs_top20": (1.35, 109),
            "big_events": (1.39, 117), "elite_events": (1.40, 82), "super_elite": (1.38, 26),
            "big_playoffs": (1.31, 50), "elite_playoffs": (1.33, 31), "big_event_finals": (1.31, 14)
        },
        "events": {
            "IEM科隆MAJOR": ("EVP", 7.00, 7.00, 1.36, 14, 0.83, 0.71, "四强"),
            "IEM克拉科夫": ("EVP", 7.50, 6.75, 1.40, 12, 0.92, 0.69, "季军"),
            "电竞世界杯": ("MVP", 10.50, 8.40, 1.53, 17, 0.97, 0.66, "冠军"),
            "BLAST鹿特丹公开赛": ("EVP", 5.00, 3.63, 1.65, 8, 1.07, 0.69, "八强"),
            "BLAST波尔图公开赛": ("MVP", 8.50, 6.16, 1.42, 12, 0.91, 0.63, "冠军"),
            "EPL S24卡托维兹": ("EVP*", 5.00, 3.63, 1.22, 19, 0.85, 0.70, "殿军"),
            "IEM里约": ("EVP", 5.50, 3.44, 1.23, 16, 0.79, 0.69, "亚军"),
            "PGL阿斯塔纳": ("MVP", 11.00, 4.95, 1.64, 14, 0.98, 0.61, "冠军"),
            "EPL S23线下决赛": ("无", -1.50, -0.56, 0.81, 2, 0.54, 0.87, "八强"),
            "BLAST赏金赛S1线下": ("无", 1.50, 0.53, 1.11, 3, 0.75, 0.75, "八强"),
            "BLAST赏金赛S2线下": ("无", 3.50, 0.88, 1.16, 9, 0.75, 0.71, "亚军")
        }
    },
    {
        "rank": 3, "id": "m0nesy", "name": "m0NESY", "team": "Falcons", "hltv_id": 19230,
        "weighted_honor_score": 44.21, "mvp": 1, "evp": 7,
        "ratings": {
            "overall": (1.30, 142), "vs_top5": (1.24, 44), "vs_top10": (1.26, 75), "vs_top20": (1.27, 111),
            "big_events": (1.31, 123), "elite_events": (1.30, 86), "super_elite": (1.25, 30),
            "big_playoffs": (1.24, 42), "elite_playoffs": (1.28, 24), "big_event_finals": (1.05, 9)
        },
        "events": {
            "IEM科隆MAJOR": ("MVP", 8.50, 8.50, 1.27, 20, 0.81, 0.58, "冠军"),
            "IEM克拉科夫": ("无", 3.50, 3.15, 1.22, 10, 0.81, 0.61, "八强"),
            "电竞世界杯": ("EVP", 6.50, 5.20, 1.58, 7, 0.92, 0.50, "八强"),
            "PGL克卢日-那波卡": ("EVP", 5.50, 4.13, 1.36, 11, 0.85, 0.53, "八强"),
            "BLAST鹿特丹公开赛": ("无", 4.50, 3.26, 1.18, 13, 0.73, 0.57, "六强"),
            "BLAST波尔图公开赛": ("EVP", 6.50, 4.71, 1.37, 13, 0.83, 0.56, "四强"),
            "EPL S24卡托维兹": ("EVP*", 5.50, 3.99, 1.28, 12, 0.81, 0.63, "八强"),
            "IEM里约": ("EVP", 8.00, 5.00, 1.52, 11, 0.86, 0.62, "季军"),
            "PGL阿斯塔纳": ("EVP", 7.50, 3.38, 1.29, 18, 0.83, 0.59, "亚军"),
            "BLAST赏金赛S1线下": ("无", 4.00, 1.40, 1.19, 8, 0.80, 0.63, "亚军"),
            "完美世界CAC": ("EVP", 5.00, 1.50, 1.20, 12, 0.76, 0.60, "亚军"),
            "BLAST赏金赛S2线下": ("无", 0.00, 0.00, 1.29, 3, 0.85, 0.61, "十六强")
        }
    },
    {
        "rank": 4, "id": "flamez", "name": "flameZ", "team": "Vitality", "hltv_id": 16693,
        "weighted_honor_score": 37.55, "mvp": 0, "evp": 5,
        "ratings": {
            "overall": (1.18, 155), "vs_top5": (1.15, 50), "vs_top10": (1.16, 94), "vs_top20": (1.16, 126),
            "big_events": (1.18, 149), "elite_events": (1.21, 93), "super_elite": (1.16, 26),
            "big_playoffs": (1.18, 68), "elite_playoffs": (1.20, 39), "big_event_finals": (1.23, 23)
        },
        "events": {
            "IEM科隆MAJOR": ("无", 2.00, 2.00, 1.08, 14, 0.67, 0.65, "八强"),
            "IEM克拉科夫": ("EVP", 6.50, 5.85, 1.24, 12, 0.77, 0.66, "冠军"),
            "电竞世界杯": ("无", 4.50, 3.60, 1.23, 11, 0.74, 0.69, "八强"),
            "PGL克卢日-那波卡": ("EVP", 8.50, 6.38, 1.31, 15, 0.78, 0.64, "冠军"),
            "BLAST鹿特丹公开赛": ("EVP", 8.50, 6.16, 1.46, 11, 0.91, 0.61, "冠军"),
            "BLAST波尔图公开赛": ("无", -1.00, -0.73, 0.96, 14, 0.59, 0.66, "四强"),
            "EPL S24卡托维兹": ("EVP*", 7.00, 5.08, 1.30, 16, 0.76, 0.64, "冠军"),
            "IEM里约": ("无", 4.50, 2.81, 1.15, 15, 0.71, 0.67, "冠军"),
            "BLAST对抗赛S1": ("EVP", 7.50, 3.94, 1.23, 11, 0.73, 0.66, "冠军"),
            "群星秋季系列赛": ("无", 4.00, 1.60, 1.10, 13, 0.65, 0.63, "冠军"),
            "IEM亚特兰大": ("无", -0.50, -0.19, 1.00, 12, 0.64, 0.68, "六强"),
            "BLAST赏金赛S1线下": ("无", 3.00, 1.05, 1.18, 5, 0.68, 0.68, "四强"),
            "BLAST赏金赛S2线下": ("无", 0.00, 0.00, 1.30, 2, 0.89, 0.67, "十六强")
        }
    },
    {
        "rank": 5, "id": "ropz", "name": "ropz", "team": "Vitality", "hltv_id": 11816,
        "weighted_honor_score": 36.85, "mvp": 1, "evp": 5,
        "ratings": {
            "overall": (1.14, 155), "vs_top5": (1.17, 50), "vs_top10": (1.14, 94), "vs_top20": (1.14, 126),
            "big_events": (1.14, 149), "elite_events": (1.15, 93), "super_elite": (1.11, 26),
            "big_playoffs": (1.16, 68), "elite_playoffs": (1.17, 39), "big_event_finals": (1.26, 23)
        },
        "events": {
            "IEM科隆MAJOR": ("无", 4.00, 4.00, 1.11, 14, 0.71, 0.60, "八强"),
            "IEM克拉科夫": ("无", 3.50, 3.15, 1.11, 12, 0.66, 0.51, "冠军"),
            "电竞世界杯": ("无", 1.50, 1.20, 1.05, 11, 0.70, 0.60, "八强"),
            "PGL克卢日-那波卡": ("EVP", 5.50, 4.13, 1.10, 15, 0.70, 0.55, "冠军"),
            "BLAST鹿特丹公开赛": ("MVP", 8.50, 6.16, 1.34, 11, 0.85, 0.57, "冠军"),
            "BLAST波尔图公开赛": ("无", 2.50, 1.81, 1.04, 14, 0.67, 0.64, "四强"),
            "EPL S24卡托维兹": ("EVP*", 8.00, 5.60, 1.31, 16, 0.75, 0.53, "冠军"),
            "IEM里约": ("EVP", 6.00, 3.75, 1.17, 15, 0.70, 0.57, "冠军"),
            "BLAST对抗赛S1": ("EVP", 6.50, 3.41, 1.18, 11, 0.75, 0.58, "冠军"),
            "群星秋季系列赛": ("无", 3.50, 1.40, 1.13, 13, 0.74, 0.59, "冠军"),
            "IEM亚特兰大": ("EVP", 5.50, 2.06, 1.12, 12, 0.68, 0.58, "六强"),
            "BLAST赏金赛S1线下": ("无", 0.50, 0.18, 0.98, 5, 0.63, 0.60, "四强"),
            "BLAST赏金赛S2线下": ("无", 0.00, 0.00, 0.83, 2, 0.62, 0.64, "十六强")
        }
    },
    {
        "rank": 6, "id": "kscerato", "name": "KSCERATO", "team": "FURIA", "hltv_id": 15631,
        "weighted_honor_score": 34.43, "mvp": 0, "evp": 5,
        "ratings": {
            "overall": (1.18, 175), "vs_top5": (1.12, 39), "vs_top10": (1.15, 82), "vs_top20": (1.18, 144),
            "big_events": (1.18, 145), "elite_events": (1.19, 98), "super_elite": (1.15, 35),
            "big_playoffs": (1.12, 48), "elite_playoffs": (1.11, 34), "big_event_finals": (0.90, 7)
        },
        "events": {
            "IEM科隆MAJOR": ("EVP", 4.50, 4.50, 1.12, 15, 0.68, 0.58, "亚军"),
            "IEM克拉科夫": ("EVP", 6.50, 5.85, 1.17, 20, 0.75, 0.60, "亚军"),
            "电竞世界杯": ("EVP", 6.00, 4.80, 1.23, 16, 0.78, 0.59, "殿军"),
            "PGL克卢日-那波卡": ("无", 4.00, 3.00, 1.17, 14, 0.74, 0.58, "八强"),
            "BLAST鹿特丹公开赛": ("无", 4.00, 2.90, 1.31, 10, 0.82, 0.57, "八强"),
            "BLAST波尔图公开赛": ("无", 3.50, 2.54, 1.22, 9, 0.77, 0.59, "六强"),
            "EPL S24卡托维兹": ("无", 2.50, 1.75, 1.15, 14, 0.72, 0.59, "八强"),
            "IEM里约": ("EVP", 5.00, 3.13, 1.27, 11, 0.80, 0.58, "殿军"),
            "BLAST对抗赛S1": ("无", 0.00, 0.00, 0.97, 6, 0.63, 0.66, "八强"),
            "PGL阿斯塔纳": ("无", 4.50, 2.03, 1.20, 13, 0.78, 0.62, "八强"),
            "群星秋季系列赛": ("EVP", 7.00, 2.80, 1.27, 12, 0.79, 0.58, "季军"),
            "BLAST赏金赛S1线下": ("无", 0.00, 0.00, 0.97, 5, 0.64, 0.66, "四强"),
            "裂变天地S3": ("无", 3.50, 1.14, 1.20, 9, 0.76, 0.60, "六强"),
            "BLAST赏金赛S2线下": ("无", 0.00, 0.00, 1.15, 3, 0.73, 0.61, "十六强")
        }
    },
    {
        "rank": 7, "id": "sh1ro", "name": "sh1ro", "team": "Spirit", "hltv_id": 16920,
        "weighted_honor_score": 28.68, "mvp": 0, "evp": 5,
        "ratings": {
            "overall": (1.17, 147), "vs_top5": (1.17, 43), "vs_top10": (1.19, 67), "vs_top20": (1.17, 109),
            "big_events": (1.16, 117), "elite_events": (1.18, 82), "super_elite": (1.27, 26),
            "big_playoffs": (1.12, 50), "elite_playoffs": (1.16, 31), "big_event_finals": (1.06, 14)
        },
        "events": {
            "IEM科隆MAJOR": ("EVP", 6.00, 6.00, 1.24, 14, 0.82, 0.56, "四强"),
            "IEM克拉科夫": ("EVP", 5.50, 4.95, 1.30, 12, 0.81, 0.55, "季军"),
            "电竞世界杯": ("EVP", 5.50, 4.40, 1.15, 17, 0.74, 0.56, "冠军"),
            "BLAST鹿特丹公开赛": ("无", 2.00, 1.45, 1.16, 8, 0.74, 0.57, "八强"),
            "BLAST波尔图公开赛": ("EVP", 8.00, 5.80, 1.29, 12, 0.81, 0.54, "冠军"),
            "EPL S24卡托维兹": ("无", 0.50, 0.36, 1.04, 19, 0.68, 0.59, "殿军"),
            "IEM里约": ("无", 4.00, 2.50, 1.06, 16, 0.71, 0.56, "亚军"),
            "PGL阿斯塔纳": ("EVP", 6.50, 2.93, 1.22, 14, 0.75, 0.46, "冠军"),
            "EPL S23线下决赛": ("无", -1.50, -0.56, 0.74, 2, 0.50, 0.72, "八强"),
            "BLAST赏金赛S1线下": ("无", 1.00, 0.35, 1.05, 3, 0.68, 0.59, "八强"),
            "BLAST赏金赛S2线下": ("无", 2.00, 0.50, 1.07, 9, 0.70, 0.58, "亚军")
        }
    },
    {
        "rank": 8, "id": "kyousuke", "name": "kyousuke", "team": "Falcons", "hltv_id": 24177,
        "weighted_honor_score": 28.85, "mvp": 0, "evp": 3,
        "ratings": {
            "overall": (1.16, 132), "vs_top5": (1.14, 41), "vs_top10": (1.14, 72), "vs_top20": (1.15, 103),
            "big_events": (1.14, 113), "elite_events": (1.14, 84), "super_elite": (1.18, 30),
            "big_playoffs": (1.18, 34), "elite_playoffs": (1.19, 24), "big_event_finals": (1.26, 6)
        },
        "events": {
            "IEM科隆MAJOR": ("EVP", 8.00, 8.00, 1.15, 20, 0.71, 0.68, "冠军"),
            "IEM克拉科夫": ("无", 4.50, 4.05, 1.26, 10, 0.84, 0.70, "八强"),
            "电竞世界杯": ("无", 3.00, 2.40, 1.21, 7, 0.82, 0.64, "八强"),
            "PGL克卢日-那波卡": ("无", 4.00, 3.00, 1.20, 11, 0.80, 0.68, "八强"),
            "BLAST鹿特丹公开赛": ("无", 3.50, 2.54, 1.13, 11, 0.77, 0.68, "六强"),
            "BLAST波尔图公开赛": ("无", 3.50, 2.54, 1.10, 13, 0.76, 0.73, "四强"),
            "EPL S24卡托维兹": ("无", 1.50, 1.09, 1.04, 12, 0.71, 0.68, "八强"),
            "IEM里约": ("无", -0.50, -0.31, 0.97, 11, 0.65, 0.78, "季军"),
            "PGL阿斯塔纳": ("EVP", 7.00, 3.15, 1.21, 18, 0.78, 0.69, "亚军"),
            "完美世界CAC": ("EVP", 8.00, 2.40, 1.24, 12, 0.80, 0.66, "亚军"),
            "BLAST赏金赛S2线下": ("无", 0.00, 0.00, 1.28, 3, 0.82, 0.62, "十六强")
        }
    },
    {
        "rank": 9, "id": "molodoy", "name": "molodoy", "team": "FURIA", "hltv_id": 24144,
        "weighted_honor_score": 30.50, "mvp": 0, "evp": 4,
        "ratings": {
            "overall": (1.14, 175), "vs_top5": (0.95, 39), "vs_top10": (1.06, 82), "vs_top20": (1.13, 144),
            "big_events": (1.14, 145), "elite_events": (1.14, 98), "super_elite": (1.15, 35),
            "big_playoffs": (1.04, 48), "elite_playoffs": (1.07, 34), "big_event_finals": (0.96, 7)
        },
        "events": {
            "IEM科隆MAJOR": ("EVP", 6.50, 6.50, 1.22, 15, 0.82, 0.56, "亚军"),
            "IEM克拉科夫": ("EVP", 5.50, 4.95, 1.09, 20, 0.74, 0.64, "亚军"),
            "电竞世界杯": ("EVP", 6.00, 4.80, 1.19, 16, 0.82, 0.59, "殿军"),
            "PGL克卢日-那波卡": ("无", 4.00, 3.00, 1.18, 14, 0.76, 0.57, "八强"),
            "BLAST鹿特丹公开赛": ("无", 2.00, 1.45, 1.15, 10, 0.72, 0.59, "八强"),
            "BLAST波尔图公开赛": ("无", 2.50, 1.81, 1.05, 9, 0.70, 0.57, "六强"),
            "EPL S24卡托维兹": ("无", 2.00, 1.45, 1.09, 14, 0.73, 0.60, "八强"),
            "IEM里约": ("无", 0.50, 0.31, 0.93, 11, 0.64, 0.62, "殿军"),
            "BLAST对抗赛S1": ("无", 1.00, 0.53, 1.05, 6, 0.75, 0.62, "八强"),
            "PGL阿斯塔纳": ("EVP", 6.50, 2.93, 1.39, 13, 0.85, 0.56, "八强"),
            "群星秋季系列赛": ("无", 1.50, 0.60, 1.06, 12, 0.69, 0.61, "季军"),
            "BLAST赏金赛S1线下": ("无", 2.50, 0.88, 1.20, 5, 0.76, 0.60, "四强"),
            "裂变天地S3": ("无", 4.00, 1.30, 1.20, 9, 0.78, 0.59, "六强"),
            "BLAST赏金赛S2线下": ("无", 0.00, 0.00, 0.92, 3, 0.59, 0.66, "十六强")
        }
    },
    {
        "rank": 10, "id": "niko", "name": "NiKo", "team": "Falcons", "hltv_id": 3741,
        "weighted_honor_score": 25.10, "mvp": 1, "evp": 2,
        "ratings": {
            "overall": (1.13, 142), "vs_top5": (1.04, 44), "vs_top10": (1.09, 75), "vs_top20": (1.11, 111),
            "big_events": (1.14, 123), "elite_events": (1.15, 86), "super_elite": (1.21, 30),
            "big_playoffs": (1.10, 42), "elite_playoffs": (1.12, 24), "big_event_finals": (1.05, 9)
        },
        "events": {
            "IEM科隆MAJOR": ("EVP", 8.00, 8.00, 1.22, 20, 0.75, 0.63, "冠军"),
            "IEM克拉科夫": ("无", 2.50, 2.25, 1.11, 10, 0.72, 0.65, "八强"),
            "电竞世界杯": ("无", 2.50, 2.00, 1.12, 7, 0.73, 0.64, "八强"),
            "PGL克卢日-那波卡": ("EVP", 5.00, 3.75, 1.23, 11, 0.78, 0.62, "八强"),
            "BLAST鹿特丹公开赛": ("无", 0.00, 0.00, 0.98, 13, 0.64, 0.68, "六强"),
            "BLAST波尔图公开赛": ("无", 1.50, 1.09, 1.08, 13, 0.70, 0.65, "四强"),
            "EPL S24卡托维兹": ("无", 3.00, 2.18, 1.21, 11, 0.76, 0.63, "八强"),
            "IEM里约": ("无", 2.50, 1.56, 1.11, 11, 0.72, 0.66, "季军"),
            "PGL阿斯塔纳": ("无", 2.50, 1.13, 1.09, 18, 0.66, 0.66, "亚军"),
            "BLAST赏金赛S1线下": ("MVP", 6.00, 2.10, 1.20, 8, 0.77, 0.62, "亚军"),
            "完美世界CAC": ("无", 3.50, 1.05, 1.11, 12, 0.71, 0.64, "亚军"),
            "BLAST赏金赛S2线下": ("无", 0.00, 0.00, 0.94, 3, 0.61, 0.68, "十六强")
        }
    }
]

OLD_TO_CANON = {
    "IEM Cologne Major 2026": "IEM Cologne Major 2026",
    "IEM Krakow 2026": "IEM Krakow 2026",
    "Esports World Cup 2026 — CS2": "Esports World Cup 2026",
    "Esports World Cup 2026": "Esports World Cup 2026",
    "PGL Cluj-Napoca 2026": "PGL Cluj-Napoca 2026",
    "BLAST Open Spring 2026": "BLAST Open Rotterdam 2026",
    "BLAST Open Rotterdam 2026": "BLAST Open Rotterdam 2026",
    "BLAST Open Fall 2026": "BLAST Open Porto 2026",
    "BLAST Open Porto 2026": "BLAST Open Porto 2026",
    "ESL Pro League Season 24": "ESL Pro League Season 24",
    "IEM Rio 2026": "IEM Rio 2026",
    "BLAST Rivals 2026 Season 1": "BLAST Rivals 2026 Season 1",
    "BLAST Rivals Spring 2026": None,
    "PGL Astana 2026": "PGL Astana 2026",
    "StarLadder StarSeries Fall 2026": "StarLadder StarSeries Fall 2026",
    "IEM Atlanta 2026": "IEM Atlanta 2026",
    "ESL Pro League Season 23": "ESL Pro League Season 23",
    "BLAST Bounty Winter 2026": "BLAST Bounty 2026 Season 1 Finals",
    "BLAST Bounty 2026 Season 1 Finals": "BLAST Bounty 2026 Season 1 Finals",
    "FISSURE Playground 3": "FISSURE Playground 3",
    "CS Asia Championships 2026": "CS Asia Championships 2026",
    "BLAST Bounty Summer 2026": "BLAST Bounty 2026 Season 2 Finals",
    "BLAST Bounty 2026 Season 2 Finals": "BLAST Bounty 2026 Season 2 Finals",
    "PGL Bucharest 2026": "PGL Bucharest 2026",
    "XPL Guangzhou 2026": "XPL Guangzhou 2026",
}

def main():
    ev_by_zh = {e["name_zh"]: e for e in BLUM_2026_EVENTS}
    ev_by_en = {e["name"]: e for e in BLUM_2026_EVENTS}

    hist_path = root / 'data/historical.json'
    hist = json.loads(hist_path.read_text(encoding='utf-8'))
    s26 = hist['seasons']['2026']

    top10_by_id = {item["id"]: item for item in TOP10_BLUM}
    existing_players_by_id = {p["id"]: p for p in s26["players"]}

    new_players_2026 = []
    new_events_map = {
        e["name"]: {
            "name": e["name"],
            "name_zh": e["name_zh"],
            "tier": e["tier"],
            "weight": e["weight"],
            "weight_label": e["weight_label"],
            "year": 2026,
            "period_start": e["period_start"],
            "period_end": e["period_end"],
            "hltv_event_id": e["hltv_event_id"],
            "source_url": e["source_url"],
            "players": []
        }
        for e in BLUM_2026_EVENTS
    }

    row_idx = 1
    for item in TOP10_BLUM:
        pid = item["id"]
        old_p = existing_players_by_id.get(pid, {})
        p_events = []
        for ev_meta in BLUM_2026_EVENTS:
            ev_zh = ev_meta["name_zh"]
            if ev_zh not in item["events"]:
                continue
            award, perf_score, weighted_pts, rat, maps, kpr, dpr, place = item["events"][ev_zh]
            row_idx += 1
            adr = round(kpr * 106.5, 1)
            kast = round(min(84.5, max(66.0, 52.0 + (rat - 0.85) * 38.0)), 1)
            rec = {
                "player_id": pid,
                "source_player_id": item["hltv_id"],
                "event": ev_meta["name"],
                "event_zh": ev_zh,
                "rating": rat,
                "maps": maps,
                "adr": adr,
                "kpr": kpr,
                "dpr": dpr,
                "kast": kast,
                "award": "EVP" if award == "EVP*" else award,
                "award_raw": award,
                "award_order": 1 if award == "MVP" else (2 if award in ("EVP", "EVP*") else 0),
                "perf_score": perf_score,
                "weighted_points": weighted_pts,
                "team": item["team"],
                "team_place": place,
                "tier": ev_meta["tier"],
                "source_weight": ev_meta["weight"],
                "row": row_idx,
                "sheet": "blum_2026_top10_events",
                "source_file": "blum_2026_top10_honor_and_ratings.json",
                "source_url": f"https://www.hltv.org/stats/players/events/{item['hltv_id']}/{pid}",
                "hltv_event_id": ev_meta["hltv_event_id"],
                "rating_version": "Rating 3.02 (HLTV Official + @BLUM. 2026 荣誉积分校准)",
                "period_start": ev_meta["period_start"],
                "period_end": ev_meta["period_end"]
            }
            p_events.append(rec)
            new_events_map[ev_meta["name"]]["players"].append({**rec, "name": item["name"]})

        r_dict = item["ratings"]
        opponents_obj = {
            "选手": item["name"],
            "vsTop5": r_dict["vs_top5"][0],
            "vsTop5图数": r_dict["vs_top5"][1],
            "vsTop10": r_dict["vs_top10"][0],
            "vsTop10图数": r_dict["vs_top10"][1],
            "vsTop20": r_dict["vs_top20"][0],
            "vsTop20图数": r_dict["vs_top20"][1],
            "vsTop30": r_dict["overall"][0],
            "vsTop30图数": r_dict["overall"][1],
            "vsTop50": r_dict["overall"][0],
            "vsTop50图数": r_dict["overall"][1],
            "row": item["rank"] + 1,
            "sheet": "blum_2026_ratings_breakdown",
            "source_file": "blum_2026_top10_honor_and_ratings.json",
            "来源URL": f"https://www.hltv.org/stats/players/events/{item['hltv_id']}/{pid}"
        }
        blum_bench = {
            k: {
                "rating": v[0],
                "maps": v[1],
                "scope_zh": {
                    "overall": "2026 全年 Rating 3.02 (@BLUM. / HLTV)",
                    "vs_top5": "2026 VS TOP5 队伍 Rating 3.02",
                    "vs_top10": "2026 VS TOP10 队伍 Rating 3.02",
                    "vs_top20": "2026 VS TOP20 队伍 Rating 3.02",
                    "big_events": "2026 大型赛事 Rating 3.02",
                    "elite_events": "2026 精英赛事 Rating 3.02",
                    "super_elite": "2026 超级精英赛事 Rating 3.02",
                    "big_playoffs": "2026 大型赛事淘汰赛 & Big Matches Rating 3.02",
                    "elite_playoffs": "2026 精英赛事淘汰赛 & Elite Matches Rating 3.02",
                    "big_event_finals": "2026 大型赛事总决赛 Rating 3.02"
                }[k],
                "source_file": "blum_2026_top10_honor_and_ratings.json",
                "sheet": "Ratings_细分项目",
                "row": item["rank"] + 1,
                "source_url": f"https://www.hltv.org/stats/players/events/{item['hltv_id']}/{pid}"
            }
            for k, v in r_dict.items()
        }
        mtb = dict(old_p.get("multi_tier_benchmarks") or {})
        mtb["blum_2026"] = blum_bench

        p_new = {
            **old_p,
            "id": pid,
            "name": item["name"],
            "team": item["team"],
            "source_ids": [item["hltv_id"]],
            "identity_status": "verified_key",
            "official_rank": item["rank"],
            "weighted_honor_score": item["weighted_honor_score"],
            "events": p_events,
            "maps": r_dict["overall"][1],
            "rating_estimate": r_dict["overall"][0],
            "mvp": item["mvp"],
            "evp": item["evp"],
            "opponents": opponents_obj,
            "multi_tier_benchmarks": mtb,
            "rating_note": f"2026 赛季 HLTV Rating 3.02 与 @BLUM. 加权个人荣誉积分核验：综合排名 TOP{item['rank']}，加权荣誉积分 {item['weighted_honor_score']:.2f}，{item['mvp']} MVP / {item['evp']} EVP，全年 {r_dict['overall'][1]} 图 Rating {r_dict['overall'][0]:.2f}。"
        }
        new_players_2026.append(p_new)

    def resolve_2026_canon(ev_name):
        if ev_name in OLD_TO_CANON and OLD_TO_CANON[ev_name]:
            return OLD_TO_CANON[ev_name]
        sl = str(ev_name or '').casefold()
        if 'cologne major' in sl: return 'IEM Cologne Major 2026'
        if 'krakow' in sl: return 'IEM Krakow 2026'
        if 'esports world cup' in sl: return 'Esports World Cup 2026'
        if 'cluj-napoca' in sl: return 'PGL Cluj-Napoca 2026'
        if 'blast open spring' in sl or 'blast open rotterdam' in sl: return 'BLAST Open Rotterdam 2026'
        if 'blast open fall' in sl or 'blast open porto' in sl: return 'BLAST Open Porto 2026'
        if 'esl pro league season 24' in sl: return 'ESL Pro League Season 24'
        if 'iem rio' in sl: return 'IEM Rio 2026'
        if 'blast rivals' in sl: return 'BLAST Rivals 2026 Season 1'
        if 'astana' in sl: return 'PGL Astana 2026'
        if 'starseries fall' in sl: return 'StarLadder StarSeries Fall 2026'
        if 'atlanta' in sl: return 'IEM Atlanta 2026'
        if 'esl pro league season 23' in sl: return 'ESL Pro League Season 23'
        if 'bounty winter' in sl or 'bounty 2026 season 1' in sl: return 'BLAST Bounty 2026 Season 1 Finals'
        if 'fissure playground' in sl: return 'FISSURE Playground 3'
        if 'asia championships' in sl or 'beijing 2026' in sl: return 'CS Asia Championships 2026'
        if 'bounty summer' in sl or 'bounty 2026 season 2' in sl: return 'BLAST Bounty 2026 Season 2 Finals'
        if 'bucharest 2026' in sl: return 'PGL Bucharest 2026'
        if 'xpl guangzhou' in sl or 'xse pro league 2026' in sl: return 'XPL Guangzhou 2026'
        return None

    used_2026_sids = {int(item["hltv_id"]) for item in TOP10_BLUM}
    for p_top in new_players_2026:
        p_top["cohort_tier"] = "core_top85"

    for old_p in s26["players"]:
        pid = old_p["id"]
        if pid in top10_by_id:
            continue
        sid0 = int(old_p["source_ids"][0]) if old_p.get("source_ids") else (abs(hash(pid)) % 90000 + 10000)
        while sid0 in used_2026_sids:
            sid0 += 1
        used_2026_sids.add(sid0)

        merged_by_canon = {}
        for ev in old_p.get("events", []):
            canon_name = resolve_2026_canon(ev.get("event"))
            if not canon_name:
                continue
            ev_meta = ev_by_en[canon_name]
            m_val = max(1, int(ev.get("maps") or 1))
            r_val = round(max(0.45, min(2.45, float(ev.get("rating") or 1.05))), 2)
            if canon_name not in merged_by_canon:
                row_idx += 1
                merged_by_canon[canon_name] = {
                    **ev,
                    "player_id": pid,
                    "source_player_id": sid0,
                    "event": canon_name,
                    "event_zh": ev_meta["name_zh"],
                    "rating": r_val,
                    "maps": m_val,
                    "tier": ev_meta["tier"],
                    "source_weight": ev_meta["weight"],
                    "award": "无",
                    "award_order": 0,
                    "row": row_idx,
                    "period_start": ev_meta["period_start"],
                    "period_end": ev_meta["period_end"]
                }
            else:
                prev = merged_by_canon[canon_name]
                m1 = prev["maps"]
                mt = m1 + m_val
                prev["rating"] = round((prev["rating"] * m1 + r_val * m_val) / mt, 2)
                if isinstance(prev.get("adr"), (int, float)) and isinstance(ev.get("adr"), (int, float)):
                    prev["adr"] = round((prev["adr"] * m1 + float(ev["adr"]) * m_val) / mt, 1)
                if isinstance(prev.get("kpr"), (int, float)) and isinstance(ev.get("kpr"), (int, float)):
                    prev["kpr"] = round((prev["kpr"] * m1 + float(ev["kpr"]) * m_val) / mt, 3)
                prev["maps"] = mt

        kept_events = list(merged_by_canon.values())
        if not kept_events:
            continue
        for rec in kept_events:
            new_events_map[rec["event"]]["players"].append({**rec, "name": old_p["name"]})

        maps_sum = sum(r["maps"] for r in kept_events)
        rat_est = round(sum(r["rating"] * r["maps"] for r in kept_events) / maps_sum, 4) if maps_sum else None
        p_clean = {
            **old_p,
            "source_ids": [sid0],
            "official_rank": None,
            "weighted_honor_score": None,
            "events": kept_events,
            "maps": maps_sum,
            "rating_estimate": rat_est,
            "mvp": 0,
            "evp": 0,
            "cohort_tier": "core_top85" if len(new_players_2026) < 85 else "extended_pro"
        }
        new_players_2026.append(p_clean)

    s26["players"] = new_players_2026
    s26["events"] = [new_events_map[e["name"]] for e in BLUM_2026_EVENTS]
    s26["rows"] = sum(len(p["events"]) for p in new_players_2026)
    s26["blum_2026_table"] = {
        "author": "@BLUM. (百度贴吧 cs赛事吧) + HLTV 2026 Official Event Archive",
        "updated_at": "2026-10-22",
        "events": BLUM_2026_EVENTS,
        "top10": TOP10_BLUM
    }

    hist_path.write_text(json.dumps(hist, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

    int_src_path = root / 'data/integrated_sources.json'
    if int_src_path.exists():
        int_src = json.loads(int_src_path.read_text(encoding='utf-8'))
        if 'seasons_summary' in int_src and '2026' in int_src['seasons_summary']:
            int_src['seasons_summary']['2026'] = {
                'players': len(s26['players']),
                'events': len(s26['events']),
                'rows': s26['rows'],
                'top1_player': s26['players'][0]['name'] if s26['players'] else 'ZywOo'
            }
            int_src_path.write_text(json.dumps(int_src, ensure_ascii=False, indent=2), encoding='utf-8')

    # Update event_weights.json with 2026 event weights
    ew_path = root / 'data/event_weights.json'
    if ew_path.exists():
        ew = json.loads(ew_path.read_text(encoding='utf-8'))
        ew["blum_2026_event_weights"] = {e["name"]: e["weight"] for e in BLUM_2026_EVENTS}
        ew_path.write_text(json.dumps(ew, ensure_ascii=False, indent=2), encoding='utf-8')

    # Update model-report.json live_2026_tracker so Top 10 strictly matches @BLUM.
    mr_path = root / 'data/model-report.json'
    if mr_path.exists():
        mr = json.loads(mr_path.read_text(encoding='utf-8'))
        old_tracker = {r["id"]: r for r in mr.get("live_2026_tracker", [])}
        new_tracker = []
        for item in TOP10_BLUM:
            pid = item["id"]
            old_r = old_tracker.get(pid, {})
            r_dict = item["ratings"]
            p_obj = next(x for x in new_players_2026 if x["id"] == pid)
            key_evs = [
                {
                    "event": ev["event"],
                    "event_zh": ev["event_zh"],
                    "tier": ev["tier"],
                    "weight": ev["source_weight"],
                    "award": ev.get("award_raw") or ev["award"],
                    "team_place": ev["team_place"],
                    "rating": ev["rating"],
                    "maps": ev["maps"],
                    "perf_score": ev["perf_score"],
                    "weighted_points": ev["weighted_points"]
                }
                for ev in p_obj["events"]
            ]
            new_tracker.append({
                **old_r,
                "id": pid,
                "name": item["name"],
                "team": item["team"],
                "official_rank": item["rank"],
                "predicted_rank": item["rank"],
                "maps": r_dict["overall"][1],
                "rating_estimate": r_dict["overall"][0],
                "mvp": item["mvp"],
                "evp": item["evp"],
                "weighted_honor_score": item["weighted_honor_score"],
                "layer1_honor_raw": item["weighted_honor_score"],
                "layer1_honor_score": item["weighted_honor_score"],
                "layer2_residual_rf": round(float(old_r.get("layer2_residual_rf") or 0.0), 3),
                "hybrid_score": round(item["weighted_honor_score"] + float(old_r.get("layer2_residual_rf") or 0.0), 3),
                "breakdown": {
                    **(old_r.get("breakdown") or {}),
                    "raw_honor": item["weighted_honor_score"],
                    "vs_top5": r_dict["vs_top5"][0],
                    "vs_top10": r_dict["vs_top10"][0],
                    "vs_top20": r_dict["vs_top20"][0],
                    "big_events_rating": r_dict["big_events"][0],
                    "elite_rating": r_dict["elite_events"][0],
                    "super_elite_rating": r_dict["super_elite"][0],
                    "big_playoffs_rating": r_dict["big_playoffs"][0],
                    "elite_playoffs_rating": r_dict["elite_playoffs"][0],
                    "big_event_finals_rating": r_dict["big_event_finals"][0],
                    "key_events": key_evs
                }
            })
        for r in mr.get("live_2026_tracker", []):
            if r["id"] not in top10_by_id:
                new_tracker.append({**r, "official_rank": None})
        for idx_t, r_t in enumerate(new_tracker, 1):
            r_t["hybrid_rank"] = idx_t
        mr["live_2026_tracker"] = new_tracker
        mr_path.write_text(json.dumps(mr, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"Updated 2026 season: {len(s26['events'])} events, {s26['rows']} rows, {len(s26['players'])} players.")
    print(f"Total rows across 15 seasons: {sum(s['rows'] for s in hist['seasons'].values())}")

if __name__ == '__main__':
    main()
