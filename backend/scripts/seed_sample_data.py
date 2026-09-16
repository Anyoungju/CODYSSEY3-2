"""Create 366 deterministic daily weather-like records in Firestore."""
from __future__ import annotations

import math
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))
from app.repository import db, now


def build_records() -> list[dict]:
    """Return one year of repeatable daily temperature data."""
    start = date(2024, 1, 1)
    records = []
    for day in range(366):
        current = start + timedelta(days=day)
        value = round(10.5 + 14 * math.sin((day - 80) * math.tau / 366) + 1.8 * math.sin(day * 0.59), 1)
        records.append({"date": current.isoformat(), "value": value, "memo": "서울 일평균 기온", "created_at": now(), "updated_at": now()})
    return records


def main() -> None:
    """Write the prepared 366 records using Firestore batch commits."""
    client = db()
    for offset in range(0, 366, 450):
        batch = client.batch()
        for record in build_records()[offset:offset + 450]:
            ref = client.collection("data").document()
            batch.set(ref, record)
        batch.commit()
    print("Seeded 366 records in the data collection.")


if __name__ == "__main__":
    main()
