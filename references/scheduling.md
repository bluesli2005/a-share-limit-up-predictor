# macOS 定时运行与归档

只保留`scripts/run_daily.sh`：在沪深交易日北京时间14:25启动，每30秒保存一次行情，至14:30完成11个快照后执行正式预测。任务必须由 Codex再次核验当天是否为沪深交易日，模板不连接券商。不设置09:25开盘检查。

行情采集器是`scripts/collect_market_data.py`。默认通过东方财富单请求取得沪深A股涨幅前100名，避免AKShare全市场分页触发限流；这足以覆盖通常数量远少于100只的涨停及涨幅不低于8%的候选。如果第100名涨幅仍不低于8%，必须报告候选截断并改用授权全市场数据源。采集器保存最新价、今开、昨收、成交量额、换手率、量比和两类市值，直连失败时才回退AKShare。若环境变量`TUSHARE_TOKEN`存在，则用Tushare补充当日涨跌停价格；缺少Token时保持可运行。抓取时间只是本地获取时间，不等于数据商原生时间戳，因此模型仍须披露该限制。

按北京时间交易日保存到：

```text
outputs/YYYY-MM-DD/
  14-30-prediction.md
  14-30-predictions.json
  validation.json
  raw/afternoon/manifest.json
  raw/afternoon/snapshot-HH-MM-SS.json
```

Markdown供阅读，JSON供逐日比较和回测。JSON必须包含`schema_version`、`trade_date`、`generated_at_cst`、`run_type`、数据源和数据时间戳；预测记录还应包含`target_trade_date`和模型输出字段。数据不足时仍保存失败报告，但不得生成伪概率。不得覆盖其他运行时点的文件。

安装前确认 `codex` 绝对路径、登录状态、实时数据能力和输出目录。LaunchAgent 的 Weekday 只排除周末，研究流程仍需核验法定节假日和临时休市。

任务使用`launchd/com.openai.a-share-limit-up-predictor.plist`。LaunchAgent按Mac当前系统时区解释日历时间；仓库模板以Asia/Tokyo系统时区编写，所以15:25对应北京时间14:25。若Mac时区变化，必须同步修改模板时间。

复制该plist到`~/Library/LaunchAgents/`后再以`launchctl bootstrap`加载。日志写入skill的`outputs/`。失败时保留错误，不生成伪造排名。
