# Talmud Blogpost Dafyomi Grid

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
python .\build_blogpost_dafyomi_db.py
```

## Open Grid

```powershell
powershell -ExecutionPolicy Bypass -File .\open_blogpost_grid.ps1
```
