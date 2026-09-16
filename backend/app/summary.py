"""Pure time-series summary logic."""
from __future__ import annotations
from statistics import mean


def build_summary(records: list[dict]) -> dict:
    """Build prompt-ready statistics from date-sorted records."""
    if not records:
        return {"period": "데이터 없음", "count": 0, "metrics": {}, "trend": "판단 불가"}
    items = sorted(records, key=lambda item: item["date"])
    values = [float(item["value"]) for item in items]
    recent = values[-7:]
    previous = values[-14:-7]
    delta = mean(recent) - mean(previous) if previous else 0
    trend = "상승" if delta > 0.01 else "하락" if delta < -0.01 else "유지"
    high, low = max(items, key=lambda x: x["value"]), min(items, key=lambda x: x["value"])
    return {"period": f"{items[0]['date']} ~ {items[-1]['date']}", "count": len(items), "metrics": {"average": round(mean(values), 2), "max": high["value"], "min": low["value"], "recent_7_day_average": round(mean(recent), 2)}, "extremes": {"max_date": high["date"], "min_date": low["date"]}, "trend": f"{trend} (최근 7일 평균 변화 {delta:+.2f})"}
