#!/usr/bin/env python3
import json
import re
import os
import argparse
from datetime import datetime, timezone

# Optional LLM classification via NVIDIA API (OpenAI-compatible)
try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None

DEFAULT_KEYWORDS = [
    r"powerpoint",
    r"pptx",
    r"ppt",
    r"slides?",
    r"deck",
    r"presentation",
    r"claude",
    r"anthropic",
    r"openclaw",
    r"visa\s+sponsorship",
    r"visa\s+support",
    r"sponsor\s+visa",
    r"h1b",
    r"opt\s*extension",
    r"relocation",
    r"sponsorship",
    r"hiring",
    r"job",
    r"jobs",
]


def parse_dt(dt_str):
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def within_days(item, max_days):
    if max_days is None:
        return True
    dt = parse_dt(item.get("dt"))
    if not dt:
        return True
    age_days = (datetime.now(timezone.utc) - dt).days
    return age_days <= max_days


def load_seen(path):
    try:
        with open(path, "r") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen(path, ids):
    with open(path, "w") as f:
        json.dump(sorted(list(ids)), f, indent=2)


def regex_filter(items, patterns, max_days=None, seen_ids=None):
    regex = re.compile("|".join(patterns), re.IGNORECASE)
    out = []
    for it in items:
        if not within_days(it, max_days):
            continue
        text = " ".join([
            it.get("title") or "",
            it.get("url") or "",
        ])
        is_match = regex.search(text) is not None
        already_seen = seen_ids is not None and it.get("id") in seen_ids
        if is_match or already_seen:
            it = dict(it)
            it["match_mode"] = "regex" if is_match else "seen"
            it["pptx_present"] = bool(re.search(r"pptx", text, re.IGNORECASE))
            out.append(it)
    return out


def llm_filter(items, api_key, model, max_days=None, limit=None, seen_ids=None):
    if OpenAI is None:
        raise RuntimeError("openai package not installed")
    client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
    filtered = []
    candidates = [it for it in items if within_days(it, max_days)]
    if limit:
        candidates = candidates[:limit]
    for it in candidates:
        title = it.get("title") or ""
        url = it.get("url") or ""
        prompt = (
            "Decide if this HN item is about PowerPoint (ppt/pptx/slides/deck/presentation) "
            "or Claude/Anthropic/OpenClaw + PowerPoint. Reply only YES or NO.\n\n"
            f"Title: {title}\nURL: {url}"
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            top_p=1,
            max_tokens=5,
        )
        text = (resp.choices[0].message.content or "").strip().upper()
        if text.startswith("YES"):
            it = dict(it)
            it["match_mode"] = "llm"
            it["pptx_present"] = bool(re.search(r"pptx", (title + " " + url), re.IGNORECASE))
            filtered.append(it)
        else:
            if seen_ids is not None and it.get("id") in seen_ids:
                it = dict(it)
                it["match_mode"] = "seen"
                it["pptx_present"] = bool(re.search(r"pptx", (title + " " + url), re.IGNORECASE))
                filtered.append(it)
    return filtered


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=["regex", "llm"], default="regex")
    ap.add_argument("--model", default="z-ai/glm5")
    ap.add_argument("--keywords", default="|".join(DEFAULT_KEYWORDS))
    ap.add_argument("--max-days", type=int, default=90)
    ap.add_argument("--llm-limit", type=int, default=20)
    ap.add_argument("--seen-file", default="seen_ids.json")
    args = ap.parse_args()

    with open(args.inp, "r") as f:
        data = json.load(f)

    items = data["results"] if isinstance(data, dict) and "results" in data else data

    seen_ids = load_seen(args.seen_file) if args.seen_file else set()

    if args.mode == "llm":
        api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NVAPI_KEY")
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY (or NVAPI_KEY) not set")
        filtered = llm_filter(items, api_key, args.model, max_days=args.max_days, limit=args.llm_limit, seen_ids=seen_ids)
    else:
        filtered = regex_filter(items, args.keywords.split("|"), max_days=args.max_days, seen_ids=seen_ids)

    if args.seen_file:
        for it in filtered:
            if it.get("id"):
                seen_ids.add(it.get("id"))
        save_seen(args.seen_file, seen_ids)

    out = {
        "generated_at": data.get("generated_at") if isinstance(data, dict) else None,
        "count": len(filtered),
        "results": filtered,
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
