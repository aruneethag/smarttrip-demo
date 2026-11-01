# Iterations

Date: 2026-11-01
Problem or feedback source: Product specification; empty starting workspace.
Before: Only chatbot_build.md existed.
Change made: Implemented local demo planner, API/storage, canonical schema validation, and responsive chat/itinerary UI.
Reason: Make the specified demo runnable without API keys or installation.
Evidence or screenshot: server.py, planner.py, schema.py, static/; developer Chrome checks recorded in test-results.md.
Checks run and actual results: Initial business/API run had 17 passing test bodies, but teardown failed with a Windows SQLite file lock.
Remaining issue: Fixed in the next iteration.

Date: 2026-11-01
Problem or feedback source: Actual test teardown failure and code review of edit controls.
Before: SQLite context managers committed transactions without explicitly closing connections; cost editing rejected meal IDs because it searched activities first.
Change made: Added a context manager that closes database connections in finally; allow cost editing of every item kind; added a meal-cost regression test. Corrected saved-trip select sizing observed in desktop preview.
Reason: Prevent locked database files and allow explicit unknown costs on meals and other included items.
Evidence or screenshot: server.connect, planner.revise, tests/test_smarttrip.py; Chrome displayed revision 2 after making day two cheaper.
Checks run and actual results: The connection fix produced a clean 17-test pass; the expanded suite is recorded separately after the cost regression test.
Remaining issue: Live integrations and observed user research remain outside this demo build.

Date: 2026-11-01
Problem or feedback source: Browser keyboard/mobile inspection and native-prompt automation timeout.
Before: Day title and cost edits used native browser prompts.
Change made: Added a labeled in-page edit dialog; added recovery confirmation for a reload between confirmation and generation.
Reason: Make edits easier to inspect, keyboard-operable, and recoverable.
Evidence or screenshot: screenshots/desktop.png and screenshots/mobile.png; blank meal price displayed “Costs incomplete” and one unknown cost.
Checks run and actual results: 19 automated tests passed; Python and final JavaScript syntax checks passed; browser cost-edit flow succeeded. See test-results.md.
Remaining issue: Print rendering, live integrations, exhaustive accessibility validation, and real-user research remain pending.
