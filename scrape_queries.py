#!/usr/bin/env python3
import json
import argparse
import requests
from datetime import datetime

ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


def fetch_query(name, query, tags, hits_per_page=100):
    params = {
        "query": query,
        "tags": tags,
        "hitsPerPage": hits_per_page,
        "page": 0,
    }
    r = requests.get(ALGOLIA_SEARCH_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    results = []
    for hit in data.get("hits", []):
        results.append({
            "id": hit.get("objectID"),
            "title": hit.get("title") or hit.get("story_title"),
            "url": hit.get("url") or hit.get("story_url"),
            "points": hit.get("points"),
            "submitter": hit.get("author"),
            "dt": hit.get("created_at"),
            "commentsUrl": f"https://news.ycombinator.com/item?id={hit.get('objectID')}" if hit.get("objectID") else None,
            "numComments": hit.get("num_comments"),
            "queryName": name,
            "query": query,
        })
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", default="queries.json", help="Path to queries.json")
    ap.add_argument("--out", default="hn_queries.json", help="Output JSON file")
    ap.add_argument("--hits", type=int, default=100)
    args = ap.parse_args()

    with open(args.queries, "r") as f:
        queries = json.load(f)

    all_results = []
    for name, cfg in queries.items():
        results = fetch_query(name, cfg["query"], cfg.get("tags", "story"), args.hits)
        all_results.extend(results)

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "count": len(all_results),
        "results": all_results,
    }
    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2)


if __name__ == "__main__":
    main()
