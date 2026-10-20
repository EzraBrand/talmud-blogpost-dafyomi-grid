# Talmud Blogpost Daf Yomi Grid

## Combined schedule v2

[Open the combined Daf Yomi and parasha table](https://ezrabrand.github.io/talmud-blogpost-dafyomi-grid/blogpost_schedule_v2.html).

The v2 table preserves all 500 entries from the original grid and adds 117 direct parasha matches, plus 46 optional broader suggestions. Direct matches cover 50 of the 54 portions; broader suggestions cover the other four. Blue rows are Daf Yomi and green rows are parasha entries. Use the schedule-type dropdown, portion, calendar, connection and date filters, or search by title, source or Torah verse. Each row displays its next relevant date, with upcoming matches highlighted above the table. Sort using the column headings. The original grid remains available below.

Torah references are automatically parsed from indexed titles and source citations. A multi-portion range creates a row for every intersecting portion. A single whole chapter uses the portion holding most of its verses. Narrative keywords and curated direct mappings extend coverage; thematic, haftarah and seasonal connections are optional and hidden by default. These are index-based suggestions, not a full-text audit.

Parasha reposts are **two days before the reading**, normally Thursday, on the Israel calendar by default. The browser also supports Diaspora dates. Combined portions share their actual reading date; duplicate events for the same post on the same date are merged. Festival weeks pause the regular cycle, and Vezot Haberakhah is scheduled on Simchat Torah. Daf Yomi uses the first daf in each indexed passage and includes subsequent occurrences in the cached calendar. The v2 period is October 20, 2026 through December 31, 2036. The browser uses the current civil date in Asia/Jerusalem.

### Calendar downloads

All complete downloads include direct matches; broader suggestions can be added using the table's filtered export. Each calendar contains one all-day event per post per reading date, with post URLs, source and multipart links. A post can have several opportunities per year when it spans multiple portions. Import either a combined calendar or the separate calendars.

- [Parasha, Israel](https://ezrabrand.github.io/talmud-blogpost-dafyomi-grid/blogpost_parasha_israel_v2.ics)
- [Parasha, Diaspora](https://ezrabrand.github.io/talmud-blogpost-dafyomi-grid/blogpost_parasha_diaspora_v2.ics)
- [Daf Yomi v2](https://ezrabrand.github.io/talmud-blogpost-dafyomi-grid/blogpost_dafyomi_v2.ics)
- [Combined, Israel](https://ezrabrand.github.io/talmud-blogpost-dafyomi-grid/blogpost_combined_israel_v2.ics)
- [Combined, Diaspora](https://ezrabrand.github.io/talmud-blogpost-dafyomi-grid/blogpost_combined_diaspora_v2.ics)

The CSV button exports the filtered occurrences with dates. `blogpost_schedule_v2.csv` is the complete assignment index, including optional connections. Filtered ICS downloads use the same event UIDs as complete calendars.

### Rebuild v2

Python 3.10+, standard library only:

```sh
python build_schedule_v2.py
python -m unittest test_schedule_v2.py
```

First rebuild the original Daf Yomi grid when its source index changes. V2 reads that grid's embedded data, its existing `dafyomi_2026_2036.json`, the cached Israel/Diaspora calendars in `parasha/`, and editable `parasha/curated_mappings.tsv`. Curated entries are keyed by title and source; missing entries fail clearly instead of silently attaching to a different row. The four non-Talmud entries in `parasha/extra_posts.csv` were supplied in Claude's comparison index. Its verse-based approach informed v2; Torah portion boundaries were retained from that supplied Hebcal-based index, with the duplicate Vezot entry removed. Chapter verse counts were corrected to Hebrew numbering using the official [Hebcal leyning data](https://github.com/hebcal/hebcal-leyning/blob/main/src/numverses.json), avoiding English/Hebrew chapter-boundary mismatches. Calendar caches retain their exact Hebcal request URLs. Main links for multipart entries use the first part when the original index has no main URL.

`--lead-days N` changes the parasha lead interval. All dates are civil dates; ICS events use `VALUE=DATE`. Static generated files can be hosted directly on GitHub Pages without runtime services. `index.html` opens v2; `blogpost_dafyomi_grid.html` preserves v1.

## Original Daf Yomi grid

Builds a CSV, interactive local HTML grid, and iCalendar file from my archived index post:

- Source backup HTML slug: [`cataloguing-my-blogposts-an-organized-78d`](https://www.ezrabrand.com/p/cataloguing-my-blogposts-an-organized-78d)
- Output columns:
  - `page range`
  - `blogpost title`
  - `daf yomi start date`

## Outputs

- `blogpost_dafyomi_db.csv`
- `blogpost_dafyomi_grid.html`
- `blogpost_dafyomi_calendar.ics`

## Features

- `page range` links to ChavrutAI using the starting daf (for example `Rosh Hashanah 11a-b` -> `/talmud/rosh-hashanah/11a`)
- `blogpost title` links to the original EzraBrand post URL (when present in source)
- Multi-part entries append linked `[Pt1] [Pt2] ...` based on the archived HTML
- Daf Yomi dates fetched from Hebcal JSON API
- Date display format: `D-Mon-YYYY` (for example `1-Jan-2026`)

## Rebuild

```powershell
python .\build_blogpost_dafyomi_db.py `
  --archive C:\path\to\blog-export.zip `
  --calendar-json .\dafyomi_2026_2036.json `
  --output-dir .
```

The archive should contain the canonical `posts/*cataloguing-my-blogposts-an-organized*.html` export. The builder extracts that index, maps its cited daf ranges to the cached Hebcal calendar, and writes all three outputs in the selected output directory.

## Open Grid

```powershell
powershell -ExecutionPolicy Bypass -File .\open_blogpost_grid.ps1
```
