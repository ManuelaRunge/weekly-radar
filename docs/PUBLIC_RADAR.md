# RIDA Radar – public index and editorial review

## Three different outputs

**Full inbox (`output/latest.md`)** is a dated list of discovery leads from the last 30 days plus upcoming events. It is not automatically quality-assured. It remains available in a collapsed README section and in releases.

**Public source index (`output/public.json` and README)** keeps a smaller topic-relevant set of original links, publication or event dates, source attribution and broad topics. News uses the same last-seven-days and 8–30-day periods as the full inbox, with WHO priority; upcoming events remain chronological. No private notes, AI summaries or first-person observations are exported. A listing is not an endorsement and should not be presented as a validated finding.

**Editorial opportunities (`output/opportunity_scan.json`)** provide two lanes: timely source-linked candidate hooks and evergreen original content ideas. Suggested angles are questions for later source review and should not be copied unchanged into published commentary. Its backlog (`config/evergreen_backlog.json`) is public and should contain only general, non-confidential ideas.

## Generate the outputs

After the collector, full briefing and newsletter packet, the weekly workflow runs `src/public_feed.py`, `src/opportunities.py`, and `src/publish.py`. These steps need no AI API key and do not post to social platforms. Source lists, collection history and editorial states remain in their existing files.

See the [local setup commands](TECHNICAL.md#get-started). Run `python src/public_feed.py` and `python src/opportunities.py` against an existing inbox to preview the two JSON outputs without network access. `python src/publish.py` updates the README and run notes. Only the GitHub workflow's release step publishes a release and tag.

## Website integration

Preferred source for the Astro `/radar/` page:

`https://raw.githubusercontent.com/ManuelaRunge/weekly-radar/main/output/public.json`

The file has `schema_version`, `generated_date`, `notice` and `sections[]`, each with an `id`, `title`, `description` and `items[]`. Each item contains `title`, `url`, `date`, `publisher` and `topic`. Website code should display only these fields, not the unfiltered `data/items.json` archive.

Website code can consume this dedicated feed instead of duplicating filters over the full archive. Display its notice and generation date, and link the release archive. `previous_week` is the stable section ID for the older-news group; its documented window is 8–30 days. The index is limited to 12 recent items, 6 older items and 8 upcoming events. All records contain only `title`, `url`, `date`, `publisher` and `topic`.

No website repository, pull request or deployment is changed by this integration. A website needs its own code change and rebuild to consume the feed.

## Human editorial gate

Do not automatically publish summaries of scientific findings, medical or policy conclusions, promotional copy or personal reflections. Verify the linked documents, then write a distinctly sourced and attributed post or article for personal LinkedIn or RIDA. When the source cannot be read, the item remains a discovery lead.

## Backlog maintenance

Edit the `status` values in `config/evergreen_backlog.json`: `backlog`, `drafting`, `reviewed`, `published` or `archived`. Published and archived ideas are excluded from the rotating weekly suggestions, but remain in the backlog file for history. The generator highlights a maximum of five at a time, prioritising higher-priority ideas and rotating those with equal priority.
