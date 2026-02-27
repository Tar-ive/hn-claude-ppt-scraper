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
| https://news.ycombinator.com/item?id=47041634 | https://www.h1bexposed.tech/ | 2026-02-16T23:15:37Z | no | regex |

_Last updated: 2026-02-27T10:28:00.319962Z_
<!-- HN_TABLE_END -->

## GitHub Actions
Runs hourly and auto-commits JSON outputs + README updates.
