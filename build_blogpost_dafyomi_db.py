import csv
import hashlib
import html
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.request import urlopen

BASE = Path(r"C:\Users\ezrab\Downloads")
ZIP_HTML = BASE / "blog_archive_extracted" / "posts" / "135518669.cataloguing-my-blogposts-an-organized-78d.html"
CAL_JSON = BASE / "dafyomi_2026_2036.json"
OUT_CSV = BASE / "blogpost_dafyomi_db.csv"
OUT_HTML = BASE / "blogpost_dafyomi_grid.html"
OUT_ICS = BASE / "blogpost_dafyomi_calendar.ics"

HEBCAL_URL = "https://www.hebcal.com/hebcal?cfg=json&v=1&F=on&start=2026-01-01&end=2036-12-31"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fix_mojibake(s: str) -> str:
    try:
        fixed = s.encode("latin1").decode("utf-8")
        if fixed.count("\ufffd") <= s.count("\ufffd"):
            return fixed
    except Exception:
        return s
    return s


def norm(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


def format_date_human(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day}-{MONTHS[d.month - 1]}-{d.year}"


def clean_text(fragment: str) -> str:
    txt = re.sub(r"<[^>]+>", "", fragment)
    txt = html.unescape(txt)
    txt = fix_mojibake(re.sub(r"\s+", " ", txt).strip())
    return txt


def tractate_alias(raw: str) -> str | None:
    aliases = {
        "berakhot": "Berachot",
        "berachot": "Berachot",
        "shabbat": "Shabbat",
        "eruvin": "Eruvin",
        "pesachim": "Pesachim",
        "roshhashanah": "Rosh Hashana",
        "roshhashana": "Rosh Hashana",
        "yoma": "Yoma",
        "sukkah": "Sukkah",
        "beitzah": "Beitzah",
        "taanit": "Taanit",
        "megillah": "Megillah",
        "moedkatan": "Moed Katan",
        "chagigah": "Chagigah",
        "yevamot": "Yevamot",
        "ketubot": "Ketubot",
        "nedarim": "Nedarim",
        "sotah": "Sotah",
        "gittin": "Gitin",
        "gitin": "Gitin",
        "kiddushin": "Kiddushin",
        "bavakamma": "Baba Kamma",
        "babakamma": "Baba Kamma",
        "bavametzia": "Baba Metzia",
        "babametzia": "Baba Metzia",
        "bavabatra": "Baba Batra",
        "bababatra": "Baba Batra",
        "sanhedrin": "Sanhedrin",
        "makkot": "Makkot",
        "shevuot": "Shevuot",
        "avodahzarah": "Avodah Zarah",
        "avodazarah": "Avodah Zarah",
        "horayot": "Horayot",
        "menachot": "Menachot",
        "chullin": "Chullin",
        "bekhorot": "Bechorot",
        "bechorot": "Bechorot",
        "arakhin": "Arachin",
        "arachin": "Arachin",
        "temurah": "Temurah",
        "keritot": "Keritot",
        "meilah": "Meilah",
        "tamid": "Tamid",
        "niddah": "Niddah",
    }
    return aliases.get(norm(raw))


def tractate_slug(raw: str) -> str | None:
    slugs = {
        "berakhot": "berakhot",
        "berachot": "berakhot",
        "shabbat": "shabbat",
        "eruvin": "eruvin",
        "pesachim": "pesachim",
        "roshhashanah": "rosh-hashanah",
        "roshhashana": "rosh-hashanah",
        "yoma": "yoma",
        "sukkah": "sukkah",
        "beitzah": "beitzah",
        "taanit": "taanit",
        "megillah": "megillah",
        "moedkatan": "moed-katan",
        "chagigah": "chagigah",
        "yevamot": "yevamot",
        "ketubot": "ketubot",
        "nedarim": "nedarim",
        "sotah": "sotah",
        "gittin": "gittin",
        "gitin": "gittin",
        "kiddushin": "kiddushin",
        "bavakamma": "bava-kamma",
        "babakamma": "bava-kamma",
        "bavametzia": "bava-metzia",
        "babametzia": "bava-metzia",
        "bavabatra": "bava-batra",
        "bababatra": "bava-batra",
        "sanhedrin": "sanhedrin",
        "makkot": "makkot",
        "shevuot": "shevuot",
        "avodahzarah": "avodah-zarah",
        "avodazarah": "avodah-zarah",
        "horayot": "horayot",
        "menachot": "menachot",
        "chullin": "chullin",
        "bekhorot": "bekhorot",
        "bechorot": "bekhorot",
        "arakhin": "arakhin",
        "arachin": "arakhin",
        "temurah": "temurah",
        "keritot": "keritot",
        "meilah": "meilah",
        "tamid": "tamid",
        "niddah": "niddah",
    }
    return slugs.get(norm(raw))


def pick_blogpost_url(paragraph_html: str) -> str:
    hrefs = re.findall(r'href="([^"]+)"', paragraph_html, flags=re.I)
    unique: list[str] = []
    seen = set()
    for href in hrefs:
        href = fix_mojibake(html.unescape(href.strip()))
        if href and href not in seen:
            seen.add(href)
            unique.append(href)
    for href in unique:
        if href.startswith("https://www.ezrabrand.com/p/") or href.startswith("https://www.ezrabrand.com/i/"):
            return href
    return unique[0] if unique else ""


def pick_part_links(ol_html: str) -> list[dict[str, str]]:
    links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', ol_html, flags=re.I | re.S)
    out: list[dict[str, str]] = []
    seen = set()
    for href, label_html in links:
        label = clean_text(label_html)
        if not re.match(r"^Pt\s*\d+", label, flags=re.I):
            continue
        label = re.sub(r"\s+", "", label)
        href = fix_mojibake(html.unescape(href.strip()))
        key = (label, href)
        if key in seen:
            continue
        seen.add(key)
        out.append({"label": label, "url": href})
    return out


def load_dafyomi_calendar() -> dict[tuple[str, int], str]:
    with urlopen(HEBCAL_URL, timeout=30) as response:
        payload = response.read().decode("utf-8")
    CAL_JSON.write_text(payload, encoding="utf-8")
    data = json.loads(payload)

    out: dict[tuple[str, int], str] = {}
    for item in data.get("items", []):
        if item.get("category") != "dafyomi":
            continue
        title = item.get("title", "")
        if " " not in title:
            continue
        masekhet, daf_num = title.rsplit(" ", 1)
        key = (masekhet, int(daf_num))
        if key not in out:
            out[key] = item.get("date", "")
    return out


def parse_rows(first_date: dict[tuple[str, int], str]) -> list[dict[str, str]]:
    raw = ZIP_HTML.read_text(encoding="utf-8", errors="ignore")
    blocks = [
        (m.group(1).lower(), m.group(2))
        for m in re.finditer(r"<(p|ol)>(.*?)</\1>", raw, flags=re.I | re.S)
    ]

    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    order = 0
    for i, (tag, content) in enumerate(blocks):
        if tag != "p":
            continue

        txt = clean_text(content)
        if not txt:
            continue

        parens = re.findall(r"\(([^()]*)\)", txt)
        page_range = ""
        for g in reversed(parens):
            if re.search(r"\b\d+[ab]\b", g):
                page_range = fix_mojibake(g.strip())
                break
        if not page_range:
            continue

        m = re.search(r"\b([A-Za-z][A-Za-z\- ]*?)\s+(\d+)([ab])\b", page_range)
        if not m:
            continue

        tract_raw = m.group(1).strip()
        start_daf = int(m.group(2))
        start_amud = m.group(3)

        cal_name = tractate_alias(tract_raw)
        slug = tractate_slug(tract_raw)
        if not cal_name or not slug:
            continue

        title = re.sub(r"\s*\([^()]*\d+[ab][^()]*\)\s*", "", txt).strip().strip("[] ")
        blogpost_url = pick_blogpost_url(content)

        part_links: list[dict[str, str]] = []
        j = i + 1
        while j < len(blocks) and blocks[j][0] == "ol":
            pts = pick_part_links(blocks[j][1])
            if pts:
                part_links.extend(pts)
                j += 1
            else:
                break

        yomi_iso = first_date.get((cal_name, start_daf), "")
        if not yomi_iso:
            continue
        yomi_human = format_date_human(yomi_iso)

        key = (page_range, title)
        if key in seen:
            continue
        seen.add(key)

        rows.append(
            {
                "__order": order,
                "__date_iso": yomi_iso,
                "page range": page_range,
                "blogpost title": title,
                "daf yomi start date": yomi_human,
                "blogpost_url": blogpost_url,
                "part_links": part_links,
                "chavrutai_url": f"https://chavrutai.com/talmud/{slug}/{start_daf}{start_amud}",
            }
        )
        order += 1

    return rows


def write_csv(rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "page range",
        "blogpost title",
        "daf yomi start date",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_html(rows: list[dict[str, str]]) -> None:
    data_json = json.dumps(rows, ensure_ascii=False)
    html_doc = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Cataloguing My Blogposts - Daf Yomi Grid</title>
  <style>
    :root {{
      --bg: #f5f7fb;
      --panel: #ffffff;
      --text: #1c2430;
      --muted: #5f6b7a;
      --line: #d6dde8;
      --head: #eaf0f8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Segoe UI, Arial, sans-serif;
      color: var(--text);
      background: linear-gradient(180deg, #eef3fa 0%, var(--bg) 100%);
    }}
    .wrap {{ max-width: 1240px; margin: 20px auto; padding: 0 14px; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }}
    .top {{ padding: 14px; border-bottom: 1px solid var(--line); display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }}
    .title {{ font-size: 20px; font-weight: 700; margin-right: auto; }}
    .meta {{ color: var(--muted); font-size: 13px; }}
    .search {{ border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; min-width: 280px; font-size: 14px; }}
    .table-wrap {{ overflow: auto; max-height: calc(100vh - 180px); }}
    table {{ width: 100%; border-collapse: collapse; min-width: 980px; table-layout: fixed; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 10px 12px; text-align: left; vertical-align: top; }}
    th {{ position: sticky; top: 0; background: var(--head); font-size: 13px; text-transform: uppercase; letter-spacing: .02em; cursor: pointer; }}
    tr:nth-child(even) td {{ background: #fbfdff; }}
    td:nth-child(1), th:nth-child(1) {{ width: 220px; white-space: normal; overflow-wrap: anywhere; word-break: break-word; }}
    td:nth-child(2), th:nth-child(2) {{ width: 530px; }}
    td:nth-child(3), th:nth-child(3) {{ width: 160px; white-space: nowrap; }}
    a {{ color: #1f5fae; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .pt {{ color: #44566c; margin-left: 4px; white-space: nowrap; }}
    .hint {{ font-size: 12px; color: var(--muted); padding: 10px 14px; border-top: 1px solid var(--line); }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"card\">
      <div class=\"top\">
        <div class=\"title\">Cataloguing My Blogposts: Daf Yomi Grid</div>
        <input id=\"q\" class=\"search\" type=\"search\" placeholder=\"Filter by page range, title, part labels, or date\" />
        <div class=\"meta\" id=\"count\"></div>
      </div>
      <div class=\"table-wrap\">
        <table id=\"grid\">
          <thead>
            <tr>
              <th data-key=\"page range\">Page Range</th>
              <th data-key=\"blogpost title\">Blogpost Title</th>
              <th data-key=\"daf yomi start date\">Daf Yomi Start Date</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <div class=\"hint\">Dates source: Hebcal Daf Yomi. Page range links go to ChavrutAI starting daf. Title links go to EzraBrand posts.</div>
    </div>
  </div>

<script>
const data = {data_json};
const tbody = document.querySelector('#grid tbody');
const countEl = document.getElementById('count');
const q = document.getElementById('q');

let sortKey = '__order';
let sortDir = 'asc';
let filtered = [...data];

function esc(v) {{
  return String(v ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
}}

function link(text, href) {{
  const t = esc(text);
  const h = String(href ?? '');
  if (!h) return t;
  return `<a href="${{esc(h)}}" target="_blank" rel="noopener noreferrer">${{t}}</a>`;
}}

function partLinks(parts) {{
  if (!Array.isArray(parts) || parts.length === 0) return '';
  return parts.map(p => ` <span class="pt">[${{link(p.label, p.url)}}]</span>`).join('');
}}

function cmp(a, b) {{
  if (sortKey === '__order') {{
    return sortDir === 'asc' ? (a.__order - b.__order) : (b.__order - a.__order);
  }}
  if (sortKey === 'daf yomi start date') {{
    const out = String(a.__date_iso).localeCompare(String(b.__date_iso));
    return sortDir === 'asc' ? out : -out;
  }}
  const av = String(a[sortKey] ?? '');
  const bv = String(b[sortKey] ?? '');
  const out = av.localeCompare(bv, undefined, {{ numeric: true, sensitivity: 'base' }});
  return sortDir === 'asc' ? out : -out;
}}

function render() {{
  filtered.sort(cmp);
  tbody.innerHTML = filtered.map(r => `\n<tr>\n<td>${{link(r['page range'], r['chavrutai_url'])}}</td>\n<td>${{link(r['blogpost title'], r['blogpost_url'])}}${{partLinks(r['part_links'])}}</td>\n<td>${{esc(r['daf yomi start date'])}}</td>\n</tr>`).join('');
  countEl.textContent = `${{filtered.length}} rows`;
}}

function rowText(r) {{
  const partText = Array.isArray(r.part_links) ? r.part_links.map(p => `${{p.label}} ${{p.url}}`).join(' ') : '';
  return `${{r['page range']}} ${{r['blogpost title']}} ${{r['daf yomi start date']}} ${{partText}}`.toLowerCase();
}}

function applyFilter() {{
  const term = q.value.trim().toLowerCase();
  if (!term) {{
    filtered = [...data];
  }} else {{
    filtered = data.filter(r => rowText(r).includes(term));
  }}
  render();
}}

document.querySelectorAll('th[data-key]').forEach(th => {{
  th.addEventListener('click', () => {{
    const key = th.getAttribute('data-key');
    if (sortKey === key) {{
      sortDir = sortDir === 'asc' ? 'desc' : 'asc';
    }} else {{
      sortKey = key;
      sortDir = 'asc';
    }}
    render();
  }});
}});

q.addEventListener('input', applyFilter);
render();
</script>
</body>
</html>
"""
    OUT_HTML.write_text(html_doc, encoding="utf-8")


def ics_escape(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def write_ics(rows: list[dict[str, str]]) -> None:
    stamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//EzraBrand//Talmud Blogpost DafYomi//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Talmud Blogposts by Daf Yomi",
    ]

    for r in rows:
        d = date.fromisoformat(r["__date_iso"])
        end = d + timedelta(days=1)
        uid_base = f"{r['__date_iso']}|{r['page range']}|{r['blogpost title']}"
        uid = hashlib.sha1(uid_base.encode("utf-8")).hexdigest() + "@ezrabrand"

        summary = f"{r['page range']} - {r['blogpost title']}"
        description_lines = [
            f"Page range: {r['page range']}",
            f"Blogpost title: {r['blogpost title']}",
            f"Daf Yomi start date: {r['daf yomi start date']}",
        ]
        if r.get("blogpost_url"):
            description_lines.append(f"Blogpost URL: {r['blogpost_url']}")
        if r.get("chavrutai_url"):
            description_lines.append(f"ChavrutAI URL: {r['chavrutai_url']}")
        if r.get("part_links"):
            for p in r["part_links"]:
                description_lines.append(f"{p['label']}: {p['url']}")
        desc = "\n".join(description_lines)

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{stamp}",
                f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
                f"SUMMARY:{ics_escape(summary)}",
                f"DESCRIPTION:{ics_escape(desc)}",
                f"URL:{ics_escape(r.get('blogpost_url') or r.get('chavrutai_url') or '')}",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    OUT_ICS.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")


def main() -> None:
    first_date = load_dafyomi_calendar()
    rows = parse_rows(first_date)
    write_csv(rows)
    write_html(rows)
    write_ics(rows)
    print(f"rows: {len(rows)}")
    print(f"csv: {OUT_CSV}")
    print(f"html: {OUT_HTML}")
    print(f"ics: {OUT_ICS}")


if __name__ == "__main__":
    main()
