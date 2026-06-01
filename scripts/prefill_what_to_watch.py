#!/usr/bin/env python3
"""
prefill_what_to_watch.py

Reads signal-brief.html, extracts all Critical / Elevated / Watch signal rows,
and prints draft "What to Watch" bullets to stdout.

With --write the script replaces the existing <ul> under "What to Watch Next Week"
in signal-brief.html with the generated bullets. Each bullet contains inline
placeholder text ([WATCH — <headline>]) that the editor must replace with specific,
forward-looking language before publishing.

Usage:
    python scripts/prefill_what_to_watch.py            # preview only
    python scripts/prefill_what_to_watch.py --write    # update the HTML in place
"""

import re
import sys

SIGNAL_FILE = 'signal-brief.html'
ACTIVE_LEVELS = {'critical', 'elevated', 'watch'}

RE_LEVEL = re.compile(r'class="level-box level-(\w+)"[^>]*>([^<]+)<')
RE_LABEL = re.compile(r'class="signal-label">([^<]+)<')
RE_HEADLINE = re.compile(r'class="signal-headline">([^<]+)<')

RE_WTW_UL = re.compile(
    r'(<h2>What to Watch Next Week</h2>\s*)<ul[^>]*>.*?</ul>',
    re.DOTALL,
)


def extract_signals(html: str) -> list[dict]:
    """Return a list of dicts for every signal row at an active alert level.

    Splits the file on <div class="signal-row"> boundaries to avoid
    the need for a complex multi-level regex.
    """
    chunks = html.split('<div class="signal-row">')
    signals = []
    for chunk in chunks[1:]:  # skip content before first signal-row
        level_match = RE_LEVEL.search(chunk)
        label_match = RE_LABEL.search(chunk)
        headline_match = RE_HEADLINE.search(chunk)
        if not (level_match and label_match and headline_match):
            continue
        level_key = level_match.group(1).lower()
        if level_key not in ACTIVE_LEVELS:
            continue
        signals.append({
            'level': level_match.group(2).strip(),
            'level_key': level_key,
            'label': label_match.group(1).strip(),
            'headline': headline_match.group(1).strip(),
        })
    return signals


def build_bullet(signal: dict) -> str:
    """Return a single <li> string for the signal."""
    label = signal['label']
    headline = signal['headline']
    level = signal['level']
    return (
        f'      <li>{label} [{level}]: '
        f'[WATCH \u2014 {headline}]</li>'
    )


def build_ul(signals: list[dict]) -> str:
    items = '\n'.join(build_bullet(s) for s in signals)
    return (
        '<ul style="margin:0;padding:0 0 0 18px;'
        'color:#374151;font-size:.9rem;line-height:1.9;">\n'
        f'{items}\n'
        '    </ul>'
    )


def main():
    write_mode = '--write' in sys.argv

    with open(SIGNAL_FILE, 'r', encoding='utf-8') as f:
        html = f.read()

    signals = extract_signals(html)

    if not signals:
        print('No Critical/Elevated/Watch signals found — nothing to do.')
        sys.exit(0)

    print(f'Found {len(signals)} active signal(s):\n')
    for s in signals:
        print(f'  [{s["level"]}] {s["label"]}')
        print(f'    {s["headline"]}')
        print()

    print('--- Draft "What to Watch" bullets ---\n')
    for s in signals:
        print(build_bullet(s).strip())
    print()

    if not write_mode:
        print('Run with --write to replace the existing bullets in signal-brief.html.')
        return

    new_ul = build_ul(signals)

    def replacer(m):
        return m.group(1) + new_ul

    new_html, n = RE_WTW_UL.subn(replacer, html)
    if n == 0:
        print('ERROR: Could not locate the "What to Watch" <ul> in the file.')
        sys.exit(1)

    with open(SIGNAL_FILE, 'w', encoding='utf-8') as f:
        f.write(new_html)

    print(f'Updated {SIGNAL_FILE} with {len(signals)} draft bullets.')
    print('Open the file and replace each [WATCH \u2014 ...] placeholder with specific,')
    print('forward-looking language before publishing.')


if __name__ == '__main__':
    main()
