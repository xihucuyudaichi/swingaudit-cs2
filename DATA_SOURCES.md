# 数据来源与复现范围

运行快照保留来源标识；原始观测、聚合派生值与预测报告需区分。以下许可标签照录历史登记，**未全部独立核实，不能作为授权结论**。代码仓库的许可证不必然涵盖其数据。

| 来源 | 原登记标签 | 上游链接 |
| --- | --- | --- |
| iftv-top20 | MIT (Code) | [iftv-top20](https://github.com/bootsh-zvuat/IFTV-TOP20) |
| ageha6912-majors | Public Archive | [ageha6912-majors](https://github.com/Ageha6912/cs-major-archive) |
| santtu777-hltv-top | MIT | [santtu777-hltv-top](https://github.com/Santtu777/hltv_top) |
| markzhdan-top20 | Academic Public | [markzhdan-top20](https://github.com/markzhdan/hltv-top-20-predictions) |
| danilofuchs-top20 | MIT | [danilofuchs-top20](https://github.com/danilofuchs/hltv-top20-evolution) |
| raymondtoh94-hltv | Kaggle Public | [raymondtoh94-hltv](https://www.kaggle.com/datasets/raymondtoh94/csgo-players-stats-hltv) |
| tedtay-csgo | MIT | [tedtay-csgo](https://github.com/tedtay/CS-GO-Pro-Matches-Comprehensive-Dataset) |
| onestudio-hltv | GitHub Public | [onestudio-hltv](https://github.com/One-Studio/hltv-stats) |
| valve-vrs | Valve Official | [valve-vrs](https://github.com/ValveSoftware/counter-strike_regional_standings) |
| ektarr-cs2 | CC BY-SA 4.0 | [ektarr-cs2](https://www.kaggle.com/datasets/ektarr/counter-strike-pro-matches) |
| eupeutro-blast-2026 | Kaggle Public | [eupeutro-blast-2026](https://www.kaggle.com/datasets/eupeutro/blast-rivals-2026-cs2-match-statistics) |
| jamiepacker-roles | CC BY 4.0 | [jamiepacker-roles](https://github.com/Jamie-Packer/cs2-playstyle-dataset-2024) |
| opencs2-telemetry | CC BY 4.0 | [opencs2-telemetry](https://huggingface.co/datasets/blanchon/opencs2_dataset) |
| sneakyzero-economy | HF Open | [sneakyzero-economy](https://huggingface.co/datasets/sneakyzero/cs2-pro-round-economy) |
| griffin-ts-rounds | CC0 | [griffin-ts-rounds](https://www.kaggle.com/datasets/griffindesroches/cs2-professional-round-by-round-statistics-dataset) |
| esportsbench-cs | CC BY-SA 3.0 | [esportsbench-cs](https://huggingface.co/datasets/EsportsBench/EsportsBench) |
| eshtiak-career | Kaggle Public | [eshtiak-career](https://www.kaggle.com/datasets/eshtiakferdousmahi/cs2-player-stats) |
| livanoff-merfaruk | Kaggle Public | [livanoff-merfaruk](https://www.kaggle.com/datasets/livanoff/csgo-esport-matches-round-data) |
| pachellber-econ-r30 | MIT | [pachellber-econ-r30](https://github.com/pachellber-marine/CS2-ECONEFFICIENCY) |
| nmwalsh-hltv-ids | GitHub Public | [nmwalsh-hltv-ids](https://github.com/nmwalsh/HLTV-Scraper) |
| gungor-major-mvps | GitHub Public | [gungor-major-mvps](https://github.com/gungorMetehan/csgo-cs2) |
| dsckgec-career | GitHub Public | [dsckgec-career](https://github.com/DSCKGEC/CS-GO-Professionals) |
| rlinv1-top20-rosters | GitHub Public | [rlinv1-top20-rosters](https://github.com/RLinV1/HLTV-Web-Scraper) |

原始来源表位于 `data/source-audit/iftv/`；其 manifest 提供下载 URL、表结构与 SHA-256。其余原始大体积下载不随仓库提供，导入脚本中的路径记录了所需输入。

本发布保留现有运行数据，不执行批量 HLTV 抓取。`integrated_sources.json` 中的 verified 命名是历史程序字段，不意味着授权或事实核验已经全部完成。

## 2026-11-02 GitHub 上游许可文件核对

以下是 GitHub 当前许可接口返回的**仓库级**文件，副本保存在 `third_party/licenses/`；仍不能推定覆盖作者采集的所有统计数据。未返回的条目不意味着已获许可。

- iftv-top20: NOASSERTION — https://github.com/bootsh-zvuat/IFTV-TOP20/blob/main/LICENSE
- ageha6912-majors: not returned by GitHub license API
- santtu777-hltv-top: MIT — https://github.com/Santtu777/hltv_top/blob/main/LICENSE
- markzhdan-top20: not returned by GitHub license API
- danilofuchs-top20: MIT — https://github.com/danilofuchs/hltv-top20-evolution/blob/master/LICENSE
- tedtay-csgo: MIT — https://github.com/tedtay/CS-GO-Pro-Matches-Comprehensive-Dataset/blob/main/LICENSE.txt
- onestudio-hltv: not returned by GitHub license API
- valve-vrs: not returned by GitHub license API
- jamiepacker-roles: CC-BY-4.0 — https://github.com/Jamie-Packer/cs2-playstyle-dataset-2024/blob/main/LICENSE
- pachellber-econ-r30: MIT — https://github.com/pachellber-marine/CS2-ECONEFFICIENCY/blob/master/LICENSE
- nmwalsh-hltv-ids: not returned by GitHub license API
- gungor-major-mvps: MIT — https://github.com/gungorMetehan/csgo-cs2/blob/main/LICENSE
- dsckgec-career: MIT — https://github.com/DSCKGEC/CS-GO-Professionals/blob/main/LICENSE
- rlinv1-top20-rosters: not returned by GitHub license API
