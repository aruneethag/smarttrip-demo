# Design thinking — actual status

## Empathize

Research is pending. No interviews or usability sessions with real travelers have occurred. Assumptions from the brief: research can feel overwhelming; costs are hard to compare; some travelers need slower plans; freshness matters. “Sam” remains an unvalidated example persona, not research evidence.

Interview guide for 3–5 willing participants:

- Tell me how you planned your last leisure trip.
- Which step took the most time, and why?
- How did you estimate costs and verify hours?
- What changed during the trip?
- What would help you trust or correct a generated plan?

Collect anonymized task notes only with consent. Do not collect travel documents. Anonymized notes: none available.

## Define

Problem: travelers need a quick way to create a realistic plan fitting time, budget, and preferences because information is spread across sources. Priorities: confirm details, show honest cost uncertainty, preserve edits, make sources visible, and permit export/deletion. These needs are specification assumptions, not validated findings.

## Ideate

Considered chat-only, form-only, and chat beside editable itinerary. Selected the combined layout for visible corrections and targeted edits. Booking and maps are deferred. See decisions.md.

## Prototype

Prototype A: layout sketch implemented as the initial empty state.

```text
Desktop: [brand / demo] [intro / CSS postcard]
         [chat + setup form] [confirmation / budget / day cards / sources]
Mobile:  [intro] [Chat & details | Your itinerary]
```

Prototype B: working deterministic demo, SQLite sessions, validation, revision checks, exports, and responsive UI implemented on 2026-11-01. Browser inspected through Chrome. Prototype C (connected live providers) is not implemented.

## Test

Automated business and API tests and developer browser checks are recorded in test-results.md. Real-user tasks remain pending: create a trip, change an activity, locate assumptions, export, and explain unknown costs. Track task completion, pauses, misunderstandings, and feedback when these sessions actually occur.
