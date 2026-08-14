#!/usr/bin/env python3
"""
process_report.py — Append a single damage report to data/damage-data.json.

Usage (called by api/report.py or manually):
    python3 scripts/process_report.py <json-file>

The JSON file must contain a single object with the following optional keys:
    date, species, frass, exit_hole, removal_count, removal_count_note,
    severity, memo, address, lat, lng, photo_source

Outputs the appended entry's id to stdout.
"""
import sys
import json
import os
from datetime import datetime, timezone

GIFU_MUNICIPALITIES = [
    '岐阜市', '大垣市', '高山市', '多治見市', '関市', '中津川市', '美濃市', '瑞浪市', '羽島市', '恵那市',
    '美濃加茂市', '土岐市', '各務原市', '可児市', '山県市', '瑞穂市', '飛騨市', '本巣市', '郡上市', '下呂市', '海津市',
    '岐南町', '笠松町', '養老町', '垂井町', '関ケ原町', '神戸町', '輪之内町', '安八町', '揖斐川町', '大野町', '池田町',
    '北方町', '坂祝町', '富加町', '川辺町', '七宗町', '八百津町', '白川町', '東白川村', '御嵩町', '白川村',
]


def extract_municipality(address):
    if not address:
        return ""
    for muni in GIFU_MUNICIPALITIES:
        if muni in address:
            return muni
    return ""


def build_entry(data):
    date = str(data.get("date", "")).strip()
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    photo_source = str(data.get("photo_source", "")).strip()
    if photo_source.startswith("file:"):
        photo_file = photo_source[len("file:"):]
        photo_url = ""
        photo = ""
    else:
        photo_file = ""
        photo_url = photo_source
        photo = photo_source

    address = str(data.get("address", "")).strip()

    lat = data.get("lat")
    lng = data.get("lng")
    try:
        lat = float(lat) if lat not in (None, "") else None
    except (ValueError, TypeError):
        lat = None
    try:
        lng = float(lng) if lng not in (None, "") else None
    except (ValueError, TypeError):
        lng = None

    removal_raw = data.get("removal_count", "")
    try:
        removal_count = int(removal_raw) if removal_raw not in (None, "") else ""
    except (ValueError, TypeError):
        removal_count = ""

    severity = str(data.get("severity", "")).strip()

    return {
        "date": date,
        "species": str(data.get("species", "")).strip(),
        "frass": str(data.get("frass", "")).strip(),
        "exit_hole": str(data.get("exit_hole", "")).strip(),
        "removal_count": removal_count,
        "removal_count_note": str(data.get("removal_count_note", "")).strip(),
        "severity": severity,
        "damage": severity,
        "memo": str(data.get("memo", "")).strip(),
        "address": address,
        "municipality": extract_municipality(address),
        "photo_file": photo_file,
        "photo_url": photo_url,
        "photo": photo,
        "lat": lat,
        "lng": lng,
    }


def append_to_data(entry, json_path="data/damage-data.json"):
    if not os.path.exists(json_path):
        items = []
    else:
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                items = json.load(f)
            except json.JSONDecodeError:
                items = []

    max_id = 0
    for it in items:
        if isinstance(it.get("id"), int) and it["id"] > max_id:
            max_id = it["id"]

    entry["id"] = max_id + 1
    items.append(entry)

    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    return entry["id"]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: process_report.py <json-file>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)

    entry = build_entry(data)
    new_id = append_to_data(entry)
    print(f"Appended entry id={new_id}")
