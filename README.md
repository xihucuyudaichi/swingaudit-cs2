---
title: SwingAudit CS2 选手观察室
emoji: 🎯
colorFrom: gray
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
domain:
  - multi-modal
tags:
  - cs2
  - sports-analytics
  - agent
deployspec:
  cpu: 2
  memory: 16000
  gpu: 0
  gpu_memory: 0
  instance: 1
---

# SwingAudit · CS2 选手观察室

设计大数据课程项目：面向 CS/CS2 职业选手的证据检索、同位置比较、年度排名分析与未来赛事条件推演。前端采用 React / Vite，后端采用 Python / SQLite。

## 在线体验

- [独立工作台（推荐）](https://lafivibe-swingaudit-cs2.ms.show/)
- [魔搭创空间](https://www.modelscope.cn/studios/Lafivibe/swingaudit-cs2?mode=full)

建议依次体验：选手对比 → 点选数据向悬浮助手追问 → 展开依据 → 年度排名／未来推演。首次访问请等待空间与数据加载。2026 是进行中赛季，站内追踪为项目计算，不是官方年终榜单，也不是实时数据服务。

当前数据：2012–2026 共 15 个赛季年份、6,943 份选手赛季档案、38,895 条分站记录；23 组公开来源登记 10,516,747 行，另有 BLUM 2026 补充表。原始行数混合比赛、回合、帧等粒度，不能当作独立训练样本数。

## 快速运行

已验证环境：Node.js 24.14、Python 3.11.9。Vite 要求 Node.js 20.19+ 或 22.12+；建议使用 Node.js 24 与 Python 3.11。

```sh
git clone https://github.com/xihucuyudaichi/swingaudit-cs2.git
cd swingaudit-cs2
npm ci
python -m venv .venv
```

激活虚拟环境：Windows PowerShell 执行 `.\.venv\Scripts\Activate.ps1`；macOS / Linux 执行 `source .venv/bin/activate`。如 PowerShell 禁止脚本，可直接使用 `.\.venv\Scripts\python.exe` 替代下文的 `python`。

```sh
python -m pip install -r backend/requirements-lock.txt
python backend/server.py
```

保持后端终端运行，在第二个终端进入项目目录：

```sh
npm run dev
```

浏览器打开 **http://127.0.0.1:5177/**。后端位于 `127.0.0.1:5188`，两个端口须空闲。Windows 完成依赖安装并激活虚拟环境后，也可执行 `./start.ps1`。

仓库附带当前运行快照，无需重新抓取或训练。浏览数据、选手比较、角色分析、预测报告与条件推演不需要模型密钥；AI 问答需下述配置。个人研究记录首次保存时自动创建于 `data/research.sqlite3`，不随仓库分发。

## 可选：配置 AI 问答

1. 复制 `backend/lab.example.json` 为 `backend/lab.local.json`。
2. 复制 `backend/credentials.example.py` 为 `backend/credentials.local.py`，填写自己的 `API_KEY`。
3. 在本机 JSON 中填写有权使用的 Chat Completions 服务 `base_url`。默认模型固定为 `qwen3.8-27b`，服务须支持该模型及工具调用；这不是任意模型服务的通用保证。
4. 从项目根目录启动后端；若凭据文件在别处，可将 `credential_source` 改为绝对路径。`ROUND_LAB_CONFIG` 可指定配置文件位置。

两个 `.local.*` 文件均已忽略。服务地址和原作者密钥不随仓库提供。未配置时 AI 会显示配置缺失，不影响数据页面。前端代码和 `VITE_*` 环境变量中不得放入密钥。

## 功能与证据边界

- 2012–2026 共 15 赛季的收录快照：选手档案、赛事、同年同范围比较。
- 角色对齐、历史留出预测报告、2026 追踪榜。
- 仅针对未来赛事的条件推演；假设与预测不是已发生的事实。
- AI 求证调用后端受控工具；本地入口使用本机 SQLite，云端入口按访客会话隔离研究记录。

数据来自多个第三方公开来源，并非官方完整数据库或实时更新服务。赛事加权 Rating 不应称为官方全年 Rating；缺失、推导指标、预测与原始观测应分别解读。完整来源和许可待核实项见 [DATA_SOURCES.md](DATA_SOURCES.md)。

## 目录

| 路径 | 用途 |
| --- | --- |
| `src/`, `public/` | 前端源码及展示素材 |
| `backend/` | API、数据处理、模型与工具逻辑 |
| `data/*.json` | 运行所需数据快照、规则、角色与模型报告 |
| `data/source-audit/iftv/` | 启动时校验所需的六份原始表与 SHA-256 清单 |
| `tests/` | 离线测试与可选浏览器测试 |
| `package-lock.json`, `backend/requirements-lock.txt` | 依赖版本记录 |

大型研究下载、临时分析依赖、截图、旧备份、个人数据库不进入版本控制。公开快照包含运行必需数据，但不包含所有上游原始研究文件。`normalize.py` 是早期两赛季导入脚本，**不要为启动而运行它**，它会覆盖当前快照；全量重建需另行获取相应上游输入并按导入脚本准备，不能等同于正常启动。

## 验证

```sh
npm run build
npm test
```

先构建再测试：云端静态资源测试会读取 `dist/`，全新下载后直接运行 `npm test` 会因缺少前端产物失败。使用虚拟环境时，确认 `npm test` 调用的 `python` 已激活，或直接运行 `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v`。

浏览器测试是可选步骤：另行安装 Python Playwright 和相应浏览器，先启动前后端，再运行 `npm run test:browser`。`npm run test:agent` 会调用自己配置的在线模型，可能产生服务费用，不属于离线测试。

## 云端独立部署（魔搭社区创空间 ModelScope Studio · Docker 模式）

仓库内置免侵入的云端单端口同源入口（`app.py` / `backend/cloud_server.py`）与多阶段构建 `Dockerfile`，监听标准容器端口 `0.0.0.0:7860`：

- **同源静态与 API 托管**：自动编译并托管 `dist/` 静态前端与 `/api/*` 数据与分析接口，兼容 `*.ms.show` / `modelscope.cn` 等云端同源 `POST` 请求。
- **Gzip 内存预压缩**：对大体量数据响应提供 Gzip 缓存；实际首屏体积取决于部署版本与首屏数据模式。
- **访客 SQLite 隔离**：按访客会话隔离研究记录，不读取或暴露任何个人本地数据库。
- **加密环境变量注入**：支持在创空间【设置 -> Secrets】中配置 `ROUND_LAB_BASE_URL` 与 `ROUND_LAB_API_KEY`（可选 `ROUND_LAB_TIMEOUT_SECONDS`、`ROUND_LAB_MAX_TOKENS`），无需在代码库中存放密钥。

### 一键发布至魔搭创空间

1. 登录 [魔搭社区 Access Token 页面](https://modelscope.cn/my/myaccesstoken) 获取 SDK 访问令牌（使用 Docker 创空间需先完成实名认证与阿里云账号绑定）。
2. 在项目根目录执行：

```sh
python scripts/deploy_modelscope.py --token "<YOUR_MODELSCOPE_TOKEN>"
```

脚本会自动校验账号、创建或更新 `swingaudit-cs2` Docker 创空间（所选规格与可用资源以平台实际配置为准）、将本机 `lab.local.json` 模型密钥同步至云端加密 Secrets、推送代码至创空间 `master` 分支并触发构建。构建完成后可直接访问：
- 创空间页面：`https://modelscope.cn/studios/<你的用户名>/swingaudit-cs2`
- 全屏直连页面：`https://<你的用户名>-swingaudit-cs2.ms.show`

## 部署边界

在线 Demo 已部署在上述魔搭创空间；GitHub 用于查看代码、下载与复现。完整应用需要 Python 后端，不能只上传 `dist/` 静态文件。

本地开发入口 `backend/server.py` 默认监听 `127.0.0.1:5188`；云端入口 `app.py` 监听 `0.0.0.0:7860` 并同源托管前端与 API。两者的监听地址、来源校验及记录存储方式不同。云端按访客会话隔离研究记录，该会话并非登录账户；清除浏览器 Cookie 或使用另一浏览器可能无法取回原会话记录。持久保存需要挂载稳定存储。

数据与模型报告按快照提供，页面可访问不代表上游数据实时更新。AI 需要后端配置可用模型服务；health 的 `configured_unverified` 仅说明已配置，不等于实时问答已验证。

## 使用与权利说明

本仓库用于课程展示及代码交流，未对整个项目追加 MIT 等统一开源许可。公开可查看与完整开源授权是不同概念。第三方数据、字体、依赖、游戏相关素材的权利及适用条款归相应权利人；来源登记不是再分发权利已全部核验的声明。详见 [NOTICE.md](NOTICE.md) 与 [DATA_SOURCES.md](DATA_SOURCES.md)。

## 初次发布验证记录（2026-11-02）

在仅含 Git 提交文件、不含本机模型配置或研究数据库的独立副本中：

- `npm ci` 成功；新建 Python 3.11 虚拟环境并安装锁定依赖成功。
- 67 项离线单元测试全部通过。
- `npm run build` 成功，有主 JavaScript 包超过 500 kB 的体积提示。
- 临时本地 HTTP 服务的 health / coverage / rules / upcoming-events / sources 五个接口均返回 200；无模型密钥时 health 明确报告未配置。

上述初次发布检查未执行浏览器视觉验收、真实在线模型问答或公开服务器部署；随后已完成魔搭部署，见文首在线入口。来源哈希一致与程序测试通过不等于统计事实及数据权利已全部核验。

## 提交前交叉核验（2026-11-03）

- 本地工作副本：71 项离线测试通过，生产构建通过。
- GitHub `c705b79` 的独立源码副本：`npm ci`、生产构建与 71 项测试通过；该公开版本仍有 JavaScript 单包体积超过 500 kB 的构建提示。后续本地分包与首屏优化尚未包含在此提交中。
- 魔搭：页面与 health、模型、角色、来源、覆盖、未来赛程接口可访问；模型、角色和来源清单与提交材料所用 JSON 一致。
- 未来推演接口：donk 在新加坡 Major 夺冠＋MVP、Rating 1.50、12 图时，得分 18.19 → 22.55；再增加同等表现的香港站后为 24.38，仍低于 ZywOo 的 25.68。其他选手不追加成绩，结果仅适用于该快照与设定。
- 2025 主报告：双层 RF 命中 17/20、MAE 3.50；荣誉基线为 19/20、MAE 3.20。主报告候选池 166/171 人，与滚动回测末窗口 189/196 人、MAE 3.45 分开报告。
- 2025 角色报告：467 份档案、239 份核心拟合样本，轮廓系数 0.8163；部分特征为推导或校准值，不能据此宣称角色识别准确率。

本轮未重新完成浏览器全流程和真实 AI 问答验收。已有交互记录、离线测试及接口检查的证据范围分别保留。
