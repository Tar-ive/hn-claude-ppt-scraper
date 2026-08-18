#!/usr/bin/env python3
"""
warehouse_check.py — check one item's price/availability across ALL warehouses
via the Warehouse Runner backend (api-runner.a-ok.app).

The Runner backend is a private, undocumented mobile API. Rather than hardcode
guessed routes, this tool is *capture-driven*: you capture ONE real request that
the app makes (endpoint, headers/auth, body), save it as a config, and this tool
replays that request across every warehouse concurrently and prints a table.

Workflow
--------
1) Capture one request from the app (see README "Capturing a request").
2) Turn the captured `curl` into a config:
       python warehouse_check.py import-curl captured.txt -o runner_config.json
   (or copy runner_config.example.json and edit it by hand)
3) Fill in the `warehouses` list (id + name) in the config.
4) Run:
       python warehouse_check.py check "organic milk" -c runner_config.json

Placeholders you put in the endpoint/body/headers get substituted per request:
    {warehouse_id}  -> current warehouse id
    {item}          -> the item argument from the CLI (URL-safe in the path)
"""
import argparse
import concurrent.futures as cf
import json
import re
import shlex
import sys
import urllib.parse
from datetime import datetime, timezone

import requests

DEFAULT_CONFIG = "runner_config.json"
DEFAULT_TIMEOUT = 20
DEFAULT_WORKERS = 8


# --------------------------------------------------------------------------- #
# Config helpers
# --------------------------------------------------------------------------- #
def load_config(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit(
            f"Config '{path}' not found.\n"
            f"Create one with:  python {sys.argv[0]} import-curl <captured.txt> -o {path}\n"
            f"or copy runner_config.example.json and edit it."
        )
    except json.JSONDecodeError as e:
        sys.exit(f"Config '{path}' is not valid JSON: {e}")


def _get_path(obj, dotted):
    """Extract a value from nested dict/list via a dotted path like 'data.0.price'."""
    if not dotted:
        return None
    cur = obj
    for part in dotted.split("."):
        if cur is None:
            return None
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _substitute(value, mapping):
    """Recursively substitute {placeholders} in strings within nested structures."""
    if isinstance(value, str):
        out = value
        for k, v in mapping.items():
            out = out.replace("{" + k + "}", str(v))
        return out
    if isinstance(value, dict):
        return {k: _substitute(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, mapping) for v in value]
    return value


# --------------------------------------------------------------------------- #
# check command
# --------------------------------------------------------------------------- #
def query_one(session, cfg, warehouse, item):
    wid = warehouse.get("id")
    mapping = {
        "warehouse_id": wid,
        "item": urllib.parse.quote(str(item)),
        "item_raw": item,
    }
    method = cfg.get("method", "GET").upper()
    url = cfg["base_url"].rstrip("/") + "/" + _substitute(cfg["endpoint"], mapping).lstrip("/")
    headers = _substitute(cfg.get("headers", {}), mapping)
    params = _substitute(cfg.get("query", {}), mapping)
    body = cfg.get("body")

    kwargs = {"headers": headers, "params": params, "timeout": cfg.get("timeout", DEFAULT_TIMEOUT)}
    if body is not None and method in ("POST", "PUT", "PATCH"):
        body = _substitute(body, mapping)
        if isinstance(body, (dict, list)):
            kwargs["json"] = body
        else:
            kwargs["data"] = body

    result = {"warehouse_id": wid, "warehouse": warehouse.get("name", str(wid))}
    try:
        r = session.request(method, url, **kwargs)
        result["http_status"] = r.status_code
        try:
            data = r.json()
        except ValueError:
            result["error"] = f"non-JSON response ({r.status_code}): {r.text[:120]}"
            return result
        ex = cfg.get("extract", {})
        result["price"] = _get_path(data, ex.get("price", ""))
        result["available"] = _get_path(data, ex.get("available", ""))
        result["name"] = _get_path(data, ex.get("name", ""))
        if not any(k in result for k in ("price", "available", "name")) or (
            result.get("price") is None and result.get("available") is None
        ):
            # keep the raw payload so the user can figure out the right extract paths
            result["raw"] = data
    except requests.RequestException as e:
        result["error"] = str(e)
    return result


def cmd_check(args):
    cfg = load_config(args.config)
    for key in ("base_url", "endpoint"):
        if key not in cfg:
            sys.exit(f"Config is missing required key '{key}'. See runner_config.example.json.")
    warehouses = cfg.get("warehouses", [])
    if not warehouses:
        sys.exit("Config has no 'warehouses'. Add a list of {\"id\": ..., \"name\": ...} entries.")

    session = requests.Session()
    results = []
    workers = min(args.workers, len(warehouses)) or 1
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(query_one, session, cfg, w, args.item): w for w in warehouses}
        for fut in cf.as_completed(futures):
            results.append(fut.result())

    # order results to match config order
    order = {w.get("id"): i for i, w in enumerate(warehouses)}
    results.sort(key=lambda r: order.get(r["warehouse_id"], 1e9))

    print_table(args.item, results)

    if args.out:
        payload = {
            "item": args.item,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "results": results,
        }
        with open(args.out, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"\nSaved JSON -> {args.out}")


def print_table(item, results):
    print(f"\nItem: {item}   ({len(results)} warehouses)\n")
    name_w = max([len(str(r["warehouse"])) for r in results] + [9])
    header = f"{'Warehouse':<{name_w}}  {'Price':>10}  {'Avail':>6}  Notes"
    print(header)
    print("-" * len(header))
    for r in results:
        if "error" in r:
            note = f"ERROR: {r['error'][:60]}"
            price, avail = "-", "-"
        elif "raw" in r:
            note = f"HTTP {r.get('http_status','?')} - couldn't extract; check 'extract' paths"
            price, avail = "-", "-"
        else:
            price = f"{r.get('price')}" if r.get("price") is not None else "-"
            avail = fmt_avail(r.get("available"))
            note = r.get("name") or ""
        print(f"{str(r['warehouse']):<{name_w}}  {price:>10}  {avail:>6}  {note}")


def fmt_avail(v):
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "yes" if v else "no"
    return str(v)


# --------------------------------------------------------------------------- #
# import-curl command
# --------------------------------------------------------------------------- #
def cmd_import_curl(args):
    with open(args.file) as f:
        raw = f.read()
    cfg = parse_curl(raw)
    cfg.setdefault("warehouses", [{"id": "REPLACE_ME", "name": "Example Warehouse"}])
    cfg.setdefault(
        "extract",
        {"price": "REPLACE.dotted.path", "available": "REPLACE.dotted.path", "name": "REPLACE.dotted.path"},
    )
    with open(args.out, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"Wrote {args.out}")
    print(
        "\nNext steps:\n"
        "  1. In the endpoint/body, replace the real warehouse id with {warehouse_id}\n"
        "     and the searched item with {item}.\n"
        "  2. Fill in the 'warehouses' list with every warehouse id + name.\n"
        "  3. Set the 'extract' dotted paths to point at price/available/name in the\n"
        "     JSON response (run a 'check' once; unextracted rows print the raw payload).\n"
    )


def parse_curl(raw):
    # normalise line-continuations, then tokenise like a shell
    raw = raw.replace("\\\n", " ").strip()
    if raw.startswith("curl "):
        raw = raw[len("curl "):]
    tokens = shlex.split(raw)

    cfg = {"method": "GET", "base_url": "", "endpoint": "", "headers": {}, "query": {}}
    url = None
    method = None
    body = None
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in ("-X", "--request"):
            method = tokens[i + 1]; i += 2; continue
        if t in ("-H", "--header"):
            hv = tokens[i + 1]; i += 2
            if ":" in hv:
                k, v = hv.split(":", 1)
                cfg["headers"][k.strip()] = v.strip()
            continue
        if t in ("-d", "--data", "--data-raw", "--data-binary", "--data-ascii"):
            body = tokens[i + 1]; i += 2; continue
        if t in ("-b", "--cookie"):
            cfg["headers"]["Cookie"] = tokens[i + 1]; i += 2; continue
        if t in ("--compressed", "-s", "-S", "-L", "-k", "-i", "-v", "--location"):
            i += 1; continue
        if t.startswith("-"):
            # unknown flag that likely takes a value; skip conservatively
            i += 2 if (i + 1 < len(tokens) and not tokens[i + 1].startswith("-")) else 1
            continue
        if url is None and (t.startswith("http://") or t.startswith("https://")):
            url = t
        i += 1

    if not url:
        sys.exit("Could not find a URL in the curl command.")
    parsed = urllib.parse.urlparse(url)
    cfg["base_url"] = f"{parsed.scheme}://{parsed.netloc}"
    cfg["endpoint"] = parsed.path or "/"
    if parsed.query:
        cfg["query"] = dict(urllib.parse.parse_qsl(parsed.query))

    if body is not None:
        try:
            cfg["body"] = json.loads(body)
        except ValueError:
            cfg["body"] = body
        if method is None:
            method = "POST"
    cfg["method"] = (method or "GET").upper()
    return cfg


# --------------------------------------------------------------------------- #
def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="check an item across all warehouses")
    c.add_argument("item", help="item to search for (name, UPC, or item id)")
    c.add_argument("-c", "--config", default=DEFAULT_CONFIG, help=f"config file (default: {DEFAULT_CONFIG})")
    c.add_argument("-w", "--workers", type=int, default=DEFAULT_WORKERS, help="concurrent requests")
    c.add_argument("-o", "--out", help="also write full results to this JSON file")
    c.set_defaults(func=cmd_check)

    ic = sub.add_parser("import-curl", help="build a config from a captured curl command")
    ic.add_argument("file", help="text file containing the captured `curl ...` command")
    ic.add_argument("-o", "--out", default=DEFAULT_CONFIG, help=f"output config (default: {DEFAULT_CONFIG})")
    ic.set_defaults(func=cmd_import_curl)
    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
