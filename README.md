# HN Claude + PowerPoint + Startup Jobs Scraper

This repo mirrors the **shot-scraper + JS** pattern from `simonw/scrape-hacker-news-by-domain`, but targets:
- **Startup jobs** (HN Jobs pages)
- **Claude + PowerPoint** news (Algolia API keyword queries)
- **OpenClaw + PowerPoint** news (Algolia API keyword queries)

## How it works
- **HN Jobs**: `shot-scraper` runs `scrape_hn_list.js` against `news.ycombinator.com/jobs` (first 2 pages).
- **Keyword queries**: `scrape_queries.py` calls the HN Algolia API using the queries in `queries.json`.
- **Filtering**: `filter_results.py` creates `hn_powerpoint.json` from `hn_queries.json`.
- Outputs are stored as JSON with `generated_at`, `count`, and `results`.

## Files
- `scrape_hn_list.js`: Browser-side scraper for HN list pages.
- `scrape_jobs.sh`: Scrapes HN jobs pages via shot-scraper.
- `scrape_queries.py`: Pulls keyword hits from Algolia API.
- `queries.json`: Configurable keyword queries.
- `filter_results.py`: Regex (default) or LLM filter for PowerPoint/Claude-related items.
- `merge_json.py`: Deduplicates and packages output.

## Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
shot-scraper install
```

## Run
```bash
./scrape_all.sh
```

Outputs:
- `hn_jobs.json`
- `hn_queries.json`
- `hn_powerpoint.json`

## Filtering
### Regex (default)
Edit keywords in `filter_results.py` or pass a custom set:
```bash
python filter_results.py --in hn_queries.json --out hn_powerpoint.json --mode regex \
  --keywords "powerpoint|pptx|ppt|slides|presentation|claude|anthropic|openclaw|visa sponsorship|visa support|h1b|sponsorship|hiring|jobs" \
  --max-days 14
```

### NVIDIA LLM (optional)
If you want a smarter classifier:
```bash
export NVIDIA_API_KEY="your_key"
python filter_results.py --in hn_queries.json --out hn_powerpoint.json --mode llm --model z-ai/glm5 \
  --llm-limit 20 --max-days 14 --seen-file seen_ids.json
```

## Latest PowerPoint/Claude-related items
<!-- HN_TABLE_START -->
| HN link | App/External link | Posted | PPTX present | Match mode |
|---|---|---|---|---|
| (none) | | | | |

_Last updated: 2026-08-17T16:44:45.740580Z_
<!-- HN_TABLE_END -->

## GitHub Actions
Runs hourly and auto-commits JSON outputs + README updates.

## Warehouse Runner — check an item across all warehouses

`warehouse_check.py` checks one item's price/availability across **every**
warehouse via the Warehouse Runner backend (`api-runner.a-ok.app`).

That backend is a private, undocumented mobile API (Cloudflare-fronted; only
`GET /` responds, returning `"Annie is OK"` — every other route probed returns
`404`). The route names, auth token, and request body are only knowable from a
real request the app makes. So this tool is **capture-driven**: capture one
request, and it replays that request across all warehouses concurrently.

### Capturing a request

Point the phone's traffic at an HTTPS-inspecting proxy and search one item in
the app, then grab the request to `api-runner.a-ok.app`:

- **Proxyman** or **Charles Proxy** (Mac) — install the proxy's CA cert on the
  phone, "Enable SSL Proxying" for `api-runner.a-ok.app`, do a search, then
  right-click the request → *Copy → cURL*.
- **mitmproxy** (`mitmproxy` / `mitmweb`) — same idea; export the flow as curl.

Save the copied `curl ...` into a text file (e.g. `captured.txt`).

### Build the config

```bash
python warehouse_check.py import-curl captured.txt -o runner_config.json
```

Then edit `runner_config.json` (see `runner_config.example.json`):

1. In `endpoint`/`body`, replace the captured warehouse id with `{warehouse_id}`
   and the searched term with `{item}`.
2. Fill in `warehouses` — one `{ "id": ..., "name": ... }` per warehouse. (The
   warehouse-list request in the app is itself a request you can capture the
   same way.)
3. Set the `extract` dotted paths to the price/availability/name fields in the
   JSON response. Unresolved rows print the raw payload so you can find them.

### Run

```bash
python warehouse_check.py check "organic milk" -c runner_config.json -o results.json
```

```
Item: organic milk   (3 warehouses)

Warehouse                 Price   Avail  Notes
----------------------------------------------
Costco Seattle #12         9.49     yes  Kirkland Organic Milk
Costco Portland #34        8.99      no  Kirkland Organic Milk
Costco Boise #56           9.99     yes  Kirkland Organic Milk
```

Placeholders substituted per request: `{warehouse_id}`, `{item}` (URL-encoded),
`{item_raw}`. Requests run concurrently (`-w` to tune). Only depends on
`requests`.

> The other domains in the app's privacy report are Apple's, not the Runner
> backend: `amp-api-edge.apps.apple.com` (App Store catalog), `mzstorekit.itunes.apple.com`
> (StoreKit / in-app purchases), `gsp-ssl.ls.apple.com` (Apple location service).
