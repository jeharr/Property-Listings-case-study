Tech Stack: Typescript/React + Tanstack, Python/FastApi, Sqlite/SQLAlchemy

## How to run locally

Prerequisites: Python 3.12+ and Node.js 22.12+ (tested with Python 3.14 and Node 24 on macOS).

From the repository root:

```sh
python3 run.py
```

On Windows, use `py -3 run.py` with Python 3.12+. No Docker, SQLite command-line tool, or manual virtual-environment activation is needed. Internet access is required for the first dependency installation.

The launcher creates `.venv`, installs the pinned Python and locked npm dependencies, applies Alembic migrations, and seeds the sample data when initializing a new database. Existing listings—including edits and deletions—are preserved. It then starts FastAPI with auto-reload and Vite, checks that the frontend can reach the API, and prints the ready URLs:

- Application: [http://127.0.0.1:5173](http://127.0.0.1:5173)

Keep that terminal open. **Control+C stops both servers**, including their child processes. Later launches reuse installed dependencies unless their manifest/lockfile changes; use `python3 run.py --reinstall` to force dependency installation again. If either server exits, the launcher stops the other and reports the failure.

If ports 8000 or 5173 are already occupied, stop your previous servers or choose different ports. The launcher does not terminate existing processes:

```sh
python3 run.py --api-port 8002 --web-port 5175
```

The frontend proxy automatically follows the selected API port. `LISTINGS_DB_PATH` is also respected if you want a different SQLite file.

````

## Relevancy Algorithm

For price `p`, target budget `b`, and listing age `d` in days:

```text
budget_proximity = max(0, 1 - abs(p - b) / b)
half_life_days   = 365 if no target budget is supplied, otherwise 90
recency          = 2 ** (-max(0, d) / half_life_days)
relevance        = 100 * (0.70 * budget_proximity + 0.30 * recency)
````

Without a target budget, `relevance = 100 * recency`, with a 365-day half-life: a listing 365 days old scores 50, and one 730 days old scores 25. With a target budget, the existing 90-day half-life applies to the recency component. Scores range from 0 to 100. An exact budget match listed 90 days ago scores 85; a listing 10% above or below that budget at the same age scores 78. This symmetric distance measures proximity to an ideal price, so it does not express a preference for cheaper homes. The 70/30 weighting makes budget fit the primary signal, while smooth recency decay avoids an arbitrary cutoff for older listings. I used a larger 365-day half-life because our most recent listing is still several months old and I wanted it to show high relevancy when accounting for recency only.

Ranking uses unrounded scores across **all matches before pagination**. Exact ties resolve by newest date, then source and ID in ascending, case-sensitive lexical order. The API rounds score components to four decimal places and the UI shows two, so visually equal scores may differ at full precision.

Fetching uses TanStack Query with a shared `QueryClientProvider`. Query keys include all applied filters and the page number. Pages remain fresh for 30 seconds, allowing quick back/forward navigation to reuse results

## Some Trade Offs

My Relevancy formula weighs towards the closest budget proximity but perhaps it would be more desirable to always give a slight edge to the lowest price in an approximate range

I would probably adjust the formula a bit if working with a more recent data set, but I still wanted the most recent listings to have a high score

A 30-second cache speeds repeat navigation, but database changes may remain temporarily unseen

If dealing with a much larger scale of listings DB queries and indexes would be a bigger consideration.

## Testing

From the repository root:

```sh
.venv/bin/python -m pytest -q
npm test --prefix frontend
npm run build --prefix frontend
npm run format:check --prefix frontend
```

For browser tests, install Chromium once, then run the suite:

```sh
cd frontend
npx playwright install chromium
npm run test:e2e
```

Playwright starts real backend and frontend servers on ports 8001 and 5174 and stops them afterward; leave those ports free.

`npm run build --prefix frontend` type-checks the app and produces `frontend/dist`. With FastAPI running, `npm run preview --prefix frontend` previews that build locally.
