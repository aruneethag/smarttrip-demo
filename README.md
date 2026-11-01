# SmartTrip AI

A local, demo-first travel planner built from `chatbot_build.md`. No API keys, paid services, package installation, or internet connection is needed.

**Render deployment:** ready-to-use Free-plan configuration and a clean upload archive are supported. See [deployment instructions](docs/deploy-render.md). Run `python scripts/package_release.py` to build `release/smarttrip-render.zip`, which excludes local trip data, secrets, and screenshots. GitHub upload and actual deployment require connected accounts and have not yet been performed. On Render Free, SQLite data is temporary and can disappear on sleep/restart/redeploy; export trips you want to keep.

## Run

Requires Python 3.12+ (tested on Python 3.12.11, Windows) and a modern browser.

```powershell
cd C:\astro_aru
python server.py
```

Open http://127.0.0.1:8000. For a different port: `python server.py --port 8001`.

Try the Lisbon sample, choose **Review trip details**, inspect the summary, and select **Confirm & generate demo**. Describe a trip in chat with a supported city, ISO dates, number of people, and an explicit currency budget, for example:

> Lisbon from 2027-04-12 to 2027-04-14 for 2 people, EUR 900, food and culture, slow pace

Chat intake is deliberately rule-based. Review extracted details in the form. It cannot reliably understand arbitrary natural language. Revisions include “make day two cheaper”, “replace an activity on day 1”, and “add a break on day 3”. Buttons also replace activities, edit day titles, and update whole-party costs (leave blank for unknown).

## Behavior

- Desktop chat beside the plan; mobile chat/itinerary tabs, visible focus, labeled controls, and status announcements.
- Confirmation before generation; changing intake invalidates confirmation while preserving the last itinerary.
- One destination, 1–14 inclusive dates, 1–12 travelers, seven currencies (USD, EUR, GBP, INR, JPY, CAD, AUD).
- Five supported IANA destination time zones: Europe/Lisbon, Europe/Paris, America/Chicago, Asia/Tokyo, Asia/Kolkata. Dates and times represent destination-local wall times; there is no UTC conversion or routing service.
- Fictional sample places, party-wide integer minor-unit costs, meal/rest/transport buffers, unknown costs, exclusions, and consistent totals.
- SQLite saved trips, hashed anonymous session identifiers, HTTP-only SameSite cookies, ownership checks, 30-day retention, stale revision checks, idempotent generation/revision, origin checks, and per-session mutation rate limits.
- Automatic save after each successful change. Refresh restores the most recently updated trip. Save also verifies that the trip is in the saved list.
- JSON and Markdown downloads, print stylesheet, confirmed trip/session deletion.

## Commands

```powershell
python -m unittest discover -s tests -v
python -m py_compile server.py planner.py schema.py
node --check static/app.js
python server.py --cleanup
```

Node is optional and only used for the JavaScript syntax check. No compilation/bundle step exists: the server serves the source HTML, CSS, and JS directly.

Schedule `python C:\astro_aru\server.py --cleanup` daily with Windows Task Scheduler, using the project directory as the working directory and the same `SMARTTRIP_DB` value as the app. Cleanup also runs at startup, and an expired session is rejected on access. SQLite foreign-key cascades remove trips, conversations, and cached request results. No app backup system is configured. Files copied manually are outside deletion control.

## Configuration

`.env.example` documents the options; the application reads process environment variables and does **not** automatically load `.env` files. Defaults: `HOST=127.0.0.1`, `PORT=8000`, `SMARTTRIP_DB=data/smarttrip.sqlite3`, `SECURE_COOKIES=0`. Use an absolute database path for a scheduled task.

For local development keep the loopback host. The Render testing configuration binds `0.0.0.0`, honors `PORT`, enables Secure cookies and HTTPS origin checks, and displays the temporary-storage notice. This standard-library HTTP server is a prototype, not a hardened production server. A larger production deployment requires a production HTTP stack, durable storage, and load/security review. The user has requested preparation for a GitHub/Render testing deployment; no paid services are authorized.

## Architecture

`server.py` provides JSON endpoints and SQLite persistence; `planner.py` holds the demo adapter, intake parsing, revision rules, costs, exports, and business validation; `schema.py` interprets the exact JSON Schema keywords used by the canonical contract in `schemas/itinerary.schema.json`. It is not a general-purpose JSON Schema engine. The checked-in schema is the single runtime source, so no second generated copy can drift. Tests include valid and malformed plans. `static/` contains the responsive UI. All user content is escaped before HTML rendering; model-generated HTML is not used.

There are no third-party runtime packages or lockfile. Python and the browser supply the runtime. The suggested Next.js/Prisma stack was replaced to make the app runnable in this environment without unavailable package downloads. See `docs/decisions.md`.

## Privacy and limits

No external AI, maps, weather, routing, places, currency conversion, or booking providers are enabled. No live provider credentials are accepted. Demo fixtures never claim real venue availability or current prices. The nominal sample prices in each chosen currency are illustrative, not converted or market-based. Included accommodation allocates a nightly estimate for each date including the last date; verify the actual number of nights. Travel to the destination remains an explicit unknown when included.

Optional access/dietary notes are stored locally with the trip only after submission; the UI warns before collection. Database records are not encrypted at rest; protect the computer and local data directory. Clearing the session cookie can remove access to saved records. In-progress text that has not been submitted is not saved. Raw cookies, provider secrets, full messages, and sensitive preferences are not written to application logs.

Live adapters, provider timeouts/repair/retries, live failure simulation, arbitrary time zones, arrival/departure intake, and observed research with real users remain future work. No fabricated interviews or live-provider test claims are included. Acceptance scenario 7 is not applicable to this demo and remains unimplemented for a connected release. See `docs/test-results.md` for the exact verification scope.
