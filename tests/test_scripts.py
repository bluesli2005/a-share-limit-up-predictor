import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"scripts"))
from backtest import evaluate
from score_candidates import exclusion_reasons, is_eligible, score_one

def test_score_separates_probability_and_accessibility():
    row={"total_market_cap":20_000_000_000,"float_market_cap":12_000_000_000,"snapshot_age_seconds":20,"regulatory_exclusion":False,"emerging_industry_eligible":True,"emerging_industry_category":"next_generation_it","sealed_minutes":100,"queue_ratio":.95,"queue_decay":.02,"turnover_percentile":.55,"volume_ratio_percentile":.65,"float_market_cap_percentile":.35,"total_market_cap_percentile":.4,"float_share_ratio":.7,"theme_strength":.95,"leader_score":.9,"prior_board_quality":.9,"market_breadth":.8,"reopen_count":0}
    assert is_eligible(row)
    assert "emerging_industry_unverified_or_excluded" in exclusion_reasons({**row,"emerging_industry_eligible":None})
    assert "float_market_cap_below_or_missing" in exclusion_reasons({"total_market_cap":20_000_000_000,"float_market_cap":4_999_999_999,"snapshot_age_seconds":20,"regulatory_exclusion":False})
    r=score_one(row)
    assert r["next_trading_day_limit_up_probability_pct"]>65
    assert r["buyability_probability_pct"]<25
    assert r["two_day_continuation_probability_pct"]<=r["next_trading_day_limit_up_probability_pct"]
    assert r["t_plus_2_analysis_eligible"] is True
    assert r["label"]=="高概率但难买入"

def test_backtest_uses_all_new_stock_rows_and_cap_buckets():
    r=evaluate([{"trade_date":"2026-01-02","probability":.8,"second_day_probability":.5,"two_day_probability":.4,"next_day_limit_up":1,"second_day_limit_up":1,"listing_days":20,"float_market_cap":6_000_000_000,"total_market_cap":12_000_000_000,"snapshot_age_seconds":20,"regulatory_exclusion":False,"emerging_industry_eligible":True,"emerging_industry_category":"biomedicine_healthtech","feature_coverage":.9},{"trade_date":"2026-01-02","probability":.2,"second_day_probability":.3,"two_day_probability":.1,"next_day_limit_up":0,"second_day_limit_up":0,"listing_days":900,"float_market_cap":20_000_000_000,"total_market_cap":40_000_000_000,"snapshot_age_seconds":30,"regulatory_exclusion":False,"emerging_industry_eligible":True,"emerging_industry_category":"new_energy","feature_coverage":.8},{"trade_date":"2026-01-02","probability":.9,"next_day_limit_up":1,"listing_days":900,"float_market_cap":3_000_000_000,"total_market_cap":8_000_000_000,"snapshot_age_seconds":20,"regulatory_exclusion":False,"emerging_industry_eligible":True,"emerging_industry_category":"new_materials","feature_coverage":.9}])
    assert r["samples"]==2 and r["new_stock_samples"]==1
    assert r["excluded_by_universe_or_quality_filters"]==1
    assert r["by_float_market_cap"]["50–100亿"]["hit_rate"]==1.0
    assert r["by_total_market_cap"]["≥300亿"]["hit_rate"]==0.0
    assert r["t_plus_2_gate_samples"]==1
    assert r["second_trading_day_given_first_limit_up"]["samples"]==1
    assert r["two_day_continuation"]["samples"]==1

def test_t_plus_2_is_hidden_below_probability_gate():
    r=score_one({"board_count":2,"sealed_minutes":30,"queue_ratio":0,"queue_decay":1,"turnover_percentile":0,"volume_ratio_percentile":0,"float_market_cap_percentile":1,"total_market_cap_percentile":1,"float_share_ratio":0,"theme_strength":0,"leader_score":0,"prior_board_quality":0,"market_breadth":0,"reopen_count":3})
    assert r["next_trading_day_limit_up_probability_pct"]<=60
    assert r["t_plus_2_analysis_eligible"] is False
    assert r["second_day_limit_up_given_first_probability_pct"] is None
    assert r["two_day_continuation_probability_pct"] is None

def test_first_board_and_unsealed_candidates_are_grouped_separately():
    base={"sealed_minutes":60,"queue_ratio":.5,"queue_decay":.2,"turnover_percentile":.55,"volume_ratio_percentile":.65,"float_market_cap_percentile":.35,"total_market_cap_percentile":.4,"float_share_ratio":.7,"theme_strength":.8,"leader_score":.7,"prior_board_quality":.5,"market_breadth":.6,"reopen_count":0}
    assert score_one({**base,"board_count":1,"at_limit_up":True})["candidate_group"]=="first_board"
    assert score_one({**base,"board_count":2,"at_limit_up":True})["candidate_group"]=="higher_board"
    assert score_one({**base,"board_count":1,"at_limit_up":False})["candidate_group"]=="strong_unsealed"
