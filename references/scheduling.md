# 11:30采集、14:40对照分析与归档

保留两个任务：`scripts/run_midday.sh`在沪深交易日北京时间11:30启动，等待8秒后保存上午收盘行情和涨停池；`scripts/run_daily.sh`在14:40抓取下午数据、生成11:30至14:40逐股差分并执行唯一一份T+1分析。午间任务不输出概率或投资建议。两个任务都要核验沪深交易日，且不连接券商。不设置09:25、14:20或14:50任务。

14:40由`scripts/collect_with_retries.py`编排采集。行情或涨停池任一文件缺失、状态非成功或记录数为0时，整组重试，最多3次，之后必须停止。每次证据保存在`raw/afternoon/attempts/`，尝试摘要保存为`raw/afternoon/collection-attempts.json`。三次均失败时仍生成数据质量失败报告，不继续循环。

行情采集器是`scripts/collect_market_data.py`。14:40任务先请求东方财富涨幅榜；该接口失败时，使用新浪涨幅榜作为独立后备源，单次最多读取涨幅前200名并保留新浪行情时间。两者均失败时写入失败快照与Manifest，并生成数据质量失败报告。如果最后一名涨幅仍不低于8%，必须报告候选截断并改用授权全市场数据源。`scripts/collect_limit_up_pool.py`另行保存涨停池中的首次/最后封板时间、炸板次数、封板资金、连板数和行业，用于确认14:40时的封板持续时间、炸板情况和封单强度。若环境变量`TUSHARE_TOKEN`存在，则用Tushare补充当日涨跌停价格；缺少Token时保持可运行。必须同时保存本地抓取时间和数据源行情时间；缺少完整日期时披露限制，不得把本地时间冒充交易所时间。

按北京时间交易日保存到：

```text
outputs/YYYY-MM-DD/
  11-30-to-14-40-comparison.json
  14-40-prediction.md
  14-40-predictions.json
  validation.json
  raw/midday/market-11-30.json
  raw/midday/limit-up-pool-11-30.json
  raw/midday/trading-day-check.json
  raw/afternoon/manifest.json
  raw/afternoon/collection-attempts.json
  raw/afternoon/attempts/market-attempt-N.json
  raw/afternoon/attempts/limit-up-pool-attempt-N.json
  raw/afternoon/snapshot-HH-MM-SS.json
  raw/afternoon/limit-up-pool-14-40.json
```

Markdown供阅读，JSON供逐日比较和回测。JSON必须包含`schema_version`、`trade_date`、`generated_at_cst`、`run_type`、数据源和数据时间戳；预测记录还应包含`target_trade_date`和模型输出字段。数据不足时仍保存失败报告，但不得生成伪概率。不得覆盖其他运行时点的文件。

安装前确认 `codex` 绝对路径、登录状态、实时数据能力和输出目录。LaunchAgent 的 Weekday 只排除周末，研究流程仍需核验法定节假日和临时休市。

任务使用`launchd/com.openai.a-share-limit-up-predictor-midday.plist`和`launchd/com.openai.a-share-limit-up-predictor.plist`。LaunchAgent按Mac当前系统时区解释日历时间；仓库模板以Asia/Tokyo系统时区编写，所以12:30对应北京时间11:30，15:40对应北京时间14:40。若Mac时区变化，必须同步修改两个模板时间。

复制两个plist到`~/Library/LaunchAgents/`后再分别以`launchctl bootstrap`加载，并确保旧的`com.openai.a-share-limit-up-late-review`任务已卸载。日志写入skill的`outputs/`。失败时保留错误，不生成伪造排名。输出只包含T+1概率；预计次日涨幅仅在独立收益模型完成样本外校准后展示，不生成T+2概率。
