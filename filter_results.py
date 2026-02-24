#!/usr/bin/env python3
import json
import re
import os
import argparse

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
]


def regex_filter(items, patterns):
    regex = re.compile("|".join(patterns), re.IGNORECASE)
    out = []
    for it in items:
        text = " ".join([
            it.get("title") or "",
            it.get("url") or "",
        ])
        if regex.search(text):
            it = dict(it)
            it["match_mode"] = "regex"
            it["pptx_present"] = bool(re.search(r"pptx", text, re.IGNORECASE))
            out.append(it)
    return out


def llm_filter(items, api_key, model):
    if OpenAI is None:
        raise RuntimeError("openai package not installed")
    client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
    filtered = []
    for it in items:
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
    return filtered


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=["regex", "llm"], default="regex")
    ap.add_argument("--model", default="z-ai/glm5")
    ap.add_argument("--keywords", default="|".join(DEFAULT_KEYWORDS))
    args = ap.parse_args()

    with open(args.inp, "r") as f:
        data = json.load(f)

    items = data["results"] if isinstance(data, dict) and "results" in data else data

    if args.mode == "llm":
        api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NVAPI_KEY")
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY (or NVAPI_KEY) not set")
        filtered = llm_filter(items, api_key, args.model)
    else:
        filtered = regex_filter(items, args.keywords.split("|"))

    out = {
        "generated_at": data.get("generated_at") if isinstance(data, dict) else None,
        "count": len(filtered),
        "results": filtered,
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
