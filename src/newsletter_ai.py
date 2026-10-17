"""Prepare a private ChatGPT briefing packet or explicitly run paid OpenAI API curation.

Default mode NEVER calls an API. Only --mode api sends material to OpenAI.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
from urllib import request, error
from selection import select_items
from formatting import display_text

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "data" / "items.json"
OUT = ROOT / "output"
INSTRUCTIONS = (ROOT / "config" / "editorial_instructions.md")

def shortlist(items, max_items=90):
    groups = select_items(items)
    selected = []
    # Reserve room for the calendar even during busy news weeks.
    per_section, remainder = divmod(max(0, max_items), 3)
    for index, kind in enumerate(('last_7_days', 'last_30_days', 'event')):
        for item in groups[kind][:per_section + (index < remainder)]:
            candidate = {key: item.get(key, '') for key in
                         ('title', 'url', 'source', 'category', 'published_date', 'event_date',
                          'first_seen', 'notes', 'verification', 'method', 'editorial_status')}
            candidate['recency_group'] = kind
            for field in ('title', 'source', 'notes'):
                candidate[field] = display_text(candidate[field])
            selected.append(candidate)
    return selected

def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    items = json.loads(INBOX.read_text(encoding="utf-8")) if INBOX.exists() else []
    packet = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "UNVERIFIED_DISCOVERY_LEADS",
        "instructions": "News is limited to the last 30 days; lead with the last 7 days and prioritize WHO global disease news over MalVax within each period. Sort upcoming events by event date. Include malaria subnational tailoring (SNT) and Campaign Effectiveness. Exclude malariasimulation and OpenMalaria tracking. Use en dashes, never em dashes; put the publisher in parentheses after each entry's original link. Use only verifiable details; do not invent dates or content. Read source pages when accessible.",
        "items": shortlist(items),
    }
    (OUT / "chatgpt_input.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown = (
        "# RIDA Radar – ChatGPT curation instructions\n\n"
        "1. Open `output/chatgpt_input.json` and `config/editorial_instructions.md`.\n"
        "2. Paste or attach the JSON to ChatGPT, along with the editorial instructions, "
        "or ask ChatGPT with repository access to read both files.\n"
        "3. Ask for the private weekly newsletter; verify dates and original links before sharing.\n\n"
        "**Note:** Entries are discovery leads, not verified news. The packet does not contain full article text.\n"
    )
    (OUT / "HOW_TO_CHATGPT.md").write_text(markdown, encoding="utf-8")
    print(f"Prepared {len(packet['items'])} candidates; no AI API called.")
    return packet

def run_api(packet, model):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("OPENAI_API_KEY is required for --mode api. No request was made.")
    instructions = INSTRUCTIONS.read_text(encoding="utf-8")
    # Use a smaller bounded packet to control API costs; still requires human verification.
    payload = {
        "model": model,
        "instructions": instructions,
        "input": "Create this week's PRIVATE RIDA Radar newsletter from the following discovery records. "
                 "Do not imply external URLs were checked when they were not.\n" +
                 json.dumps(packet, ensure_ascii=False),
        "max_output_tokens": 4000,
    }
    req = request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise SystemExit(f"API request failed (HTTP {exc.code}); check model access and billing.") from exc
    text = "\n".join(x.get("text", "") for o in result.get("output", [])
                     for x in o.get("content", []) if x.get("type") == "output_text")
    if not text:
        raise SystemExit("API response contained no newsletter text. Review the API response before retrying.")
    (OUT / "ai_draft.md").write_text(text + "\n", encoding="utf-8")
    print("Created output/ai_draft.md – draft only, not verified or published.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("prepare", "api"), default="prepare",
                        help="prepare is free/offline; api explicitly invokes paid API")
    parser.add_argument("--model", default="gpt-5-mini", help="API model; change if unavailable")
    args = parser.parse_args()
    packet = prepare()
    if args.mode == "api":
        run_api(packet, args.model)

if __name__ == "__main__":
    main()
