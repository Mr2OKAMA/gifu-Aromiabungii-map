#!/usr/bin/env python3
import sys
import json
import os
import re
from datetime import datetime

GIFU_MUNICIPALITIES = [
    '岐阜市','大垣市','高山市','多治見市','関市','中津川市','美濃市','瑞浪市','羽島市','恵那市',
    '美濃加茂市','土岐市','各務原市','可児市','山県市','瑞穂市','飛騨市','本巣市','郡上市','下呂市','海津市',
    '岐南町','笠松町','養老町','垂井町','関ケ原町','神戸町','輪之内町','安八町','揖斐川町','大野町','池田町',
    '北方町','坂祝町','富加町','川辺町','七宗町','八百津町','白川町','東白川村','御嵩町','白川村'
]

if len(sys.argv) < 2:
    print("Missing event path arg")
    sys.exit(1)

event_path = sys.argv[1]
with open(event_path, "r", encoding="utf-8") as f:
    event = json.load(f)

issue = event.get("issue", {})
body = issue.get("body", "") or ""
created_at = issue.get("created_at")
issue_number = issue.get("number")

data = {}
for line in body.splitlines():
    if ":" in line:
        k, v = line.split(":", 1)
        data[k.strip()] = v.strip()

def extract_municipality(address):
    if not address:
        return ""
    for muni in GIFU_MUNICIPALITIES:
        if muni in address:
            return muni
    return ""

entry = {}

if data.get("発見日"):
    entry["date"] = data["発見日"]
elif created_at:
    entry["date"] = created_at.split("T")[0]
else:
    entry["date"] = datetime.utcnow().strftime("%Y-%m-%d")

entry["species"] = data.get("樹種", "")
entry["frass"] = data.get("フラス", "")
entry["exit_hole"] = data.get("脱出食痕", "")
entry["removal_count"] = data.get("駆除数", "")
entry["removal_count_note"] = data.get("駆除数補足", "")
entry["severity"] = data.get("分類", data.get("被害", ""))
entry["damage"] = entry["severity"]
entry["memo"] = data.get("備考", "")
entry["address"] = data.get("住所", "")
entry["municipality"] = extract_municipality(entry["address"])

photo_source = data.get("写真URL", "")
if photo_source.startswith("file:"):
    entry["photo_file"] = photo_source.replace("file:", "", 1)
    entry["photo_url"] = ""
    entry["photo"] = ""
else:
    entry["photo_file"] = ""
    entry["photo_url"] = photo_source
    entry["photo"] = photo_source

lat = data.get("緯度", "")
lng = data.get("経度", "")

try:
    entry["lat"] = float(lat) if lat else None
except:
    entry["lat"] = None

try:
    entry["lng"] = float(lng) if lng else None
except:
    entry["lng"] = None

json_path = "data/damage-data.json"
if not os.path.exists(json_path):
    items = []
else:
    with open(json_path, "r", encoding="utf-8") as f:
        try:
            items = json.load(f)
        except:
            items = []

max_id = 0
for it in items:
    if isinstance(it.get("id"), int) and it["id"] > max_id:
        max_id = it["id"]

entry["id"] = max_id + 1
items.append(entry)

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f"Appended entry id={entry['id']} from issue #{issue_number}")
