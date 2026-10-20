"""Combine the existing Daf Yomi index with annual parasha repost suggestions.

Python 3.10+, standard library only. Run from any working directory.
"""
import argparse
import csv
import hashlib
import html
import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARASHA = ROOT / 'parasha'
START, END = '2026-10-20', '2036-12-31'
BOOKS = {'genesis': 'Genesis', 'gen': 'Genesis', 'exodus': 'Exodus', 'exod': 'Exodus', 'ex': 'Exodus', 'leviticus': 'Leviticus', 'lev': 'Leviticus', 'numbers': 'Numbers', 'num': 'Numbers', 'deuteronomy': 'Deuteronomy', 'deut': 'Deuteronomy'}
NUM = r'\d+(?::\d+)?(?:\s*[-–—]\s*\d+(?::\d+)?)?'
REF = re.compile(r'\b(Genesis|Gen\.?|Exodus|Exod\.?|Ex\.|Leviticus|Lev\.?|Numbers|Num\.?|Deuteronomy|Deut\.?)\s+(' + NUM + r'(?:\s*(?:,|and)\s*' + NUM + r')*)', re.I)
ONE = re.compile(r'(\d+)(?::(\d+))?(?:\s*[-–—]\s*(\d+)(?::(\d+))?)?')
KEYWORDS = [
    (r"Adam['’]s Creation|The First Man", 'Genesis 2:7'),
    (r"Noah['’]s Flood|Noah['’]s Ark|From Noah", 'Genesis 6:9'),
    (r"Nimrod['’]s Furnace", 'Genesis 11:28'),
    (r'\bSodom\b', 'Genesis 19:1'),
    (r"Esau['’]s .*Birthright", 'Genesis 25:29'),
    (r"Jacob['’]s Descent to Egypt", 'Genesis 46:1'),
    (r'Splitting of the Sea', 'Exodus 14:21'),
    (r'Giving of the Torah|Revelation at Sinai|Ten Commandments', 'Exodus 19:1'),
    (r'Golden Calf', 'Exodus 32:1'),
    (r'Korah', 'Numbers 16:1'),
]


def norm(text):
    return ''.join(c.lower() for c in text if c.isalnum())


class TorahIndex:
    def __init__(self):
        self.portions = json.loads((PARASHA / 'portion_boundaries.json').read_text())
        self.verses = json.loads((PARASHA / 'torah_chapter_verses.json').read_text())
        assert len(self.portions) == len({p['name'] for p in self.portions}) == 54
        self.by_name = {norm(p['name']): p for p in self.portions}

    def refs(self, text):
        result = []
        for match in REF.finditer(text):
            book = BOOKS[match[1].rstrip('.').lower()]
            for fragment in re.split(r'\s*(?:,|and)\s*', match[2], flags=re.I):
                m = ONE.fullmatch(fragment.strip())
                if not m:
                    continue
                c1, v1, x, y = (int(s) if s else None for s in m.groups())
                c2 = x if y is not None or (x is not None and v1 is None) else c1
                if not 1 <= c1 <= c2 <= len(self.verses[book]):
                    continue
                v2 = y if y is not None else (x if x is not None and v1 is not None else (v1 if v1 is not None else self.verses[book][c2 - 1]))
                lo, hi = (c1, v1 or 1), (c2, v2)
                if lo > hi or hi[1] > self.verses[book][c2 - 1] or lo[1] > self.verses[book][c1 - 1]:
                    continue
                result.append(dict(book=book, start=lo, end=hi, chapter_only=v1 is None, label=book + ' ' + fragment.strip()))
        return result

    def portions_for(self, ref):
        # A single unnumbered chapter maps to the portion holding most of it.
        # Ranges map to EVERY intersecting portion, with real verse endpoints.
        hits = [p for p in self.portions if p['book'] == ref['book'] and tuple(p['start']) <= ref['end'] and tuple(p['end']) >= ref['start']]
        if ref['chapter_only'] and ref['start'][0] == ref['end'][0] and hits:
            def overlap(p):
                lo = max(ref['start'], tuple(p['start']))
                hi = min(ref['end'], tuple(p['end']))
                return hi[1] - lo[1] + 1
            return [max(hits, key=overlap)]
        return hits


def source_posts():
    raw = (ROOT / 'blogpost_dafyomi_grid.html').read_text(encoding='utf-8-sig')
    found = re.search(r'const data = (\[.*?\]);\s*\n', raw, re.S)
    if not found:
        raise ValueError('Original Daf Yomi grid contains no data array')
    result = []
    for r in json.loads(found[1]):
        parts = r.get('part_links', [])
        result.append(dict(title=r['blogpost title'], source=r['page range'], url=r.get('blogpost_url') or next((p['url'] for p in parts if p.get('url')), ''), part_links=parts, source_url=(r.get('chavrutai_url') or '').replace('https://chavrutai.com/', 'https://bekiut.com/'), original_date=r['__date_iso']))
    return result


def calendar(region, index):
    events = json.loads((PARASHA / f'calendar_{region}.json').read_text())['items']
    dates = defaultdict(list)
    for event in events:
        d = event['date'][:10]
        if not START <= d <= END:
            continue
        if event['category'] == 'parashat':
            label = event['title'].removeprefix('Parashat ')
            # Portion names themselves may contain hyphens, e.g. Lech-Lecha.
            names = [p['name'] for p in index.portions if norm(p['name']) == norm(label)]
            if not names:
                names = next(([a['name'], b['name']] for a in index.portions for b in index.portions if norm(a['name'] + b['name']) == norm(label)), [])
            if not names:
                raise ValueError('Unknown parasha: ' + label)
        elif event['title'] == ('Shmini Atzeret' if region == 'israel' else 'Simchat Torah'):
            label, names = 'Vezot Haberakhah (Simchat Torah)', ['Vezot Haberakhah']
        else:
            continue
        portions = [index.by_name[norm(name)] for name in names]
        first, last = portions[0], portions[-1]
        full_range = f"{first['book']} {first['start'][0]}:{first['start'][1]}-{last['end'][0]}:{last['end'][1]}"
        short_range = chapter_range(first['book'], first['start'][0], last['end'][0])
        for name in names:
            dates[norm(name)].append(dict(reading=d, label=label, parasha_range=full_range, chapter_range=short_range, torah=event.get('leyning', {}).get('torah', full_range), calendar_url=event.get('link', 'https://www.hebcal.com/')))
    return dates


def chapter_range(book, first, last):
    short = {'Genesis': 'Gen', 'Exodus': 'Ex', 'Leviticus': 'Lev', 'Numbers': 'Num', 'Deuteronomy': 'Deut'}[book]
    return f'{short} {first}' + (f'–{last}' if last != first else '')


def previous_sunday(iso):
    d = date.fromisoformat(iso)
    return str(d - timedelta(days=(d.weekday() + 1) % 7 or 7))


def reading_events(region='israel'):
    unique = {}
    for events in calendar(region, TorahIndex()).values():
        for event in events:
            unique[event['reading']] = event
    return [unique[d] for d in sorted(unique)]


def build_rows():
    index = TorahIndex()
    originals = source_posts()
    daf = json.loads((ROOT / 'dafyomi_2026_2036.json').read_text())['items']
    by_date = {i['date']: i['title'] for i in daf if i['category'] == 'dafyomi'}
    by_daf = defaultdict(list)
    for i in daf:
        if i['category'] == 'dafyomi' and START <= i['date'] <= END:
            by_daf[i['title']].append(dict(post=i['date'], reading=i['date'], label=i['title']))
    rows = []
    for post in originals:
        title = by_date[post['original_date']]
        rows.append(dict(type='Daf Yomi', trigger=title, order=0, match='Daf', optional=False, torah_refs=[], connection='The first daf in the indexed Talmud passage. Includes every matching date in the cached 2026–2036 Daf Yomi calendar.', dates={'israel': by_daf[title], 'diaspora': by_daf[title]}, **post))
    # Candidate assignments are merged by post AND portion. Automatic verse
    # evidence takes priority; explicit editorial explanations remain attached.
    assigned = {}
    post_lookup = {(p['title'], p['source']): p for p in originals}
    with (PARASHA / 'curated_mappings.tsv').open(newline='') as f:
        curated = list(csv.DictReader(f, delimiter='\t'))
    extras = []
    with (PARASHA / 'extra_posts.csv').open(encoding='utf-8-sig', newline='') as f:
        for p in csv.DictReader(f):
            extras.append(dict(title=p['title'], source=p['source'], url=p['url'], part_links=[], source_url='', original_date='', explicit_torah_ref=p['torah_ref']))

    def add(post, portion, method, reason, refs=None, optional=False):
        key = (post['title'], post['source'], portion['name'])
        if key not in assigned:
            assigned[key] = dict(type='Parasha', trigger=portion['name'], order=portion['order'], match=method, optional=optional, torah_refs=[], connection=reason, portion_range=portion['summary'], chapter_range=chapter_range(portion['book'], portion['start'][0], portion['end'][0]), **post)
        row = assigned[key]
        for ref in refs or []:
            item = dict(text=ref['label'], url=f"https://www.sefaria.org/{ref['book']}.{ref['start'][0]}.{ref['start'][1]}")
            if item not in row['torah_refs']:
                row['torah_refs'].append(item)
        if reason and reason not in row['connection']:
            row['connection'] += ' ' + reason

    for post in originals + extras:
        explicit = post.get('explicit_torah_ref')
        refs = index.refs(explicit or (post['source'] + '; ' + post['title']))
        method = 'Verse'
        if not refs:
            for pattern, anchor in KEYWORDS:
                if re.search(pattern, post['title'], re.I):
                    refs = index.refs(anchor)
                    method = 'Keyword'
                    break
        for ref in refs:
            for portion in index.portions_for(ref):
                reason = ('Explicit Torah reference: ' if method == 'Verse' else 'Narrative keyword anchor: ') + ref['label'] + '.'
                add(post, portion, method, reason, [ref])
    for m in curated:
        post = post_lookup.get((m['title'], m['source']))
        if post is None:
            raise ValueError('Curated post missing from current index: ' + m['title'])
        portion = index.by_name[norm(m['parasha'])]
        # Do not interpret every verse in an explanation as a direct match:
        # contextual comparisons often refer to a different portion.
        refs = index.refs(m['connection']) if m['match_type'] == 'Direct' else []
        refs = [ref for ref in refs if portion in index.portions_for(ref)]
        add(post, portion, 'Curated direct' if m['match_type'] == 'Direct' else m['match_type'], m['connection'], refs, m['match_type'] != 'Direct')
    calendars = {region: calendar(region, index) for region in ['israel', 'diaspora']}
    for row in assigned.values():
        row['dates'] = {}
        for region in calendars:
            row['dates'][region] = [dict(d, post=previous_sunday(d['reading'])) for d in calendars[region][norm(row['trigger'])]]
        rows.append(row)
    for row in rows:
        row['id'] = hashlib.sha256((row['type'] + '|' + row['trigger'] + '|' + row['source'] + '|' + row['title']).encode()).hexdigest()[:24]
        row['event_id'] = hashlib.sha256((row['type'] + '|' + row['source'] + '|' + row['title']).encode()).hexdigest()[:24]
    return rows


def ics_escape(text):
    return str(text).replace('\\', '\\\\').replace('\n', '\\n').replace(';', '\\;').replace(',', '\\,')


def fold(text):
    parts, cur = [], ''
    for char in text:
        if len((cur + char).encode('utf-8')) > 75:
            parts.append(cur)
            cur = ' '
        cur += char
    return '\r\n'.join(parts + [cur])


def calendar_ics(rows, region, kind=None, include_optional=False):
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH', 'PRODID:-//EzraBrand//Blogpost Schedule V2//EN', 'X-WR-CALNAME:' + ics_escape('Talmud & Tech - ' + (kind or 'Combined') + ' - ' + region.title())]
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    seen = set()
    for row in rows:
        if (kind and row['type'] != kind) or (row['optional'] and not include_optional):
            continue
        for event in row['dates'][region]:
            key = (row['event_id'], event['reading'])
            if key in seen:
                continue
            seen.add(key)
            d = date.fromisoformat(event['post'])
            desc = [f"{row['type']}: {event['label']}", f"Reading date: {event['reading']}", f"Post: {row['title']}", f"Source: {row['source']}", f"Match: {row['match']}", row['connection'], row['url']]
            desc += [f"{p['label']}: {p['url']}" for p in row['part_links']]
            if row['source_url']:
                desc.append('Bekiut: ' + row['source_url'])
            desc += [r['text'] + ': ' + r['url'] for r in row['torah_refs']]
            uid_region = region if row['type'] == 'Parasha' else 'both'
            uid = f"v2-{uid_region}-{row['event_id']}-{event['reading']}@ezrabrand.com"
            lines += ['BEGIN:VEVENT', 'UID:' + uid, 'DTSTAMP:' + stamp, 'DTSTART;VALUE=DATE:' + d.strftime('%Y%m%d'), 'DTEND;VALUE=DATE:' + (d + timedelta(days=1)).strftime('%Y%m%d'), 'SUMMARY:' + ics_escape(f"[{row['type']}] {event['label']} - {row['title']}"), 'DESCRIPTION:' + ics_escape('\n'.join(desc)), 'URL:' + row['url'], 'CATEGORIES:' + ('Parasha' if row['type'] == 'Parasha' else 'Daf Yomi'), 'TRANSP:TRANSPARENT', 'END:VEVENT']
    if kind != 'Daf Yomi':
        for event in reading_events(region):
            d = date.fromisoformat(event['reading'])
            desc = f"Israel reading schedule" if region == 'israel' else 'Diaspora reading schedule'
            desc += f"\nParasha: {event['label']}\nTorah range: {event['parasha_range']}\nChapter range: {event['chapter_range']}"
            lines += ['BEGIN:VEVENT', f"UID:v2-{region}-parasha-reading-{event['reading']}@ezrabrand.com", 'DTSTAMP:' + stamp, 'DTSTART;VALUE=DATE:' + d.strftime('%Y%m%d'), 'DTEND;VALUE=DATE:' + (d + timedelta(days=1)).strftime('%Y%m%d'), 'SUMMARY:' + ics_escape(f"Parashat {event['label']} ({event['chapter_range']})"), 'DESCRIPTION:' + ics_escape(desc), 'URL:' + event['calendar_url'], 'CATEGORIES:Parasha', 'TRANSP:TRANSPARENT', 'END:VEVENT']
    return '\r\n'.join(map(fold, lines + ['END:VCALENDAR'])) + '\r\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    rows = build_rows()
    metadata = dict(start=START, end=END, repost_rule='preceding_sunday', schedule='Israel', built=datetime.now(timezone.utc).isoformat(), source_posts=len(source_posts()))
    embedded = json.dumps(dict(meta=metadata, rows=rows, readings=reading_events('israel')), ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    template = (ROOT / 'schedule_v2_template.html').read_text()
    (ROOT / 'blogpost_schedule_v2.html').write_text(template.replace('__DATA__', embedded), encoding='utf-8')
    # Keep one stable entry point for the combined table; v1 remains available.
    (ROOT / 'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=blogpost_schedule_v2.html"><title>Blogpost Schedule v2</title><a href="blogpost_schedule_v2.html">Open the combined Daf Yomi and parasha schedule</a></html>\n')
    for region in ['israel', 'diaspora']:
        for kind, filename in [('Parasha', f'blogpost_parasha_{region}_v2.ics'), (None, f'blogpost_combined_{region}_v2.ics')]:
            (ROOT / filename).write_bytes(calendar_ics(rows, region, kind).encode('utf-8'))
    (ROOT / 'blogpost_dafyomi_v2.ics').write_bytes(calendar_ics(rows, 'israel', 'Daf Yomi').encode('utf-8'))
    with (ROOT / 'blogpost_schedule_v2.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['type', 'trigger', 'title', 'source', 'match', 'optional', 'torah_references', 'url', 'part_links', 'connection'])
        for row in rows:
            w.writerow([row['type'], row['trigger'], row['title'], row['source'], row['match'], row['optional'], '; '.join(r['text'] for r in row['torah_refs']), row['url'], '; '.join(p['label'] + ': ' + p['url'] for p in row['part_links']), row['connection']])
    core = [r for r in rows if r['type'] == 'Parasha' and not r['optional']]
    print(f"Daf Yomi rows: {sum(r['type'] == 'Daf Yomi' for r in rows)}; parasha core: {len(core)}; optional: {sum(r['optional'] for r in rows)}; core portions: {len({r['trigger'] for r in core})}/54")


if __name__ == '__main__':
    main()
