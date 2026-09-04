#!/usr/bin/env python3
"""Evaluate out-of-sample JSONL predictions; standard-library only."""
import argparse, collections, json, math
MIN_TOTAL_MARKET_CAP = 10_000_000_000
MIN_FLOAT_MARKET_CAP = 5_000_000_000
MAX_SNAPSHOT_AGE_SECONDS = 60
MIN_FEATURE_COVERAGE = .60
T_PLUS_2_ANALYSIS_THRESHOLD = .60

def cap_bucket(value):
    if value is None: return "missing"
    value=float(value)
    if value < 5_000_000_000: return "<50亿"
    if value < 10_000_000_000: return "50–100亿"
    if value < 30_000_000_000: return "100–300亿"
    return "≥300亿"

def grouped_stats(rows, field):
    groups=collections.defaultdict(list)
    for r in rows: groups[cap_bucket(r.get(field))].append(r)
    return {name:{"samples":len(group),"hit_rate":round(sum(r["next_day_limit_up"] for r in group)/len(group),4),"brier_score":round(sum((float(r["probability"])-r["next_day_limit_up"])**2 for r in group)/len(group),5)} for name,group in sorted(groups.items())}

def horizon_metrics(rows, probability_field, label_function):
    usable=[r for r in rows if r.get(probability_field) is not None and label_function(r) in (0,1)]
    if not usable: return None
    pairs=[(max(1e-6,min(1-1e-6,float(r[probability_field]))),label_function(r)) for r in usable]
    return {"samples":len(pairs),"brier_score":round(sum((p-y)**2 for p,y in pairs)/len(pairs),5),"log_loss":round(sum(-(y*math.log(p)+(1-y)*math.log(1-p)) for p,y in pairs)/len(pairs),5),"hit_rate":round(sum(y for _,y in pairs)/len(pairs),4)}

def evaluate(rows):
    labeled=[r for r in rows if r.get("next_day_limit_up") in (0,1)]
    valid=[r for r in labeled if r.get("total_market_cap") is not None and float(r["total_market_cap"]) >= MIN_TOTAL_MARKET_CAP and r.get("float_market_cap") is not None and float(r["float_market_cap"]) >= MIN_FLOAT_MARKET_CAP and r.get("snapshot_age_seconds") is not None and float(r["snapshot_age_seconds"]) <= MAX_SNAPSHOT_AGE_SECONDS and r.get("regulatory_exclusion") is False and r.get("emerging_industry_eligible") is True and bool(r.get("emerging_industry_category")) and float(r.get("feature_coverage",0)) >= MIN_FEATURE_COVERAGE]
    if not valid: raise ValueError("No labeled predictions.")
    brier=sum((float(r["probability"])-r["next_day_limit_up"])**2 for r in valid)/len(valid)
    loss=0.; bins=collections.defaultdict(lambda:[0,0.,0.]); days=collections.defaultdict(list)
    for r in valid:
        p=max(1e-6,min(1-1e-6,float(r["probability"]))); y=r["next_day_limit_up"]
        loss-=y*math.log(p)+(1-y)*math.log(1-p); b=min(9,int(p*10)); bins[b][0]+=1; bins[b][1]+=p; bins[b][2]+=y; days[r["trade_date"]].append(r)
    result={"samples":len(valid),"excluded_by_universe_or_quality_filters":len(labeled)-len(valid),"minimum_total_market_cap":MIN_TOTAL_MARKET_CAP,"minimum_float_market_cap":MIN_FLOAT_MARKET_CAP,"maximum_snapshot_age_seconds":MAX_SNAPSHOT_AGE_SECONDS,"minimum_feature_coverage":MIN_FEATURE_COVERAGE,"brier_score":round(brier,5),"log_loss":round(loss/len(valid),5),"new_stock_samples":sum(1 for r in valid if int(r.get("listing_days",999999))<730)}
    for k in (5,10):
        rates=[]
        for group in days.values():
            chosen=sorted(group,key=lambda r:r["probability"],reverse=True)[:k]; rates.append(sum(r["next_day_limit_up"] for r in chosen)/len(chosen))
        result[f"top_{k}_mean_hit_rate"]=round(sum(rates)/len(rates),4)
    result["calibration"]=[{"bin":f"{i/10:.1f}-{(i+1)/10:.1f}","n":v[0],"mean_probability":round(v[1]/v[0],3),"hit_rate":round(v[2]/v[0],3)} for i,v in sorted(bins.items())]
    result["by_float_market_cap"] = grouped_stats(valid,"float_market_cap")
    result["by_total_market_cap"] = grouped_stats(valid,"total_market_cap")
    gated=[r for r in valid if float(r["probability"]) > T_PLUS_2_ANALYSIS_THRESHOLD]
    conditional=[r for r in gated if r.get("next_day_limit_up") == 1]
    result["t_plus_2_analysis_threshold"] = T_PLUS_2_ANALYSIS_THRESHOLD
    result["t_plus_2_gate_samples"] = len(gated)
    result["second_trading_day_given_first_limit_up"] = horizon_metrics(conditional,"second_day_probability",lambda r:r.get("second_day_limit_up"))
    result["two_day_continuation"] = horizon_metrics(gated,"two_day_probability",lambda r:r.get("next_day_limit_up")*r.get("second_day_limit_up") if r.get("second_day_limit_up") in (0,1) else None)
    return result

def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); a=p.parse_args()
    with open(a.input,encoding="utf-8") as f: rows=[json.loads(x) for x in f if x.strip()]
    print(json.dumps(evaluate(rows),ensure_ascii=False,indent=2))
if __name__ == "__main__": main()
