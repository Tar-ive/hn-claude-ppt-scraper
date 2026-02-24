#!/usr/bin/env python3
import json
import sys
from datetime import datetime

def main():
    files = sys.argv[1:]
    all_items = []
    for f in files:
        with open(f, "r") as fh:
            data = json.load(fh)
            if isinstance(data, dict) and "results" in data:
                data = data["results"]
            if isinstance(data, list):
                all_items.extend(data)
    # de-dup by id
    seen = set()
    deduped = []
    for item in all_items:
        _id = item.get("id")
        if _id and _id in seen:
            continue
        if _id:
            seen.add(_id)
        deduped.append(item)
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "count": len(deduped),
        "results": deduped,
    }
    json.dump(payload, sys.stdout, indent=2)

if __name__ == "__main__":
    main()
