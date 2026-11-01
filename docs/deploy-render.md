# Deploy the free testing demo on Render

This setup is for a small public demo with fictional itinerary content. No paid AI or travel providers are used. The Render blueprint explicitly selects `plan: free`. Do not upgrade plans, add paid disks, or add paid databases as part of these instructions.

## Storage and testing expectations

Render Free services sleep after 15 idle minutes. A subsequent visit can take about a minute to wake the app. The local filesystem, including this SQLite database, is ephemeral: saved trips and session records can disappear on sleep, restart, or deployment. Free services cannot attach a persistent disk. Export trips before relying on them. The app displays this limitation when `EPHEMERAL_STORAGE=1`.

The 30-day policy is a maximum retention period, not a durability guarantee. Each visitor gets an HTTP-only, Secure, SameSite session cookie on HTTPS; visitors cannot access each other's saved trips. Anyone with the service URL can use the demo; it does not have a login restriction.

Sources: https://render.com/docs/free and https://render.com/docs/web-services (checked 2026-11-01).

## Prepare a clean upload

Run `python scripts/package_release.py`. Extract `release/smarttrip-render.zip` into a new folder. This is an explicit allowlist: it includes application code, schema, tests, deployment configuration, and setup documentation, but excludes `data/`, database files, `.env`, personal data, local screenshots, and local caches. `.env.example` contains placeholders and public configuration only.

The server creates the database's parent folders and empty tables automatically at startup. Do not upload a populated database or create a placeholder database.

## GitHub

Create a private repository named `smarttrip-demo` (or choose your own). Push the extracted release folder to it. A private source repository still supports a public Render app when Render is authorized to read that repository. Connect only the repository needed for this app where GitHub offers that option. Do not paste account tokens into source files or this chat.

If using Git locally in the clean extracted folder:

```powershell
git init -b main
git add .
git status --short
git commit -m "Prepare SmartTrip demo for Render"
git remote add origin https://github.com/YOUR-ACCOUNT/smarttrip-demo.git
git push -u origin main
```

Use Git's normal sign-in flow. Replace the remote with the actual repository URL. Inspect the staged files before committing; no data or secrets should appear.

## Render

The easiest route is **New → Blueprint** and select the repository containing `render.yaml`. Review that the service is **Free**, then deploy. Alternatively choose **New → Web Service**, connect the repo, and enter:

| Setting | Value |
|---|---|
| Runtime | Python |
| Build command | `python -m py_compile server.py planner.py schema.py` |
| Start command | `python server.py` |
| Instance plan | Free |
| Health check | `/api/health` |
| `PYTHON_VERSION` | `3.12.11` |
| `HOST` | `0.0.0.0` |
| `SECURE_COOKIES` | `1` |
| `EPHEMERAL_STORAGE` | `1` |
| `SMARTTRIP_DB` | `data/smarttrip.sqlite3` |

Render supplies `PORT`; the server reads it. Render terminates HTTPS, so the secure cookie and origin check use the public HTTPS origin. Do not configure an HTTP origin, set `SECURE_COOKIES=0`, or override `PORT` unnecessarily. There are no packages to install; `requirements.txt` documents that explicitly.

After deployment, open the returned `https://...onrender.com` URL. Verify `/api/health` returns `status: ok`, create a sample trip, generate, revise, refresh, and download both exports. Use a separate browser profile/private window to verify session separation. Do not submit sensitive personal travel information while testing.

## Trips you can test

This remains a rule-based demo: it uses fictional places even when a real destination is entered. It is useful for testing setup, validation, preferences, revisions, and budgets; it does not research real attractions or current travel prices. Choose one of the five supported destination time zones and 1–14 dates. Test low budgets, unknown costs, relaxed/busy pace, party size, dietary/access notes, and stale-tab edits. General natural-language understanding remains limited.

## Serving limits

The current process uses Python's standard-library threaded HTTP server with request size limits and a 15-second socket timeout. This is a small testing deployment, not a hardened production service. Before expanding to production, replace the HTTP layer with a production server/framework, add durable storage, global abuse protection, and load/security verification. Do not run multiple instances against local SQLite.

## Deployment status

Configuration and local checks are prepared. No GitHub repository upload or Render deployment is claimed until returned repository/deployment URLs are recorded. Connecting GitHub and Render accounts is required to perform those actions.
