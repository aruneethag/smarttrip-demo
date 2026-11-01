# Challenges

- **Package downloads failed.** Attempted jsonschema installation returned DNS/network failures. Resolved by keeping all runtime code in the standard library and validating the contract's actual schema keywords directly. This validator is intentionally limited to this contract and is not a complete JSON Schema implementation.
- **Windows lacks IANA tzdata.** ZoneInfo(Europe/Lisbon) failed. The demo validates a curated list of five valid IANA identifiers and uses destination-local dates and wall times; no conversion or forecast precision is claimed. Arbitrary zones remain unsupported.
- **Sandbox loopback restrictions.** The first preview server could not be reached. A local loopback server was launched through the execution permission mechanism on port 8001, enabling Chrome inspection. No public deployment occurred.
- **Database file lock.** First tests found leaked SQLite connection handles during temporary database cleanup. Explicit connection closure fixed it, and the suite passed afterward.
- **Cost-edit target selection.** Code review found that activity-only target lookup blocked editing nonactivity costs. Fixed and covered by a regression test.
- **No real research or providers.** User interviews, connected provider behavior, and production operations cannot be claimed from this demo. These are explicitly marked pending.
