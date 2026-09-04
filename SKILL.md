---
name: a-share-limit-up-predictor
description: Screen Shanghai and Shenzhen A-shares around 14:30 China Standard Time and estimate one-day and two-day limit-up continuation probabilities plus buyability for qualifying emerging-industry stocks. Use for first-board, second-board, and higher continuation research and backtesting; not for execution or guaranteed predictions.
argument-hint: "[scan|score|backtest]"
---

# A-Share Limit-Up Continuation Research

Produce a timestamped probability ranking around 14:30 China Standard Time on mainland-China trading days. Never connect to a broker, submit an order, promise a fill, or claim that a stock will certainly remain sealed.

## Universe

Cover SSE/SZSE Main Boards, STAR Market, and ChiNext. At the 14:30 snapshot require verified total market capitalization of at least RMB 10 billion (100亿元) and free-float market capitalization of at least RMB 5 billion (50亿元); exclude candidates below either threshold or with missing data. Exclude ST, `*ST`, delisting-risk securities, B-shares, Beijing Stock Exchange securities, funds, and bonds. Include recently listed stocks only when they meet both market-cap thresholds; during a no-price-limit period classify them as `new-stock observation` rather than assign a conventional board count.

Cover the full emerging-industry taxonomy in [emerging industry scope](references/emerging_industries.md), including next-generation IT, AI, semiconductors, optical communications, advanced computing, cybersecurity, robotics, high-end equipment, commercial aerospace, low-altitude economy, new materials, new energy, new-energy vehicles, energy storage, hydrogen energy, environmental technology, innovative drugs, biotechnology, high-end medical devices, digital creativity, quantum technology, brain-computer interfaces, synthetic biology and other verifiable frontier technologies. Do not restrict candidates to the examples previously named.

Set `emerging_industry_eligible=true` only from current constituent classifications plus company disclosures or other traceable主营 evidence. Industry-name keyword matches may discover candidates but cannot by themselves establish eligibility. Exclude a pure traditional business; include a cross-industry company only when its emerging business is material or supported by a clearly disclosed product, revenue, order, capacity or R&D milestone. Missing verification is `null` and is excluded from formal scoring.

At 14:30 select stocks at their verified applicable limit-up price or up at least 8% from the previous official close. Verify board, listing-age rules, ex-rights state, risk-warning state, and that day's actual limit price; never assume every security uses 10%.

Include verified `board_count=1` stocks as `首板候选`, as well as second-board and higher stocks. First-board stocks must satisfy the same industry, market-cap, freshness, regulatory, and feature-coverage rules. Keep stocks up at least 8% but not sealed in a separate `强势未封板观察` group; do not call them first-board stocks.

## Snapshot and evidence

Read [data contract](references/data_contract.md) before collection. Require data age no greater than 60 seconds at evaluation time; reject missing or stale timestamps. Collect price path, applicable limit, first/last seal time, continuously sealed minutes, reopen count, queue value and decay, unmatched buy volume, turnover, volume ratio, traded value, total market cap, free-float market cap, free-float ratio, board count, prior-board quality, sector breadth and leader status, news, announcements, exchange inquiries, suspensions, abnormal-trading notices, and market regime.

Use `scripts/collect_market_data.py` for scheduled snapshots. AKShare is the default quote source and Tushare supplements limit prices when `TUSHARE_TOKEN` is configured. Treat these as source adapters, not guarantees: retain source metadata, never equate local retrieval time with exchange time, and downgrade or reject data that cannot satisfy freshness requirements.

Hard-exclude a stock when a current authoritative source identifies suspension or expected suspension, severe abnormal trading/volatility, exchange重点监控, investigation, unresolved material regulatory inquiry, or another condition that makes next-day comparability or normal trading unreliable. If regulatory status cannot be verified, exclude rather than assume it is clear.

A stock sealed for at least 30 consecutive minutes by 14:30 is a `stable-seal candidate`, not proof it stays sealed through 15:00. Estimate late-break risk from queue-to-turnover ratio, queue decay, cancellations, executions near the limit, reopen history, theme weakening, and market breadth.

Always separate:

- `next_trading_day_limit_up_probability_pct`: probability of closing at its applicable limit-up price on T+1;
- `second_day_limit_up_given_first_probability_pct`: conditional probability of T+2 limit-up given T+1 closed limit-up;
- `two_day_continuation_probability_pct`: joint probability of closing limit-up on both T+1 and T+2;
- `buyability_probability_pct`: probability a hypothetical order could fill without chasing an opening spike;
- `late_break_risk_pct`: risk today's seal opens before the close.

Display all probabilities as percentages from 0% to 100%. The two-day joint probability must not exceed either constituent probability. Treat each horizon as a separate calibration target; do not obtain T+2 merely by copying T+1. Buyability is a market-access estimate, not a Buy recommendation.

Only perform and display T+2 analysis when the calibrated T+1 limit-up probability is strictly greater than 60%. At 60% or below, set both T+2 fields to `—` and state `未达到T+2分析门槛`; keep the stock in the T+1 ranking when otherwise eligible. This gate controls inference and presentation, not collection of T+1 training samples.

High continuation probability with low accessibility must be labeled `高概率但难买入`. For turnover, volume ratio, and fill-risk interpretation, read [feature guide](references/features.md).

## Scoring and backtest

Normalize inputs and call `scripts/score_candidates.py`. Every row must provide verified `emerging_industry_eligible=true` and a canonical `emerging_industry_category`; false or missing eligibility is a hard exclusion. Require feature coverage of at least 60%; exclude lower-coverage rows. Label 60%–under-80% coverage `low confidence`; permit normal confidence only at 80% or higher. Use walk-forward empirical calibration when available. Without calibration, label results `启发式概率（未校准）`, cap confidence at low, and avoid false precision. Missing material microstructure data must actually reduce coverage; do not silently substitute neutral defaults.

Use `scripts/backtest.py` on strictly out-of-sample daily predictions and apply the same market-cap, freshness, coverage, and point-in-time regulatory filters historically. Maintain separate labels for T+1 limit-up, T+2 limit-up, and limit-up on both days. Evaluate the joint outcome within the historical T+1-probability-above-60% gate; calibrate conditional T+2 only among gated observations whose actual T+1 label is 1. Prevent final-close data, future-day data, revised classifications, and later news from entering 14:30 features. Use at least two years when available; for qualifying stocks listed less than two years use all observations since listing and report them separately. Report sample count, excluded count, Brier score, log loss, calibration bins, Top-5/Top-10 hit rates, and results by board count, theme, total-market-cap bucket, and free-float-market-cap bucket.

Calibrate and evaluate first-board observations separately from second-board-and-higher observations because their base rates differ. If the first-board calibration sample is insufficient, label it `首板启发式概率（未校准）`; do not silently reuse a higher-board calibration curve.

## Output

Rank by calibrated T+1 continuation probability, then—only above the 60% T+1 gate—the two-day joint probability, seal quality, and confidence. Show ticker/name, board, theme, current board count, price change, seal duration, reopen count, queue and decay, turnover, volume ratio, total market cap, free-float market cap, free-float ratio, market-cap cohort, all three continuation probabilities, buyability percentage, late-break-risk percentage, evidence, uncertainty, and observable invalidation conditions.

Provide a `首板晋级概率榜`, a `二板及以上连板概率榜`, a separate `强势未封板观察`, and a separate `高概率但难买入` list. For a first-board row, T+1 means its probability of advancing from first board to second board. Do not mix the two probability rankings. If no reliable real-time data exists, output a data-quality failure report rather than a ranking.

Archive every run locally by China trading date. Read [scheduling and archive rules](references/scheduling.md) before installing or changing scheduled runs. Preserve both a human-readable Markdown report and machine-readable JSON; never overwrite the opening report with the 14:30 report. Historical comparisons must use archived point-in-time inputs and predictions rather than reconstructed values.

## Scheduling and validation

Run only the afternoon LaunchAgent: start collection at 14:25 Asia/Shanghai on weekdays and finish the formal snapshot at about 14:30. Do not schedule or generate a 09:25 opening review. The runner must verify the SSE/SZSE trading calendar and exit on holidays or non-trading days. Scheduling starts research only and never touches a trading system.

> Research and model evaluation only; not personalized investment advice or a trading instruction.
