# Deployment Guide — API-based Reporting

## Overview

The reporting flow no longer depends on GitHub Issues.  
`report.html` now POSTs JSON to `POST /api/report`, which validates the payload,
extracts the municipality from the address, and appends the entry to
`data/damage-data.json`.  `index.html` reads that same JSON file and is unchanged.

```
report.html  →  POST /api/report  →  data/damage-data.json  →  index.html
```

---

## API contract

**Endpoint:** `POST /api/report`  
**Content-Type:** `application/json`

### Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `date` | string (YYYY-MM-DD) | no | Discovery date (defaults to today) |
| `species` | string | yes | Tree species (`サクラ`/`モモ`/`ウメ`/`スモモ`/`その他`) |
| `frass` | string | no | `あり` or `なし` |
| `exit_hole` | string | no | `あり` or `なし` |
| `removal_count` | number or `""` | no | Number of insects removed |
| `removal_count_note` | string | no | Free-text supplement |
| `severity` | string | no | Auto-classified by `report.html` |
| `memo` | string | no | Free-text notes |
| `address` | string | no | Full address string |
| `lat` | number or null | no | Latitude |
| `lng` | number or null | no | Longitude |
| `photo_source` | string | no | Photo URL or `file:<filename>` |

### Response

| Status | Body | Meaning |
|---|---|---|
| 200 | `{ "ok": true, "id": <number> }` | Report accepted |
| 400 | `{ "error": "<message>" }` | Validation error |

---

## Running locally

```bash
pip install flask
python api/report.py
# Server starts on http://localhost:5000
```

---

## Deployment options

### Option A — Vercel (recommended for static + API)

1. Add `vercel.json` at the repo root:

```json
{
  "rewrites": [{ "source": "/api/(.*)", "destination": "/api/$1" }]
}
```

2. Vercel auto-detects `api/report.py` as a serverless function.
3. Set the environment variable `DATA_FILE_PATH` if you want to point to a
   writable volume (Vercel functions are ephemeral — see note below).

### Option B — Render / Railway / Fly.io

Deploy as a standard Flask app:

```bash
pip install flask gunicorn
gunicorn "api.report:app" --bind 0.0.0.0:$PORT
```

### Option C — Cloudflare Workers (JavaScript port)

Port `api/report.py` to a Worker that writes to Cloudflare KV or R2 instead of
the local filesystem.  The JSON schema and validation logic remain the same.

---

## Important note on persistent storage

`api/report.py` writes directly to `data/damage-data.json` on disk.  
This works well when:
- Running locally for development
- Deploying to a server with a persistent volume (Option B)

On **serverless/ephemeral** platforms (Vercel, Cloudflare Workers) the filesystem
is read-only or ephemeral.  In that case, replace the `_load_data` / `_save_data`
calls in `api/report.py` with a suitable persistent store (e.g. a database, blob
storage, or a GitHub API commit).

---

## Deprecated files

The following files from the old GitHub-Issue-based flow are **no longer used**
and can be removed once the API deployment is confirmed working:

| File | Reason deprecated |
|---|---|
| `.github/workflows/issue-to-json.yml` | Triggered on Issue creation; no longer needed |
| `scripts/process_issue.py` | Parsed GitHub Issue text; replaced by `scripts/process_report.py` |
| `.github/ISSUE_TEMPLATE/report.md` | Issue template for the old flow |

`scripts/process_report.py` is the new equivalent of `process_issue.py` and
accepts a plain JSON file instead of a GitHub event payload.
