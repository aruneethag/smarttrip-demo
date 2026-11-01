# Integrations

Mode: **demo only**, selected by the user on 2026-11-01. No API keys required; no external requests from the server or frontend. No data is sent to an external AI service.

| Component | Implementation | Data status / freshness | Live test |
|---|---|---|---|
| Planning | DemoProvider, deterministic fixtures | sample, fixture version 1 | Not applicable |
| Places | Explicitly fictional named places | sample; never real venue evidence | Not implemented |
| Weather | No provider | unavailable; verify before travel | Not implemented |
| Routes | Explicit rough transport buffers | no route evidence | Not implemented |
| Currency | Seven currencies; integer minor units (JPY 0, others 2) | no exchange rates or conversions | Not implemented |
| AI | Rule-based intake/revisions | no model/provider | Not implemented |
| Persistence | Local SQLite | owned anonymous session | Automated API tests |

Source timestamps describe fixture creation, not live retrieval. No real provider URLs or attribution are invented. Demo exports include source IDs, sample verification, assumptions, warnings, and exclusions. Failure never switches a live plan into fictional places, because no live mode exists in this build.

Future connected work must check official provider documentation, pricing, licensing, attribution, freshness, and permitted caching before implementation. It must introduce structured output validation, at most one repair, timeouts, bounded transient retries, disclosure, and nonfictional partial fallback. These behaviors are not implemented or tested here.
