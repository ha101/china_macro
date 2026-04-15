# China Macro Dashboard

A self-contained static dashboard that pulls a local macro snapshot into the page and keeps the
full cycle map explorable.

## What is included

- `index.html`: the dashboard shell and layout.
- `styles.css`: the visual system and responsive styling.
- `data.js`: the cycle, metric, and source catalog.
- `snapshot.js`: the generated live snapshot rendered by the page.
- `refresh_snapshot.py`: the refresh script that fetches the current source snapshot.
- `app.js`: the filtering and rendering logic.

## How to open it

Open [index.html](/Users/gc/Documents/china_health/index.html) directly in a browser, or run:

```bash
python3 -m http.server 8000
```

Then visit `http://localhost:8000`.

The main live URL is the plain root:

```text
http://localhost:8000/
```

Older cache-busting `?v=...` links are normalized back to the root page automatically.

## Refresh the data

Run:

```bash
python3 refresh_snapshot.py
```

That regenerates [snapshot.js](/Users/gc/Documents/china_health/snapshot.js) from the latest
accessible free sources wired into the script.

## Current scope

The page now renders a pulled snapshot directly in the browser. It is meant to help with:

- reviewing the latest accessible values for the wired metrics;
- keeping official Chinese sources ahead of market-data fallbacks;
- browsing the full 152-metric cycle map while seeing the backing release context for each metric.

The latest refresh currently yields:

- 139 parsed live metric values in the generated snapshot;
- 40 pulled source snapshots rendered directly on the page;
- direct values on all 152 of the 152 dashboard metric cards;
- one-year-or-better history attached for 50 metric series in the snapshot layer, covering 56
  dashboard metric cards.

## Easy next extensions

- Replace the remaining fallback or proxy paths with cleaner first-party customs and city-policy
  parsers where the public official endpoints are still brittle.
- Add historical time series storage rather than a latest-snapshot-only view.
- Export the merged metric snapshot to JSON or CSV for research workflows.
