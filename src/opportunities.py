"""Create a two-lane *editorial planning* packet; no external AI or posting.

Outputs are committed to a public GitHub repository. Keep them general and
non-confidential; never produce private workplace details or claim to have
read the source pages. Potential angles are questions, not reported findings.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ANGLES = {
    "Malaria & subnational planning": (
        "How does this connect to decisions about malaria risk, intervention combinations or programme implementation?",
        "Relevant to malaria epidemiology, intervention modelling and subnational planning.",
        "RIDA", "Technical commentary", "medium",
    ),
    "Neglected tropical diseases": (
        "Which data, surveillance or programme decisions are relevant, and what remains uncertain?",
        "Connects disease control evidence with implementation and policy.",
        "RIDA", "Short source-linked commentary", "medium",
    ),
    "Vaccines & immunisation": (
        "What evidence is needed to translate vaccine research or policy into delivery decisions?",
        "Research interests in vaccines, malaria and intervention modelling.",
        "Personal profile", "Brief evidence-focused commentary", "quick",
    ),
    "Modelling & methods": (
        "What assumptions, input data, limitations or reproducibility considerations should readers examine?",
        "Relevant to computational epidemiology, modelling and reproducible analysis.",
        "RIDA", "Methods note", "medium",
    ),
    "Policy & implementation": (
        "Which steps separate the published evidence from decisions in national programmes?",
        "Interest in evidence-to-policy and global health planning.",
        "Personal profile", "Short professional commentary", "quick",
    ),
    "Infectious disease research": (
        "What should be checked in the original source before drawing programmatic conclusions?",
        "Relevant to infectious disease epidemiology and evidence synthesis.",
        "Personal profile", "Source-linked research commentary", "quick",
    ),
}


def evergreen_selection(backlog: list[dict], today: dt.date, limit: int = 5) -> list[dict]:
    """Resurface the highest-priority ideas, rotating within each priority tier."""
    candidates = [i for i in backlog if str(i.get("status", "backlog")).lower() not in
                  {"published", "archived", "rejected", "private", "do_not_publish", "ignored"}]
    # Stable weekly rotation among equally ranked candidates; preserve top tiers.
    week = today.isocalendar().week
    grouped = {}
    for item in candidates:
        grouped.setdefault(int(item.get("priority", 1)), []).append(item)
    chosen = []
    for priority in sorted(grouped, reverse=True):
        pool = sorted(grouped[priority], key=lambda i: i["id"])
        if pool:
            offset = week % len(pool)
            ordered = pool[offset:] + pool[:offset]
            chosen.extend(ordered)
    return [{k: v for k, v in item.items() if k != "priority"} for item in chosen[:limit]]


def build_scan(public_feed: dict, backlog: list[dict], today: dt.date) -> dict:
    timely = []
    for section in public_feed["sections"]:
        if section["id"] != "this_week":
            continue
        for item in section["items"][:7]:
            core, why, channel, format_, effort = ANGLES.get(item["topic"], ANGLES["Infectious disease research"])
            timely.append({
                "title_or_hook": item["title"],
                "lane": "timely",
                "source_date": item["date"],
                "source_url": item["url"],
                "publisher": item["publisher"],
                "why_it_fits": why,
                "core_angle_for_review": core,
                "recommended_format": format_,
                "estimated_effort": effort,
                "best_channel": channel,
                "source_material": "Original linked publication (must be read and checked before posting)",
                "status": "unreviewed_discovery_lead",
            })
    evergreen = []
    for item in evergreen_selection(backlog, today):
        evergreen.append({
            "id": item["id"], "title_or_hook": item["title"], "lane": "evergreen",
            "why_it_fits": item["why_it_fits"],
            "core_angle_for_review": item["core_angle"],
            "recommended_format": item["format"],
            "estimated_effort": item["effort"],
            "best_channel": item["best_channel"],
            "source_material": item["source_material"],
            "status": item.get("status", "backlog"),
        })
    return {
        "generated_date": today.isoformat(),
        "notice": "Planning leads only. Automated titles and suggested questions are not summaries of original findings. Read and verify sources; human review is required before any publication.",
        "lanes": {"timely": timely, "evergreen": evergreen},
    }


def main() -> None:
    public_feed = json.loads((ROOT / "output/public.json").read_text(encoding="utf-8"))
    backlog = json.loads((ROOT / "config/evergreen_backlog.json").read_text(encoding="utf-8"))
    today = dt.date.fromisoformat(public_feed["generated_date"])
    output = build_scan(public_feed, backlog, today)
    target = ROOT / "output/opportunity_scan.json"
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Created two-lane opportunity scan (editorial planning, not a publication)")


if __name__ == "__main__":
    main()
