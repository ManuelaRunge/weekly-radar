"""Conservative public source index from the existing RIDA Radar discovery inbox.

Does not inspect full articles or verify claims. Only selected original source
metadata is exported. No notes, editorial opinions, AI drafts, or first-seen dates.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from formatting import display_text
from selection import select_items, source_rank

ROOT = Path(__file__).resolve().parents[1]

TOPIC = re.compile(
    r"\b(malaria|malvax|ntds?|neglected tropical|leishmani\w*|filari\w*|"
    r"onchocer\w*|trachoma|schistosom\w*|dengue|cholera|yellow fever|"
    r"ebola|tuberculosis|measles|rabies|vaccin\w*|immuni[sz]\w*|"
    r"vector.borne|epidemiolog\w*|epidemic\w*|outbreak|surveillance|"
    r"stratif\w*|tailor\w*|modelling|modeling|forecast\w*|"
    r"campaign effectiveness|health financing|health systems|"
    r"health policy|climate.sensitive infectious|antimicrobial resistance)\b",
    re.I,
)
GENERAL = re.compile(
    r"\b(public health|health impact|risk assessment|global health|"
    r"implementation research|disease elimination|disease control|"
    r"drug development|clinical trial|research methods|reproducib\w*)\b",
    re.I,
)
STRONG = re.compile(
    r"malaria|malvax|neglected tropical|ntds?|leishman|onchocer|filari|"
    r"vaccin|epidemiolog|modell|modeling|stratif|tailor|surveillance",
    re.I,
)
METHODS = re.compile(
    r"report|guidance|guideline|evaluation|analysis|study|trial|"
    r"surveillance|research|policy|assessment|framework|model",
    re.I,
)
JUNK = re.compile(
    r"^(highlighted signals and events|learn more|read more|view all|"
    r"skip to|home|homepage|news|latest news|events|resources|about us)$|"
    r"\b(entertainment|celebrity|music video|train accident)\b",
    re.I,
)
SKIP_STATES = {"ignored", "rejected", "archived", "private", "do_not_publish"}
MAX_ITEMS = {"this_week": 12, "previous_week": 6, "upcoming": 8}
SECTION_INFO = {
    "this_week": ("This week", "Source items published within the last seven days"),
    "previous_week": ("Also worth reading", "Source items dated 8–30 days ago"),
    "upcoming": ("Upcoming events", "Events with recorded dates in the next 180 days"),
}


def safe_url(raw: str) -> bool:
    """Restrict outputs to absolute HTTPS URLs without embedded credentials."""
    try:
        parsed = urlsplit(raw)
        parsed.port  # Validate malformed port numbers as well as the hostname.
        return (parsed.scheme == "https" and bool(parsed.hostname)
                and not (parsed.username or parsed.password)
                and not any(char.isspace() for char in raw)
                and not any(char in raw for char in "<>"))
    except (ValueError, TypeError):
        return False


def canonical_url(raw: str) -> str:
    parts = urlsplit(raw)
    tracking = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "fbclid", "gclid"}
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                       if k.lower() not in tracking])
    # Keep fragments: individual reports in a WHO WER issue often have distinct anchors.
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), query, parts.fragment))


def topic_label(title: str, category: str = "") -> str:
    text = title + " " + category
    if re.search(r"malaria|malvax|subnational tailor|stratification|\bsnt\b", text, re.I):
        return "Malaria & subnational planning"
    if re.search(r"ntds?|neglected tropical|leishman|onchocer|filari|trachoma|schistosom|rabies", text, re.I):
        return "Neglected tropical diseases"
    if re.search(r"vaccin|immuni[sz]|measles", text, re.I):
        return "Vaccines & immunisation"
    if re.search(r"modell|modeling|epidemiolog|reproducib|statistical|data analy|forecast|\btools\b", text, re.I):
        return "Modelling & methods"
    if re.search(r"policy|financing|funding|strategy|implementation", text, re.I):
        return "Policy & implementation"
    return "Infectious disease research"


def topic_score(item: dict) -> int:
    title = str(item.get("title", "")).strip()
    if not title or len(title) > 210 or JUNK.search(title):
        return 0
    financing = item.get("category") == "health-financing"
    if not (TOPIC.search(title) or GENERAL.search(title) or financing):
        return 0
    score = 6 if TOPIC.search(title) or financing else 2
    if STRONG.search(title):
        score += 3
    if METHODS.search(title):
        score += 2
    if re.search(r"snt|campaigns|methods|malaria|ntd", str(item.get("category", "")), re.I):
        score += 2
    return score


def public_sections(items: list[dict], today: dt.date) -> list[dict]:
    """Return dated, relevant URL-only selections; do not treat first_seen as published."""
    eligible = [item for item in items
                if safe_url(str(item.get("url", "")))
                and str(item.get("editorial_status", "")).lower() not in SKIP_STATES
                and str(item.get("verification", "")).lower() != "rejected"]
    groups = select_items(eligible, today)
    buckets = {
        "this_week": groups["last_7_days"],
        "previous_week": groups["last_30_days"],
        "upcoming": groups["event"],
    }
    output = []
    for key, candidates in buckets.items():
        selected = []
        seen_urls, seen_titles = set(), set()
        for item in candidates:
            raw_url = str(item.get("url", ""))
            if not safe_url(raw_url):
                continue
            if str(item.get("editorial_status", "")).lower() in SKIP_STATES:
                continue
            if str(item.get("verification", "")).lower() == "rejected":
                continue
            score = topic_score(item)
            if score < 4:
                continue
            title = display_text(item.get("title", "")).strip()
            date = str(item.get("event_date") if key == "upcoming" else item.get("published_date"))
            url_id = canonical_url(raw_url)
            title_id = (re.sub(r"\W+", " ", title.casefold()).strip(), date)
            if url_id in seen_urls or title_id in seen_titles:
                continue
            seen_urls.add(url_id)
            seen_titles.add(title_id)
            selected.append({
                "title": title,
                "url": raw_url,
                "date": date,
                "publisher": display_text(item.get("publisher") or item.get("source") or "Original source"),
                "topic": topic_label(title, str(item.get("category", ""))),
                "_score": score,
                "_source_rank": source_rank(item),
            })
        if key == "upcoming":
            selected.sort(key=lambda i: (i["date"], -i["_score"], i["_source_rank"], i["title"]))
        else:
            selected.sort(key=lambda i: (i["_source_rank"], -i["_score"], -int(i["date"].replace("-", "")), i["title"]))
        selected = [{k: v for k, v in record.items() if not k.startswith("_")}
                    for record in selected[:MAX_ITEMS[key]]]
        output.append({"id": key, "title": SECTION_INFO[key][0],
                       "description": SECTION_INFO[key][1], "items": selected})
    return output


def build_public_feed(items: list[dict], today: dt.date) -> dict:
    return {
        "schema_version": 1,
        "generated_date": today.isoformat(),
        "status": "automated_source_discovery_not_independently_verified",
        "notice": "Source-linked leads only. Verify original publication dates, claims and events before relying on them. Inclusion does not imply endorsement.",
        "sections": public_sections(items, today),
    }


def main() -> None:
    items = json.loads((ROOT / "data/items.json").read_text(encoding="utf-8"))
    today = dt.datetime.now(dt.timezone.utc).date()
    output = build_public_feed(items, today)
    path = ROOT / "output/public.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Created {path} ({sum(len(s['items']) for s in output['sections'])} public source links)")


if __name__ == "__main__":
    main()
