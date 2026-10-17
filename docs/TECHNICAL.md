# RIDA Radar – technical guide

[Read the latest briefing](../README.md#latest-briefing) · [Newsletter preparation](AI_NEWSLETTER.md)

## How it works

1. **Collect** links from configured webpages, news feeds and WHO's outbreak listing, plus manually supplied URLs.
2. **Keep an inbox** with stable URL identifiers, first-seen dates and any manually supplied publication or event dates.
3. **Build a briefing** with news from the previous 30 days, giving the last 7 days prominence and WHO global disease news priority over MalVax within each period. Upcoming events within 180 days appear in chronological order.
4. **Review and curate** the original sources before saving, sharing or selecting items for RIDA.

This is an early starter: collected links are discovery leads and may include irrelevant navigation links. Dates, claims and event status require verification against the original source.

## WHO source coverage

WHO discovery combines the RSS feed with the paginated headline listing and the Weekly Epidemiological Record (WER), since the feed can omit announcements. Headlines are followed until the 30-day cutoff or five pages. WER checks up to six linked HTML issues and uses each issue's explicit publication date; individual reports link directly to their article headings in the original issue. Duplicate WHO titles with the same publication date prefer the WER article. This avoids guessing report URLs from page ranges.

## Modelling and research networks

The weekly sources also include AMMnet (home, events and newsletters), Measles Analytics Hub (home, news and calendar), VIMC (dated news feed), TB-MAC (home, meetings and newsletters), DNDi (dated news cards), and CEMA at the University of Nairobi (home and news). AMMnet's event cards supply explicit event dates and titles. Empty TB-MAC and DNDi RSS feeds are avoided in favour of their public pages. Undated pages remain discovery leads in the archive; incomplete dates such as a day and month without a year are not promoted to recent news or upcoming events.

Reader-facing output uses en dashes and places each source/publisher in parentheses after the link: `[Title](https://example.org/) (Publisher)`.

## Get started

From the repository root, using Python 3.12:

```sh
python -m pip install -r requirements.txt
python src/collect.py
python src/brief.py
python src/newsletter_ai.py --mode prepare
python src/publish.py
```

Open `output/latest.md` to review the briefing and check `data/errors.json` for failed sources, even if collection exits successfully.

The same rules apply to the newsletter packet (`python src/newsletter_ai.py --mode prepare`). Publication dates come from source feeds, explicit page metadata or manual entries. Undated links stay in the archive and are excluded from recent news; `first_seen` never substitutes for publication date. Historical data remains available, but malariasimulation and OpenMalaria records are excluded from briefings and newsletter packets.

| File | Purpose |
| --- | --- |
| `config/sources.json` | Configure webpages and feeds to monitor. |
| `config/manual_links.csv` | Add explicit URLs, dates and notes, including public LinkedIn permalinks. |
| `data/items.json` | Persistent collection of discovered candidates. |
| `data/errors.json` | Source failures from the latest collection run. |
| `output/latest.md` | Generated reading inbox and manual publishing shortlist. |

## Weekly automation

The **RIDA Radar** GitHub Actions workflow runs each Monday at 06:15 UTC and can also be started manually on the default branch. It tests the code, collects sources, builds the briefing and newsletter packet, embeds the full briefing in the README, and prepares run notes. It then commits the generated files and publishes a GitHub Release. Enable Actions and allow repository contents write access for the commit and release steps. Keep the repository private if the inbox should remain private.

### Releases and tags

Every successful scheduled or manual workflow attempt publishes a release with a unique tag such as `radar-20261017T120000Z-123456789-1`: UTC timestamp, GitHub run ID and attempt number. Reruns get a distinct attempt number, including when the source content is unchanged. The tag targets the commit containing that run's README, data and outputs. A failed generation, test or push does not proceed to publication.

The release body contains the run summary, source errors and the full `output/latest.md` briefing. `latest.md` and `release_notes.md` are also attached as downloadable Markdown assets. The release is marked Latest. The workflow uses its built-in `GITHUB_TOKEN` with `contents: write`; no additional release token is needed. Branch or tag protection rules must permit these workflow writes. Releases inherit the repository's visibility.

Local `python src/publish.py` refreshes the README and prepares `output/release_notes.md` without committing, tagging or contacting GitHub. The workflow handles remote publication. `RADAR_TAG` is optional locally; Actions supplies it automatically. Failed source requests are recorded as incomplete coverage in the notes while the run continues.

The README's `LATEST-BRIEFING` comment markers delimit the generated content; keep both markers and put manual edits outside them.

## What it does and does NOT do

- Collects links from public webpages, RSS feeds and WHO's public outbreak listing. Websites may block automated collection, change layout, or publish irrelevant navigation links. Results are **discovery leads**, not vetted updates.
- Records `first_seen`, preserves items across runs and avoids simple URL duplicates. `first_seen` is **not** a publication date.
- Reads publication dates from feeds and explicit page metadata, and accepts manually supplied publication and event dates; these must be checked against the source.
- Generates a Markdown inbox of dated updates and upcoming events. Undated discoveries remain in the archive.
- Does **not** extract full article texts, reliably parse dynamic sites, crawl LinkedIn, verify social-post dates, autonomously compose AI summaries, or post to LinkedIn. GitHub briefing releases are automatic; editorial sharing remains a human decision.
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

