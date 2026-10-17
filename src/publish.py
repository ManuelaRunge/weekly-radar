"""Embed the briefing in README and prepare release notes; no network calls."""
import datetime as dt
import json
import os
from pathlib import Path
import re

from selection import select_items

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- LATEST-BRIEFING:START -->'
END = '<!-- LATEST-BRIEFING:END -->'


def embed_briefing(readme, briefing, error_count):
    if readme.count(START) != 1 or readme.count(END) != 1 or readme.index(START) >= readme.index(END):
        raise ValueError('README must contain one ordered pair of latest-briefing markers')
    # Keep README's title and section hierarchy; preserve all briefing content.
    embedded = re.sub(r'^(#{1,4}) ', r'##\1 ', briefing.strip(), flags=re.MULTILINE)
    status = f'Collection status: **{error_count} source error(s)**. See [source report](data/errors.json).'
    before = readme.split(START)[0]
    after = readme.split(END)[1]
    return before + START + '\n\n' + embedded + '\n\n' + status + '\n\n' + END + after


def release_notes(briefing, items, errors, now, tag='', run_url=''):
    groups = select_items(items, now.date())
    lines = ['# RIDA Radar — run notes', '', f'Generated (UTC): {now.isoformat()}', '']
    if tag:
        lines.extend([f'Tag: `{tag}`', ''])
    if run_url:
        lines.extend([f'[Workflow run]({run_url})', ''])
    lines.extend(['## Run summary', '',
                  f'- Eligible news from the last 7 days: **{len(groups["last_7_days"])}**.',
                  f'- Eligible news from 8–30 days ago: **{len(groups["last_30_days"])}**.',
                  f'- Upcoming events within 180 days: **{len(groups["event"])}**.',
                  '- Refreshed the reading inbox, README briefing and ChatGPT preparation packet.',
                  '- WHO leads within each news period; events are chronological.',
                  '- Automated discovery output; verify original sources before sharing.', '',
                  '## Collection status', ''])
    if errors:
        lines.append(f'Completed with **{len(errors)} source error(s)**; coverage is incomplete.')
        lines.append('')
        for failure in errors:
            lines.append(f'- **{failure["source"]}**: {failure["error"]}')
    else:
        lines.append('All configured source requests completed without reported errors.')
    lines.extend(['', '## Briefing', '', briefing.strip(), ''])
    return '\n'.join(lines)


def main():
    briefing = (ROOT / 'output/latest.md').read_text(encoding='utf-8')
    items = json.loads((ROOT / 'data/items.json').read_text(encoding='utf-8'))
    errors = json.loads((ROOT / 'data/errors.json').read_text(encoding='utf-8'))
    readme_path = ROOT / 'README.md'
    readme = embed_briefing(readme_path.read_text(encoding='utf-8'), briefing, len(errors))
    now = dt.datetime.now(dt.timezone.utc)
    repository = os.environ.get('GITHUB_REPOSITORY', '')
    run_id = os.environ.get('GITHUB_RUN_ID', '')
    run_url = f'https://github.com/{repository}/actions/runs/{run_id}' if repository and run_id else ''
    notes = release_notes(briefing, items, errors, now, os.environ.get('RADAR_TAG', ''), run_url)
    readme_path.write_text(readme, encoding='utf-8')
    (ROOT / 'output/release_notes.md').write_text(notes, encoding='utf-8')
    print('Updated README briefing and output/release_notes.md')


if __name__ == '__main__':
    main()
