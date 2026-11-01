# Test results — 2026-11-01

Render preparation follow-up: all **22 tests passed** (2.062s), including host defaults, temporary-storage disclosure, allowlisted release contents, and HTTPS public-origin/Secure-cookie behavior behind a proxy. Python compilation and JavaScript syntax checks passed. See render-preparation.md and deploy-render.md. Actual Render deployment is not yet tested because account connections are pending.

Environment: Windows; Python 3.12.11; Node 18.12.1 for syntax checks; Chrome browser. Mode: deterministic demo only. No real-user studies or live provider tests occurred.

## Automated commands

| Command | Actual result | Status |
|---|---|---|
| `python -m unittest discover -s tests -v` (first run) | 17 test bodies passed; teardown failed because SQLite connections retained file handles | Failed, fixed |
| Same command after connection fix | 17 tests, clean pass | Pass |
| Same command after expanded regressions | 19 tests, 1.846s, OK | Pass |
| `python -m py_compile server.py planner.py schema.py` | Exit 0 | Pass |
| `node --check static/app.js` | Exit 0, including final dialog changes | Pass |

The suite uses an isolated temporary SQLite database and an actual threaded loopback HTTP server. It covers the contract and business rules, malformed fixtures, three-day dates, party-wide totals, invalid intake, currency minor units, preferences, unknown costs, targeted revisions, reconfirmation, idempotency, stale writes, ownership on all trip routes, exports, origin enforcement, mutation rate limits, session deletion, retention, and cascaded request-result deletion. Mocked or local tests do not prove live provider integration.

## Ten specification scenarios

| # | Actual checks and evidence | Result |
|---|---|---|
| 1 | Business test and Chrome sample flow: confirmation required, Apr 12–14 2027, two travelers, EUR 504.00 known estimate, schema/business checks and no overlaps | Pass (demo) |
| 2 | Springfield / “sometime next month” returns clarification without a selected destination or dates | Pass (rule-based intake) |
| 3 | Unit/API tests reject invalid date, reversed dates, zero travelers, negative budget, 15-day trip, unsupported currency/zone | Pass |
| 4 | Low budget plus unknown travel price is over budget; with a larger budget unknown prices yield uncertain. Browser meal-cost edit to blank displayed “Costs incomplete”, EUR 484.00, 1 unknown cost | Pass |
| 5 | Relaxed schedule contains breaks; step-free and vegetarian notes produce unverified suitability prompts | Pass (automated fixtures) |
| 6 | Tests replace day two while preserving days one/three, and reject stale expected revision. Chrome day-two cheaper edit changed EUR 504 to EUR 456 | Pass |
| 7 | No weather/places/AI adapters exist. Real timeout, 429 provider response, invalid AI JSON, repair and bounded retries cannot be exercised. Invalid local revisions preserve saved plan | Not implemented for live mode; local preservation passes |
| 8 | Rule-based safety responses to injection/visa request; adversarial interest treated as data; no provider secrets exist. External retrieved-place injection cannot be exercised without a provider | Partial: demo safety passes; external-provider test not run |
| 9 | API tests save/list/refresh/export; a second session cannot read/update/export/message/confirm/generate/revise/delete the first session’s trip. Deletion and expiry cascade. Chrome refresh restored saved plan | Pass |
| 10 | Chrome 390×844 override (375px content area): content width equaled viewport width; no horizontal overflow. Sample setup, review, confirmation, generation, tab switching, chat revision, and JSON export activated with keyboard. Download event returned a real JSON path. Duplicate generation tested through API returns identical stored result | Pass for checked keyboard actions and API duplication; full screen-reader/user testing pending |

## Browser observations

- Desktop chat/details and plan appeared side by side; demo state, costs, exclusions, and warnings were visible.
- Mobile sample flow completed using Enter activation. Chat “add a break on day 3” produced revision 3 and EUR 408 after the earlier day-two cheaper edit.
- Replaced native edit prompts with a labeled in-page dialog. Browser verified a blank meal price produces a null/unknown cost and incomplete budget status, rather than free.
- Saved screenshot evidence: [desktop](screenshots/desktop.png), [mobile](screenshots/mobile.png). Screenshots capture real demo states, not mockups.
- Viewport override reset after mobile checks.
- Browser console contained errors from the user’s installed Grammarly extension; no app-origin error was observed in the sampled console log. This is not a comprehensive JavaScript audit.
- A JavaScript-dialog automation timeout motivated the in-page dialog revision. The resulting cost edit succeeded.
- JSON export was observed through a browser download event. Markdown output was checked through the API; its link was also keyboard-activated.
- Print stylesheet implemented and reviewed in source; native print preview and physical/PDF output were **not** verified.
- Confirmation dialogs for deletion implemented; destructive behavior verified against isolated API test data. Browser deletion was not performed.

## Remaining verification

No claim of full production release acceptance: live provider scenarios, actual user research, exhaustive assistive-technology checks, native print rendering, arbitrary time-zone support, arrival/departure constraints, load/security testing, and production hosting remain pending. The requested no-key local demo is implemented and verified to the scope above.
