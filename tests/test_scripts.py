import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"scripts"))
from backtest import evaluate
from score_candidates import exclusion_reasons, is_eligible, score_one
from collect_market_data import normalize_sina_records
from compare_intraday_snapshots import compare

def test_sina_market_cap_units_and_bse_filter():
    rows=normalize_sina_records([
        {"symbol":"sz000001","code":"000001","name":"测试","trade":"10.5","changepercent":9.1,"volume":1000,"amount":2000,"settlement":"9.6","open":"9.7","high":"10.6","low":"9.5","mktcap":123456,"nmc":65432,"turnoverratio":2.5,"ticktime":"14:40:03"},
        {"symbol":"bj920001","code":"920001","name":"北交所"},
    ],"2026-09-10T14:40:04+08:00")
    assert len(rows)==1
    assert rows[0]["total_market_cap"]==1_234_560_000
    assert rows[0]["float_market_cap"]==654_320_000
    assert rows[0]["volume_lot"]==10
    assert rows[0]["provider_quote_time"]=="14:40:03"

def test_score_separates_probability_and_accessibility():
    row={"total_market_cap":20_000_000_000,"float_market_cap":12_000_000_000,"snapshot_age_seconds":20,"regulatory_exclusion":False,"emerging_industry_eligible":True,"emerging_industry_category":"next_generation_it","sealed_minutes":100,"queue_ratio":.95,"queue_decay":.02,"turnover_percentile":.55,"volume_ratio_percentile":.65,"float_market_cap_percentile":.35,"total_market_cap_percentile":.4,"float_share_ratio":.7,"theme_strength":.95,"leader_score":.9,"prior_board_quality":.9,"market_breadth":.8,"reopen_count":0}
    assert is_eligible(row)
    assert "emerging_industry_unverified_or_excluded" in exclusion_reasons({**row,"emerging_industry_eligible":None})
    assert "float_market_cap_below_or_missing" in exclusion_reasons({"total_market_cap":20_000_000_000,"float_market_cap":4_999_999_999,"snapshot_age_seconds":20,"regulatory_exclusion":False})
    r=score_one(row)
    assert r["next_trading_day_limit_up_probability_pct"]>65
    assert r["buyability_probability_pct"]<25
    assert "two_day_continuation_probability_pct" not in r
    assert r["expected_return_status"]=="requires_separately_calibrated_return_model"
    assert r["label"]=="高概率但难买入"

def test_backtest_uses_all_new_stock_rows_and_cap_buckets():
    r=evaluate([{"trade_date":"2026-01-02","probability":.8,"next_day_limit_up":1,"listing_days":20,"float_market_cap":6_000_000_000,"total_market_cap":12_000_000_000,"snapshot_age_seconds":20,"regulatory_exclusion":False,"emerging_industry_eligible":True,"emerging_industry_category":"biomedicine_healthtech","feature_coverage":.9},{"trade_date":"2026-01-02","probability":.2,"next_day_limit_up":0,"listing_days":900,"float_market_cap":20_000_000_000,"total_market_cap":40_000_000_000,"snapshot_age_seconds":30,"regulatory_exclusion":False,"emerging_industry_eligible":True,"emerging_industry_category":"new_energy","feature_coverage":.8},{"trade_date":"2026-01-02","probability":.9,"next_day_limit_up":1,"listing_days":900,"float_market_cap":3_000_000_000,"total_market_cap":8_000_000_000,"snapshot_age_seconds":20,"regulatory_exclusion":False,"emerging_industry_eligible":True,"emerging_industry_category":"new_materials","feature_coverage":.9}])
    assert r["samples"]==2 and r["new_stock_samples"]==1
    assert r["excluded_by_universe_or_quality_filters"]==1
    assert r["by_float_market_cap"]["50–100亿"]["hit_rate"]==1.0
    assert r["by_total_market_cap"]["≥300亿"]["hit_rate"]==0.0

def test_first_board_and_unsealed_candidates_are_grouped_separately():
    base={"sealed_minutes":60,"queue_ratio":.5,"queue_decay":.2,"turnover_percentile":.55,"volume_ratio_percentile":.65,"float_market_cap_percentile":.35,"total_market_cap_percentile":.4,"float_share_ratio":.7,"theme_strength":.8,"leader_score":.7,"prior_board_quality":.5,"market_breadth":.6,"reopen_count":0}
    assert score_one({**base,"board_count":1,"at_limit_up":True})["candidate_group"]=="first_board"
    assert score_one({**base,"board_count":2,"at_limit_up":True})["candidate_group"]=="higher_board"
    assert score_one({**base,"board_count":1,"at_limit_up":False})["candidate_group"]=="strong_unsealed"

def test_midday_comparison_tracks_seal_and_flow_changes():
    market=lambda pct, amount, turnover, ratio: {"status":"success","records":[{"ticker":"000001","name":"测试","industry":"半导体","pct_change":pct,"turnover_value":amount,"turnover_rate":turnover,"volume_ratio":ratio,"total_market_cap":20_000_000_000,"float_market_cap":10_000_000_000}]}
    pool=lambda queue, reopen: {"status":"success","records":[{"ticker":"000001","name":"测试","queue_value":queue,"reopen_count":reopen}]}
    result=compare(market(9,100,2,1.5),pool(100,0),market(10,180,3,1.8),pool(150,1))
    row=result["records"][0]
    assert result["status"]=="success"
    assert row["seal_event"]=="afternoon_resealed"
    assert row["queue_value_change_pct"]==50.0
    assert row["turnover_value_delta"]==80.0
    assert row["afternoon_strength"]=="strengthened"
