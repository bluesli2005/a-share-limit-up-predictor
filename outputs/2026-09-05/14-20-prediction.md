14:20 扫描已归档为“非交易日 / 数据质量失败”，未生成伪概率：

- 2026-09-05 是星期六，沪深交易所均非交易日。
- 11 次行情快照全部失败；其中窗口内两次也均失败。
- 涨停池虽返回 39 条记录，但于 15:52 获取且无数据源原生时间戳，无法作为 14:20 数据使用。
- T+1 概率、可买入概率及预期收益均标记为不可用。
- 未输出 T+2，未调用评分器，未连接券商或执行交易。

文件：

- [14-20-predictions.json](/Users/wenbiaoli/.agents/skills/a-share-limit-up-predictor/outputs/2026-09-05/14-20-predictions.json)
- [14-20-prediction.md](/Users/wenbiaoli/.agents/skills/a-share-limit-up-predictor/outputs/2026-09-05/14-20-prediction.md)
- [validation.json](/Users/wenbiaoli/.agents/skills/a-share-limit-up-predictor/outputs/2026-09-05/validation.json)