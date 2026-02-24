#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

rm -f jobs-page*.json

# Scrape first 2 pages of HN Jobs
for page in 1 2; do
  if [ "$page" = "1" ]; then
    URL="https://news.ycombinator.com/jobs"
  else
    URL="https://news.ycombinator.com/jobs?p=${page}"
  fi
  shot-scraper javascript "$URL" -i scrape_hn_list.js -o "jobs-page${page}.json"
  sleep 2
 done

python merge_json.py jobs-page*.json > hn_jobs.json
