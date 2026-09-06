# macOS 定时运行与归档

只保留下午任务：`scripts/run_daily.sh`在沪深交易日北京时间14:15启动，每30秒尝试保存一次行情，至14:20完成11次尝试并执行初筛；`scripts/run_late_review.sh`在14:50重新获取涨停池，与14:20结果对比并更新T+1概率。任务必须由 Codex再次核验当天是否为沪深交易日，模板不连接券商。不设置09:25开盘检查。

行情采集器是`scripts/collect_market_data.py`。定时连续采样使用直连节点、单节点5秒超时；单次失败写入失败快照并继续下一计划时点，且每次尝试后立即更新Manifest。采样时间使用固定起点的单调时钟，接口耗时不应累加到下一间隔。默认取得沪深A股涨幅前100名；如果第100名涨幅仍不低于8%，必须报告候选截断并改用授权全市场数据源。`scripts/collect_limit_up_pool.py`另行保存涨停池中的首次/最后封板时间、炸板次数、封板资金、连板数和行业，用于确认封板持续时间及14:20到14:50的封单变化。若环境变量`TUSHARE_TOKEN`存在，则用Tushare补充当日涨跌停价格；缺少Token时保持可运行。抓取时间只是本地获取时间，不等于数据商原生时间戳，因此模型仍须披露该限制。

按北京时间交易日保存到：

```text
outputs/YYYY-MM-DD/
  14-20-prediction.md
  14-20-predictions.json
  14-50-late-review.md
  14-50-late-review.json
  validation.json
  raw/afternoon/manifest.json
  raw/afternoon/snapshot-HH-MM-SS.json
  raw/afternoon/limit-up-pool-14-20.json
  raw/afternoon/limit-up-pool-14-50.json
```

Markdown供阅读，JSON供逐日比较和回测。JSON必须包含`schema_version`、`trade_date`、`generated_at_cst`、`run_type`、数据源和数据时间戳；预测记录还应包含`target_trade_date`和模型输出字段。数据不足时仍保存失败报告，但不得生成伪概率。不得覆盖其他运行时点的文件。

安装前确认 `codex` 绝对路径、登录状态、实时数据能力和输出目录。LaunchAgent 的 Weekday 只排除周末，研究流程仍需核验法定节假日和临时休市。

主任务使用`launchd/com.openai.a-share-limit-up-predictor.plist`，尾盘复核使用`launchd/com.openai.a-share-limit-up-late-review.plist`。LaunchAgent按Mac当前系统时区解释日历时间；仓库模板以Asia/Tokyo系统时区编写，所以15:15对应北京时间14:15，约14:20完成初筛；15:50对应北京时间14:50。若Mac时区变化，必须同步修改模板时间。

复制两个下午plist到`~/Library/LaunchAgents/`后再以`launchctl bootstrap`加载。日志写入skill的`outputs/`。失败时保留错误，不生成伪造排名；14:50复核不得覆盖14:20原始预测。两个输出都只包含T+1概率；预计次日涨幅仅在独立收益模型完成样本外校准后展示，不生成T+2概率。
