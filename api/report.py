"""
API endpoint: POST /api/report

Accepts a JSON body with damage report fields, validates them,
appends to data/damage-data.json, and returns HTTP 200 on success.

Deployment options (see DEPLOYMENT.md for details):
  - Run locally:  python api/report.py
  - Vercel/Render: expose via WSGI adapter (e.g. gunicorn api.report:app)
  - Cloudflare Workers: port logic to worker.js using the same schema

Required packages: flask
  pip install flask
"""

from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# Allow running the file directly without installing the package
try:
    from flask import Flask, request, jsonify
except ImportError:
    print("Flask is required. Install it with: pip install flask", file=sys.stderr)
    sys.exit(1)

app = Flask(__name__)

# Resolve paths relative to repository root (two levels up from api/)
REPO_ROOT = Path(__file__).parent.parent
_data_file_env = os.environ.get("DATA_FILE_PATH")
DATA_FILE = Path(_data_file_env) if _data_file_env else REPO_ROOT / "data" / "damage-data.json"

ALLOWED_SPECIES = {"サクラ", "モモ", "ウメ", "スモモ", "その他"}

# Thread-level lock to serialise concurrent writes
_write_lock = threading.Lock()

GIFU_MUNICIPALITIES = [
    "岐阜市", "大垣市", "高山市", "多治見市", "関市", "中津川市", "美濃市", "瑞浪市",
    "羽島市", "恵那市", "美濃加茂市", "土岐市", "各務原市", "可児市", "山県市", "瑞穂市",
    "飛騨市", "本巣市", "郡上市", "下呂市", "海津市", "岐南町", "笠松町", "養老町",
    "垂井町", "関ケ原町", "神戸町", "輪之内町", "安八町", "揖斐川町", "大野町", "池田町",
    "北方町", "坂祝町", "富加町", "川辺町", "七宗町", "八百津町", "白川町", "東白川村",
    "御嵩町", "白川村",
]


def extract_municipality(address: str) -> str:
    if not address:
        return ""
    for muni in GIFU_MUNICIPALITIES:
        if muni in address:
            return muni
    return ""


def _load_data() -> list:
    if not DATA_FILE.exists():
        return []
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_data(items: list) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _validate_photo_source(photo_source: str) -> tuple[str, str | None]:
    """Return (sanitised_value, error_message_or_None)."""
    if not photo_source:
        return "", None
    if photo_source.startswith("file:"):
        # Strip path separators to prevent path traversal
        filename = photo_source[len("file:"):]
        safe_name = os.path.basename(filename)
        return (f"file:{safe_name}" if safe_name else ""), None
    # Treat as URL — only allow http/https
    try:
        parsed = urlparse(photo_source)
    except Exception:
        return "", "写真URLが不正です"
    if parsed.scheme not in ("http", "https"):
        return "", "写真URLはhttpまたはhttpsで始まる必要があります"
    return photo_source, None


def _next_id(items: list) -> int:
    max_id = 0
    for item in items:
        if isinstance(item.get("id"), int) and item["id"] > max_id:
            max_id = item["id"]
    return max_id + 1


@app.route("/api/report", methods=["POST"])
def receive_report():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "リクエストボディが不正です"}), 400

    # --- Validation ---
    date = str(data.get("date", "")).strip()
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    species = str(data.get("species", "")).strip()
    if species not in ALLOWED_SPECIES:
        return jsonify({"error": "樹種が不正です"}), 400

    removal_raw = data.get("removal_count", "")
    if removal_raw != "" and removal_raw is not None:
        try:
            removal_count = int(removal_raw)
            if removal_count < 0:
                return jsonify({"error": "駆除数は0以上で入力してください"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "駆除数は整数で入力してください"}), 400
    else:
        removal_count = ""

    lat = data.get("lat")
    lng = data.get("lng")
    if lat is not None:
        try:
            lat = float(lat)
            if not (-90 <= lat <= 90):
                return jsonify({"error": "緯度の値が正しくありません"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "緯度の値が正しくありません"}), 400
    if lng is not None:
        try:
            lng = float(lng)
            if not (-180 <= lng <= 180):
                return jsonify({"error": "経度の値が正しくありません"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "経度の値が正しくありません"}), 400

    # --- Build entry ---
    address = str(data.get("address", "")).strip()
    photo_source, photo_err = _validate_photo_source(str(data.get("photo_source", "")).strip())
    if photo_err:
        return jsonify({"error": photo_err}), 400

    if photo_source.startswith("file:"):
        photo_file = photo_source[len("file:"):]
        photo_url = ""
        photo = ""
    else:
        photo_file = ""
        photo_url = photo_source
        photo = photo_source

    entry = {
        "date": date,
        "species": species,
        "frass": str(data.get("frass", "")).strip(),
        "exit_hole": str(data.get("exit_hole", "")).strip(),
        "removal_count": removal_count,
        "removal_count_note": str(data.get("removal_count_note", "")).strip(),
        "severity": str(data.get("severity", "")).strip(),
        "damage": str(data.get("severity", "")).strip(),
        "memo": str(data.get("memo", "")).strip(),
        "address": address,
        "municipality": extract_municipality(address),
        "photo_file": photo_file,
        "photo_url": photo_url,
        "photo": photo,
        "lat": lat,
        "lng": lng,
    }

    # --- Persist (lock to prevent concurrent write conflicts) ---
    with _write_lock:
        items = _load_data()
        entry["id"] = _next_id(items)
        items.append(entry)
        _save_data(items)

    return jsonify({"ok": True, "id": entry["id"]}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
