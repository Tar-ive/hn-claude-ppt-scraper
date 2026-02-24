#!/usr/bin/env python3
import json
import argparse
from datetime import datetime

TABLE_START = "<!-- HN_TABLE_START -->"
TABLE_END = "<!-- HN_TABLE_END -->"


def load_items(path):
    with open(path, "r") as f:
        data = json.load(f)
    return data.get("results", data)


def make_table(items, limit=20):
    rows = []
    for it in items[:limit]:
        hn = it.get("commentsUrl") or ""
        ext = it.get("url") or ""
        dt = it.get("dt") or ""
        pptx = "yes" if it.get("pptx_present") else "no"
        mode = it.get("match_mode") or "regex"
        rows.append(f"| [HN]({hn}) | {(f'[link]({ext})' if ext else '')} | {dt} | {pptx} | {mode} |")

    header = "| HN link | App/External link | Posted | PPTX present | Match mode |\n|---|---|---|---|---|"
    body = "\n".join(rows) if rows else "| (none) | | | | |"
    return header + "\n" + body


def update_readme(readme_path, table):
    with open(readme_path, "r") as f:
        content = f.read()

    if TABLE_START not in content or TABLE_END not in content:
        raise RuntimeError("README missing table markers")

    before = content.split(TABLE_START)[0]
    after = content.split(TABLE_END)[1]

    updated = (
        before
        + TABLE_START
        + "\n"
        + table
        + "\n"
        + f"\n_Last updated: {datetime.utcnow().isoformat()}Z_\n"
        + TABLE_END
        + after
    )

    with open(readme_path, "w") as f:
        f.write(updated)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--readme", default="README.md")
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    items = load_items(args.input)
    table = make_table(items, limit=args.limit)
    update_readme(args.readme, table)


if __name__ == "__main__":
    main()
