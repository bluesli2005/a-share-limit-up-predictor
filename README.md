# A-Share Limit-Up Predictor

沪深 A 股新兴产业涨停延续研究工具，也是一个 Codex Skill。项目以北京时间 **14:40** 的行情为研究时点，结合涨停池、公司业务与监管证据，分别研究首板晋级、二板及以上连板和强势未封板股票的 T+1 表现。

仅用于研究和模型评估，不连接券商、不执行交易，也不保证涨停或成交。当前评分器输出的是**未校准的启发式概率**，不是经过实盘验证的预测模型。

## 研究范围与规则

- 覆盖沪深主板、科创板和创业板的新兴产业公司；排除 ST、退市风险证券、B 股、北交所证券、基金和债券。
- 总市值至少 **100 亿元**，流通市值至少 **50 亿元**；缺失或无法核验时排除。
- 候选须处于已核验的适用涨停价，或较前一交易日官方收盘价上涨至少 8%；涨幅达到 8% 不等于涨停。
- 行业资格须有主营、产品或公告证据；监管状态须核验，不能把缺失信息当作正常。
- 评估时行情年龄不超过 60 秒；特征加权覆盖率低于 60% 时排除。
- 首板和二板及以上分别排名，强势未封板股票单列观察；只输出 T+1，不输出 T+2。

完整研究规范见 [SKILL.md](SKILL.md)，输入字段和证据要求见 [数据契约](references/data_contract.md)。这些是完整研究流程的要求，不能仅靠调用评分脚本完成全部核验。

## 目录结构

```text
.
├── SKILL.md                     # Skill 入口与研究规范
├── agents/openai.yaml           # Agent 配置
├── requirements.txt             # 行情依赖
├── scripts/
│   ├── run_daily.sh             # 采集数据并启动 Codex 研究
│   ├── collect_market_data.py   # 行情快照与采集清单
│   ├── collect_limit_up_pool.py # 涨停池采集
│   ├── find_continuations.py    # 基于历史日线的临时连板识别
│   ├── score_candidates.py     # 标准化候选评分
│   └── backtest.py             # 已标注样本外预测的评估
├── references/                 # 数据、行业、特征与调度说明
├── launchd/                    # macOS 定时任务模板
├── tests/test_scripts.py        # 本地测试
└── outputs/                    # 本地报告、原始数据和日志（Git 忽略）
```

## 环境准备

Python 脚本使用 `zoneinfo`，需要 Python 3.9 或更新版本。完整运行入口使用 zsh；定时调度使用 macOS launchd。完整研究还需要已安装、登录且能发现本 Skill 的 Codex CLI。

在仓库根目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

`requirements.txt` 包含 AKShare 和 Tushare。目前行情采集实现优先直接请求东方财富涨幅榜，失败后尝试新浪后备源；依赖已安装不代表数据接口必然可用。可选环境变量 `TUSHARE_TOKEN` 用于补充涨跌停价格，不配置时仍可运行采集。不要将 Token 写入代码或提交到仓库。

## 使用方式

### 完整研究流程

在目标交易日北京时间 14:40 执行：

```bash
zsh scripts/run_daily.sh
```

脚本优先使用 `.venv/bin/python`，不存在时使用 `python3`；随后通过 `codex exec` 启动研究。若 `codex` 不在 PATH 中，可设置 `CODEX_BIN` 为其可执行文件的绝对路径。

运行入口依次采集一次行情快照、一次涨停池，再要求 Codex 核验时间戳、沪深交易日及其他研究条件，并生成报告。采集失败后仍会尝试研究步骤，以保留数据质量失败说明。**Shell 脚本本身没有交易日或 14:40 时间拦截**，不能把任意时间的手动运行当作正式 14:40 预测。

同一天重复运行会复用报告和清单路径，可能覆盖当日结果；额外诊断采集应使用独立输出目录。

### 单独采集数据

以下命令只采集数据，不生成经过证据核验的预测：

```bash
python scripts/collect_market_data.py \
  --mode afternoon --count 1 \
  --output outputs/manual/raw/manifest.json

python scripts/collect_limit_up_pool.py \
  --output outputs/manual/raw/limit-up-pool.json
```

保留行情源时间与本地抓取时间的区别。后备源可能只覆盖涨幅靠前的部分股票，不代表完整市场；缺失时间戳、数据过期或候选截断时，须按规范降级或停止排名。

### 候选评分

先按 [数据契约](references/data_contract.md) 准备 JSON 数组，每个元素是一条经过核验、标准化的候选记录。原始行情快照不能直接当作评分输入。

```bash
mkdir -p outputs/manual
python scripts/score_candidates.py \
  --input candidates.json \
  --output outputs/manual/scores.json
```

`candidates.json` 为自行准备的输入文件，仓库不附带真实可用的候选样本。评分结果包含 T+1 涨停概率、可买入概率、尾盘开板风险、特征覆盖率和分组标记；百分比输出范围为 0–100。预计次日收益字段目前为 `null`，需要独立校准的收益模型后才能提供。

当前脚本按 T+1 概率输出统一列表并附 `candidate_group`；正式报告仍需分组展示。脚本的 `confidence` 反映特征覆盖率，但未校准结果在正式报告中必须标为低置信度。评分器不会自行检索公告、核验行业证据或完成全部证券交易状态检查。

### 历史评估

```bash
python scripts/backtest.py --input predictions.jsonl
```

`predictions.jsonl` 为自行准备的 JSONL 文件，每行一条历史预测，包含交易日期、当时的筛选与质量字段、`probability`（0–1）和 `next_day_limit_up`（0 或 1）。评分输出的百分比用于回测前须除以 100，并补充实际 T+1 标签。

评估器输出样本量、质量筛除数量、Brier score、log loss、校准分箱、每日 Top-5/Top-10 平均命中率和市值分组统计。它不负责下载历史数据、训练模型或执行滚动校准；按首板/高板、主题等分组的完整评估需另行组织输入与分析。禁止用收盘后或未来信息回填当时特征。

## 报告与归档

正式流程约定按北京时间交易日归档：

```text
outputs/YYYY-MM-DD/
  14-40-prediction.md
  14-40-predictions.json
  validation.json
  raw/afternoon/manifest.json
  raw/afternoon/snapshot-HH-MM-SS.json
  raw/afternoon/limit-up-pool-14-40.json
```

采集脚本负责原始数据和清单，Markdown 由运行入口保存；预测 JSON 与验证记录需由研究流程生成和检查，不能仅凭目录存在判断运行成功。数据不足时应保留失败报告，不生成伪造排名。

`output/` 和 `outputs/` 均已加入 [.gitignore](.gitignore)，本地产物不会被常规 `git add` 纳入提交。

## macOS 定时任务

模板位于 [launchd/com.openai.a-share-limit-up-predictor.plist](launchd/com.openai.a-share-limit-up-predictor.plist)，安装步骤与归档要求见 [调度说明](references/scheduling.md)。

使用前需要修改脚本路径、`CODEX_BIN` 和日志路径，创建日志目录，并核对系统时区。模板按 **Asia/Tokyo 的 15:40** 编写，对应北京时间 14:40；launchd 日历时间依赖系统时区，不能仅靠模板中的 `TZ` 环境变量调整触发时刻。

只保留一个 14:40 研究任务。模板仅按工作日触发，节假日和临时休市仍须由研究流程核验；如曾安装旧的 late-review 任务，应按调度说明卸载。

## 测试

在已激活的虚拟环境中执行：

```bash
python -m pip install pytest
python -m pytest -q tests/test_scripts.py
```

测试覆盖行情单位转换与北交所过滤、评分与可买性分离、候选分组及回测市值过滤等本地逻辑，不验证实时接口可用性、定时任务触发或模型预测准确率。

## 进一步阅读

- [新兴产业范围](references/emerging_industries.md)
- [特征解释](references/features.md)
- [数据契约](references/data_contract.md)
- [定时运行与归档](references/scheduling.md)
