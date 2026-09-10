已生成 [result.json](/Users/wenbiaoli/.agents/skills/a-share-limit-up-predictor/outputs/2026-09-10/manual-rerun-sina/result.json)。

结论：

- Sina fallback 已恢复市场数据：96 条；其中涨幅 ≥8% 有 51 条。
- Eastmoney 涨停池成功返回 35 条：首板 26 条、二板及以上 9 条。
- 数据均为盘后采集。Sina 只有时分秒、没有行情日期；涨停池没有源端快照时间，因此无法验证 14:40 时点及 60 秒新鲜度。
- 主营业务、产业资格、监管状态、量比等证据不完整，满足 ≥60% 特征覆盖率的记录为 0。
- 未运行评分器；未生成任何 T+1、可买入、炸板风险或预期收益概率。
- 已通过 `jq` 结构和计数一致性校验。正式 14:40 文件哈希保持不变，未被修改。

