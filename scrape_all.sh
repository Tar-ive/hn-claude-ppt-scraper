#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

./scrape_jobs.sh
python scrape_queries.py --queries queries.json --out hn_queries.json
# Try NVIDIA LLM filter first, fall back to regex if it fails
python filter_results.py --in hn_queries.json --out hn_powerpoint.json --mode llm --model z-ai/glm5 --llm-limit 20 --max-days 7 || \
  python filter_results.py --in hn_queries.json --out hn_powerpoint.json --mode regex --max-days 7
python update_readme.py --input hn_powerpoint.json --readme README.md --limit 25
# Cleanup raw pages/queries
rm -f jobs-page*.json hn_queries.json
