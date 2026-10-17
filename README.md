# RIDA Radar

[![Radar workflow](https://github.com/runge-infectious-disease-analytics/rida-radar/actions/workflows/radar.yml/badge.svg)](https://github.com/runge-infectious-disease-analytics/rida-radar/actions/workflows/radar.yml)
![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Status: starter](https://img.shields.io/badge/Status-starter-orange)
![Public health](https://img.shields.io/badge/Focus-public%20health-teal)
![Manual review](https://img.shields.io/badge/Publishing-manual%20review-blue)

RIDA Radar gathers public health links into a private, source-linked reading inbox. It helps track events, policy updates, research resources and modelling tools, then select useful items for optional RIDA editorial curation.

The current sources cover malaria and vaccines, cholera, neglected tropical diseases, WHO updates, and epidemiology software. The output is a Markdown briefing for human review. Nothing is automatically published.

## How it works

1. **Collect** links from configured webpages and release feeds, plus manually supplied URLs.
2. **Keep an inbox** with stable URL identifiers, first-seen dates and any manually supplied publication or event dates.
3. **Build a briefing** with upcoming events within 180 days, dated updates from the previous 14 days, and undated discoveries.
4. **Review and curate** the original sources before saving, sharing or selecting items for RIDA.

This is an early starter: collected links are discovery leads and may include irrelevant navigation links. Dates, claims and event status require verification against the original source.

## Get started

From the repository root, using Python 3.12:

```sh
python -m pip install -r requirements.txt
python src/collect.py
python src/brief.py
```

Open `output/latest.md` to review the briefing and check `data/errors.json` for failed sources, even if collection exits successfully.

| File | Purpose |
| --- | --- |
| `config/sources.json` | Configure webpages and feeds to monitor. |
| `config/manual_links.csv` | Add explicit URLs, dates and notes, including public LinkedIn permalinks. |
| `data/items.json` | Persistent collection of discovered candidates. |
| `data/errors.json` | Source failures from the latest collection run. |
| `output/latest.md` | Generated reading inbox and manual publishing shortlist. |

## Weekly automation

The **RIDA Radar (private review)** GitHub Actions workflow runs each Monday at 06:15 UTC and can also be started manually. Enable Actions and allow repository contents write access for its commit-back step, which saves generated data and the briefing to this repository. Keep the repository private if the inbox should remain private.

## What it does and does NOT do

- Collects links from public webpages and GitHub Atom release feeds. Websites may block automated collection, change layout, or publish many irrelevant navigation links. Results are **discovery leads**, not vetted updates.
- Records `first_seen`, preserves items across runs and avoids simple URL duplicates. `first_seen` is **not** a publication date.
- Accepts manually supplied publication dates and event dates; these must be checked against the source.
- Generates a Markdown inbox highlighting upcoming dated events, dated updates and undated discoveries.
- Does **not** extract full article texts, reliably parse dynamic sites, crawl LinkedIn, verify social-post dates, autonomously compose AI summaries, post to LinkedIn, or automatically publish anything.
- LinkedIn links can be recorded manually if public permalinks are available. Do not use password/session scraping or violate platform access terms.
- Github Actions schedules can be delayed or skipped; do not use this workflow for deadline-critical alerts.

## Recommended development roadmap

1. Build source-specific RSS/API collectors for WHO news, event calendars and journals; improve event-date extraction and content relevance filtering.
2. Add a verified item schema (source date, event deadline, source permalink, LinkedIn permalink, checked timestamp) and tests.
3. Add a private weekly reading interface (CSV or Streamlit): save, attend, read, share, ignore.
4. Add opt-in AI curation fed with source text, not just titles. Require evidence links and flag uncertainty.
5. Generate separate personal briefing vs RIDA editorial candidates; allow approval and export to website Markdown, never autopost.

## Suggested categories

- Events and deadlines; Policy and guidance; Worth reading; Tools and methods; From the network (LinkedIn); For further exploration.

## Privacy, ownership and copyright

Keep this repository private initially. Reuse generic code, not employer proprietary assets or project information. Link back to original sources. Avoid redistributing full articles and copyrighted images. If using an external AI API, review the privacy and copyright implications of the material you send.

## AI assistance

![AI assisted](https://img.shields.io/badge/Development-AI%20assisted-blue)

Parts of this project were generated with OpenAI Codex. Use `AI-generated:`, `Human-authored:` or `Mixed:` in commit messages to describe contribution provenance. AI assistance does not imply validation; review and test changes. Collected information is for research and discovery, not medical advice.
