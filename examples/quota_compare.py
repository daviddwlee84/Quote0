#!/usr/bin/env python3
"""Fetch once and export PNG + Canvas JSON with the same reference time; never send."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from quote0.apps.quota import fetch_quotas, render_quota
from quote0.apps.quota_canvas import render_quota_canvas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--providers", nargs="+", required=True)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--output-dir", type=Path, default=Path("quota-comparison"))
    parser.add_argument(
        "--canvas-style", choices=("compact", "cards"), default="compact"
    )
    parser.add_argument(
        "--card-theme", choices=("light", "dark", "alternating"), default="alternating"
    )
    args = parser.parse_args()
    if args.card_theme != "alternating" and args.canvas_style != "cards":
        parser.error("--card-theme requires --canvas-style cards")
    quotas = fetch_quotas(args.providers, timeout=args.timeout)
    now = datetime.now().astimezone()
    picture = render_quota(quotas, now=now)
    canvas = render_quota_canvas(
        quotas, now=now, style=args.canvas_style, card_theme=args.card_theme
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    picture.save(args.output_dir / "quota.png", format="PNG")
    (args.output_dir / "quota.json").write_text(
        json.dumps(canvas, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"Exported PNG and Canvas JSON to {args.output_dir}; no device contacted.")
    for quota in quotas:
        if quota.error:
            print(f"{quota.provider}: {quota.error}")
    return int(any(quota.error for quota in quotas))


if __name__ == "__main__":
    raise SystemExit(main())
