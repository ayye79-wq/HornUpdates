import re
import sys
from datetime import datetime, timedelta

MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]

def fmt_week(monday, sunday):
    if monday.month == sunday.month:
        return f"{MONTHS[monday.month - 1]} {monday.day} to {sunday.day}, {sunday.year}"
    return (
        f"{MONTHS[monday.month - 1]} {monday.day} to "
        f"{MONTHS[sunday.month - 1]} {sunday.day}, {sunday.year}"
    )

def main():
    today = datetime.utcnow()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    new_week = fmt_week(monday, sunday)

    with open('signal-brief.html', 'r', encoding='utf-8') as f:
        content = f.read()

    week_match = re.search(r'Week of ([A-Za-z]+ \d+ to [A-Za-z]* ?\d+, \d+)', content)
    issue_match = re.search(r'Issue (\d+)', content)

    if not week_match or not issue_match:
        print("Could not find week or issue markers — skipping")
        sys.exit(0)

    current_week = week_match.group(1)
    current_issue = int(issue_match.group(1))
    new_issue = current_issue + 1

    if current_week == new_week:
        print(f"Already up to date: {current_week}")
        sys.exit(0)

    content = content.replace(f'Week of {current_week}', f'Week of {new_week}', 1)
    content = re.sub(
        r'(·\s*Issue )\d+',
        lambda m: m.group(1) + str(new_issue),
        content,
        count=1
    )

    new_entry = (
        f'    <a class="archive-link" href="/signal-brief.html">'
        f'Issue {current_issue}: {current_week} <span>&#8594;</span></a>\n'
    )
    marker = '<a class="archive-link"'
    idx = content.find(marker)
    if idx >= 0:
        content = content[:idx] + new_entry + content[idx:]

    with open('signal-brief.html', 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Updated: Issue {current_issue} to {new_issue}")
    print(f"Week: {current_week} to {new_week}")

if __name__ == '__main__':
    main()
