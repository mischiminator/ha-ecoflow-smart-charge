# Diagnostics requirements and disclosure boundary

Normative acceptance requirements for the adapter and reconciliation task; this document is not a substitute for the executed diagnostics test. Diagnostics must work without commanding devices, initiating recovery or fetching a new tariff. A pending/corrupt journal is reported, never modified.

## Small explicit allowlist

Safe output may include integration/version, mode, stable reason/status code, source-count/validity flags, age categories, recovery-pending boolean, session phase, pending/confirmed target COUNTS, schema version and whether a full marker/learning probe exists. Prefer counts/flags over exact household amounts, absolute local timestamps or IDs. Only expose genuinely computed metrics; missing data is unknown, never synthetic success.

Do not serialize `entry.as_dict()`, raw entry data/options, complete runtime objects, exception reprs or full Store documents. Do not dump entity IDs/unique IDs, config-entry IDs, device IDs/serials, home/tariff selectors, credentials, tokens, HA/cloud URLs, IPs, location, real statistic IDs, calendar/day histories, reserve maps, session IDs, price arrays, PV learning samples or captured dashboard/config snapshots. A session phase is enough; full saved originals are not needed in public diagnostics.

If optional nested data is retained, recursively redact keys/values with HA diagnostics redaction helpers before returning it. An explicit allowlist is safer than an expanding denylist. Redaction must cover nested lists and exception strings; third-party attributes may contain secrets despite harmless-looking outer keys. Never make raw debug dumps a fallback on errors. Show opaque error codes instead.

## Required real HA tests

- Request entry diagnostics through the real HA diagnostics endpoint/handler in shadow, active, pending, blocked and unavailable-runtime states; zero device services.
- Inject synthetic canaries into entry data/options, nested lists, external attributes, source IDs/URLs, journal originals, tariff/home name and error messages. Assert every canary is absent from serialized JSON, not just one selected field.
- Assert only the documented allowlisted shape, machine codes, counts and validity flags remain. Test empty/malformed optional fields without turning errors into false `restored`.
- Repeat after imported/restarted pending sessions and failed unload. Keep fixtures synthetic, never copied household traces.

Before sharing even a redacted diagnostic export, the operator reviews it locally. Exported diagnostics and private test logs are not release assets and must not be committed. The adapter owns `diagnostics.py`; packaging does not silently fix it during parallel work. Final reconciliation must close any mismatch, including inherited exposure of a config-entry identifier.
