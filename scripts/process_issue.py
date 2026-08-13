#!/usr/bin/env python3
import sys
import json
import os
from datetime import datetime

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
entry["photo"] = data.get("写真URL", "")
entry["address"] = data.get("住所", "")

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
