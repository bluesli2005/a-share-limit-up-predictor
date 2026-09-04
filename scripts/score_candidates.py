#!/usr/bin/env python3
"""Deterministic candidate scorer; standard-library only."""
import argparse, json, math

FEATURES = {"sealed_minutes": .13, "queue_ratio": .15, "queue_stability": .11,
            "turnover_quality": .10, "volume_quality": .07, "theme_strength": .12,
            "leader_score": .09, "prior_board_quality": .07, "market_breadth": .05,
            "capitalization_quality": .11}
MIN_TOTAL_MARKET_CAP = 10_000_000_000
MIN_FLOAT_MARKET_CAP = 5_000_000_000
MAX_SNAPSHOT_AGE_SECONDS = 60
MIN_FEATURE_COVERAGE = .60
NORMAL_FEATURE_COVERAGE = .80
T_PLUS_2_ANALYSIS_THRESHOLD = .60

def clamp(value): return max(0.0, min(1.0, float(value)))

def centered_quality(value, center):
    return clamp(1 - abs(clamp(value) - center) / max(center, 1-center))

def exclusion_reasons(row):
    reasons = []
    total = row.get("total_market_cap")
    floating = row.get("float_market_cap")
    age = row.get("snapshot_age_seconds")
    regulatory = row.get("regulatory_exclusion")
    emerging = row.get("emerging_industry_eligible")
    category = row.get("emerging_industry_category")
    if total is None or float(total) < MIN_TOTAL_MARKET_CAP: reasons.append("total_market_cap_below_or_missing")
    if floating is None or float(floating) < MIN_FLOAT_MARKET_CAP: reasons.append("float_market_cap_below_or_missing")
    if age is None or float(age) > MAX_SNAPSHOT_AGE_SECONDS: reasons.append("snapshot_stale_or_missing")
    if regulatory is None or bool(regulatory): reasons.append("regulatory_status_unverified_or_excluded")
    if emerging is not True: reasons.append("emerging_industry_unverified_or_excluded")
    if not category: reasons.append("emerging_industry_category_missing")
    return reasons

def is_eligible(row): return not exclusion_reasons(row)

def transform(raw, function):
    return None if raw is None else function(raw)

def score_one(row):
    values = dict(row)
    values["sealed_minutes"] = transform(row.get("sealed_minutes"), lambda x: clamp((float(x)-30)/90))
    values["queue_stability"] = transform(row.get("queue_decay"), lambda x: 1-clamp(x))
    values["turnover_quality"] = transform(row.get("turnover_percentile"), lambda x: 1-abs(clamp(x)-.55)/.55)
    values["volume_quality"] = transform(row.get("volume_ratio_percentile"), lambda x: 1-abs(clamp(x)-.65)/.65)
    cap_fields=(row.get("float_market_cap_percentile"),row.get("total_market_cap_percentile"),row.get("float_share_ratio"))
    values["capitalization_quality"] = None if any(v is None for v in cap_fields) else clamp(.45*centered_quality(cap_fields[0],.35)+.30*centered_quality(cap_fields[1],.40)+.25*clamp(cap_fields[2]))
    weighted = covered = 0.0; missing = []
    for name, weight in FEATURES.items():
        if values.get(name) is None: missing.append(name); continue
        weighted += clamp(values[name]) * weight; covered += weight
    raw = clamp(weighted / covered - min(.24, int(row.get("reopen_count", 0)) * .04)) if covered else 0
    probability = 1 / (1 + math.exp(-5 * (raw - .5)))
    board_count = max(1, int(row.get("board_count", 1)))
    at_limit_up = bool(row.get("at_limit_up", True))
    candidate_group = "first_board" if board_count == 1 and at_limit_up else "higher_board" if board_count >= 2 and at_limit_up else "strong_unsealed"
    conditional_day_two = clamp(.68 + .12*clamp(row.get("theme_strength",0)) + .08*clamp(row.get("leader_score",0)) - .05*max(0,board_count-1) - .10*clamp(row.get("queue_decay",1)) - .04*int(row.get("reopen_count",0)))
    two_day_probability = probability * conditional_day_two
    analyze_t_plus_2 = probability > T_PLUS_2_ANALYSIS_THRESHOLD
    accessibility = clamp(.45 * (1-clamp(row.get("queue_ratio", 0))) + .20 * clamp(row.get("turnover_percentile", .5)) + .15 * clamp(row.get("float_market_cap_percentile", .5)) + .20 * min(1, int(row.get("reopen_count", 0))/3))
    late_break = clamp(.45*clamp(row.get("queue_decay", 1)) + .10*int(row.get("reopen_count", 0)) + .25*(1-clamp(row.get("theme_strength", 0))) + .20*(1-clamp(row.get("market_breadth", 0))))
    confidence = "normal" if covered >= NORMAL_FEATURE_COVERAGE else "low" if covered >= MIN_FEATURE_COVERAGE else "insufficient"
    result = dict(row); result.update({"next_trading_day_limit_up_probability_pct": round(probability*100,1), "t_plus_2_analysis_eligible": analyze_t_plus_2, "t_plus_2_analysis_status": "analyzed" if analyze_t_plus_2 else "below_60_percent_t_plus_1_gate", "second_day_limit_up_given_first_probability_pct": round(conditional_day_two*100,1) if analyze_t_plus_2 else None, "two_day_continuation_probability_pct": round(two_day_probability*100,1) if analyze_t_plus_2 else None, "probability_type": "heuristic_uncalibrated", "buyability_probability_pct": round(accessibility*100,1), "late_break_risk_pct": round(late_break*100,1), "capitalization_quality": None if values["capitalization_quality"] is None else round(values["capitalization_quality"],3), "feature_coverage": round(covered,3), "confidence": confidence, "missing_features": missing, "label": "高概率但难买入" if probability >= .65 and accessibility < .25 else "候选"})
    result["candidate_group"] = candidate_group
    return result

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--input", required=True); parser.add_argument("--output"); args=parser.parse_args()
    with open(args.input, encoding="utf-8") as f: rows=json.load(f)
    scored=(score_one(r) for r in rows if is_eligible(r))
    results=sorted((r for r in scored if r["feature_coverage"] >= MIN_FEATURE_COVERAGE), key=lambda x:x["next_trading_day_limit_up_probability_pct"], reverse=True)
    text=json.dumps(results, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output,"w",encoding="utf-8") as f: f.write(text+"\n")
    else: print(text)
if __name__ == "__main__": main()
