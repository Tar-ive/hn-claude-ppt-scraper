#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

./scrape_jobs.sh
python scrape_queries.py --queries queries.json --out hn_queries.json
python filter_results.py --in hn_queries.json --out hn_powerpoint.json --mode regex
