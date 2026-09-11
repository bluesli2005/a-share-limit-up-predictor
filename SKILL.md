---
name: a-share-limit-up-predictor
description: Capture Shanghai and Shenzhen A-share conditions at 11:30 and compare them with a 14:40 scan to estimate next-trading-day limit-up probability, optional expected return, and buyability for qualifying emerging-industry stocks. Use for first-board and higher continuation research and backtesting; not for execution or guaranteed predictions.
argument-hint: "[scan|score|backtest]"
---

# A-Share Limit-Up Continuation Research

Capture an intermediate morning-close snapshot at 11:30 and produce one timestamped ranking at 14:40 China Standard Time on mainland-China trading days. Never connect to a broker, submit an order, promise a fill, or claim that a stock will certainly remain sealed.

## Universe

Cover SSE/SZSE Main Boards, STAR Market, and ChiNext. At the 14:40 snapshot require verified total market capitalization of at least RMB 10 billion (100亿元) and free-float market capitalization of at least RMB 5 billion (50亿元); exclude candidates below either threshold or with missing data. Exclude ST, `*ST`, delisting-risk securities, B-shares, Beijing Stock Exchange securities, funds, and bonds. Include recently listed stocks only when they meet both market-cap thresholds; during a no-price-limit period classify them as `new-stock observation` rather than assign a conventional board count.

Cover the full emerging-industry taxonomy in [emerging industry scope](references/emerging_industries.md), including next-generation IT, AI, semiconductors, optical communications, advanced computing, cybersecurity, robotics, high-end equipment, commercial aerospace, low-altitude economy, new materials, new energy, new-energy vehicles, energy storage, hydrogen energy, environmental technology, innovative drugs, biotechnology, high-end medical devices, digital creativity, quantum technology, brain-computer interfaces, synthetic biology and other verifiable frontier technologies. Do not restrict candidates to the examples previously named.

Set `emerging_industry_eligible=true` only from current constituent classifications plus company disclosures or other traceable主营 evidence. Industry-name keyword matches may discover candidates but cannot by themselves establish eligibility. Exclude a pure traditional business; include a cross-industry company only when its emerging business is material or supported by a clearly disclosed product, revenue, order, capacity or R&D milestone. Missing verification is `null` and is excluded from formal scoring.

At 14:40 select stocks at their verified applicable limit-up price or up at least 8% from the previous official close. Verify board, listing-age rules, ex-rights state, risk-warning state, and that day's actual limit price; never assume every security uses 10%.

Include verified `board_count=1` stocks as `首板候选`, as well as second-board and higher stocks. First-board stocks must satisfy the same industry, market-cap, freshness, regulatory, and feature-coverage rules. Keep stocks up at least 8% but not sealed in a separate `强势未封板观察` group; do not call them first-board stocks.

## Snapshot and evidence

Read [data contract](references/data_contract.md) before collection. Require data age no greater than 60 seconds at evaluation time; reject missing or stale timestamps. Collect price path, applicable limit, first/last seal time, continuously sealed minutes, reopen count, queue value and decay, unmatched buy volume, turnover, volume ratio, traded value, total market cap, free-float market cap, free-float ratio, board count, prior-board quality, sector breadth and leader status, news, announcements, exchange inquiries, suspensions, abnormal-trading notices, and market regime.

Use `scripts/collect_market_data.py` for scheduled snapshots. Start the 11:30 task on time and collect after a short 5–20 second settling delay. Preserve it only as intermediate point-in-time evidence; do not generate a separate 11:30 probability ranking. Capture the quote provider's `industry` field in the raw snapshot. For every stock presented in a ranking or observation list, enrich `main_business` from the latest point-in-time annual/interim report, prospectus, exchange disclosure or company product disclosure and retain `business_evidence`; never infer主营业务 from the company name or concept tags. AKShare is the default quote source and Tushare supplements limit prices when `TUSHARE_TOKEN` is configured. Treat these as source adapters, not guarantees: retain source metadata, never equate local retrieval time with exchange time, and downgrade or reject data that cannot satisfy freshness requirements.

Hard-exclude a stock when a current authoritative source identifies suspension or expected suspension, severe abnormal trading/volatility, exchange重点监控, investigation, unresolved material regulatory inquiry, or another condition that makes next-day comparability or normal trading unreliable. If regulatory status cannot be verified, exclude rather than assume it is clear.

A stock sealed for at least 30 consecutive minutes by 14:40 is a `stable-seal candidate`, not proof it stays sealed through 15:00. Use the provider's verified last-seal time together with the 14:40 limit-up pool; do not infer 30 minutes from a single snapshot. Estimate late-break risk from queue-to-turnover ratio, cancellations, executions near the limit, reopen history, theme weakening, and market breadth. Set queue decay to null unless comparable earlier point-in-time data is available from the same run; do not invent it.

Always separate:

- `next_trading_day_limit_up_probability_pct`: probability of closing at its applicable limit-up price on T+1;
- `expected_next_day_return_pct` or `expected_next_day_return_range_pct`: optional separately calibrated next-day close-to-close return estimate;
- `buyability_probability_pct`: probability a hypothetical order could fill without chasing an opening spike;
- `late_break_risk_pct`: risk today's seal opens before the close.

Display T+1 and buyability probabilities as percentages from 0% to 100%. Do not produce, store or display any T+2 probability. An expected return must come from a separately backtested return model; do not derive it mechanically from the limit-up probability. When that model is unavailable, show `—` and retain the T+1 probability. Buyability is a market-access estimate, not a Buy recommendation.

High continuation probability with low accessibility must be labeled `高概率但难买入`. For turnover, volume ratio, and fill-risk interpretation, read [feature guide](references/features.md).

## Scoring and backtest

Normalize inputs and call `scripts/score_candidates.py`. Every row must provide verified `emerging_industry_eligible=true` and a canonical `emerging_industry_category`; false or missing eligibility is a hard exclusion. Require feature coverage of at least 60%; exclude lower-coverage rows. Label 60%–under-80% coverage `low confidence`; permit normal confidence only at 80% or higher. Use walk-forward empirical calibration when available. Without calibration, label results `启发式概率（未校准）`, cap confidence at low, and avoid false precision. Missing material microstructure data must actually reduce coverage; do not silently substitute neutral defaults.

Use `scripts/backtest.py` on strictly out-of-sample daily predictions and apply the same market-cap, freshness, coverage, and point-in-time regulatory filters historically. Maintain the T+1 limit-up label and, only when an expected-return model exists, the realized next-day return label. Prevent final-close data, future-day data, revised classifications, and later news from entering 14:40 features. Use at least two years when available; for qualifying stocks listed less than two years use all observations since listing and report them separately. Report sample count, excluded count, Brier score, log loss, calibration bins, Top-5/Top-10 hit rates, and results by board count, theme, total-market-cap bucket, and free-float-market-cap bucket.

Calibrate and evaluate first-board observations separately from second-board-and-higher observations because their base rates differ. If the first-board calibration sample is insufficient, label it `首板启发式概率（未校准）`; do not silently reuse a higher-board calibration curve.

## Output

Rank by calibrated T+1 continuation probability, then seal quality and confidence. Show ticker/name, `industry`, a concise `main_business`, board, theme, current board count, price change, seal duration, reopen count, queue and decay, turnover, volume ratio, total market cap, free-float market cap, free-float ratio, market-cap cohort, T+1 continuation probability, optional expected-return estimate, buyability percentage, late-break-risk percentage, business evidence, other evidence, uncertainty, and observable invalidation conditions. Industry and主营业务 must also appear in `强势未封板观察`, exclusions discussed by name, and `高概率但难买入` lists—not only in the top ranking.

Provide a `首板晋级概率榜`, a `二板及以上连板概率榜`, a separate `强势未封板观察`, and a separate `高概率但难买入` list. For a first-board row, T+1 means its probability of advancing from first board to second board. Do not mix the two probability rankings. If no reliable real-time data exists, output a data-quality failure report rather than a ranking.

Archive every run locally by China trading date. Read [scheduling and archive rules](references/scheduling.md) before installing or changing scheduled runs. Preserve both a human-readable Markdown report and machine-readable JSON for the 14:40 run. Historical comparisons must use archived point-in-time inputs and predictions rather than reconstructed values.

At 14:40, read `11-30-to-14-40-comparison.json` and use available changes in price, seal status, queue value, traded value, turnover rate, volume ratio, and sector breadth as supporting features. Distinguish afternoon new seals, still-sealed stocks, and morning seals that opened in the afternoon. Missing or incomparable observations remain null and reduce confidence; never reconstruct the 11:30 state from later data.

## Scheduling and validation

Run an intermediate collection LaunchAgent at 11:30 and the final analysis LaunchAgent at exactly 14:40 Asia/Shanghai. Do not schedule or generate a 09:25 opening review, a 14:20 scan, or a 14:50 update. The 11:30 task archives raw evidence only; the 14:40 task performs the comparison and remains the sole T+1 report. Archive a failed snapshot and report the failure. The runner must verify the SSE/SZSE trading calendar and exit on holidays or non-trading days. Scheduling starts research only and never touches a trading system.

> Research and model evaluation only; not personalized investment advice or a trading instruction.
