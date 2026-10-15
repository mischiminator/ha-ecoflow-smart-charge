# Release checklist (all gates required, none imply publication approval)

- [ ] Reconcile all 35 rows in foundation/PARITY.md with final code, actual test nodes and executed evidence.
- [ ] Review product ConfigFlow/OptionsFlow/entities/services/translations together; no invented or stale fields. Verify locale keys and entry-targeted service schemas against adapter contract.
- [ ] Product tests pass with exact hashed HA/plugin lock and compatible Python; crash/readback, absolute-shadow, exclusive-recovery and per-write conflict cases covered in real HA where applicable.
- [ ] Recorder populated-history/unit/DST and required-meter transition verified; no alternate/mixed histories or invented prices.
- [ ] Real settings/learning/session/marker preview-import path tested; no defaults replacing imported values, no commands from import, no direct `.storage` changes.
- [ ] Supported native card update implemented/tested separately or explicitly use standard HA cards and keep old dashboard unchanged. A spec alone is not an implemented adapter.
- [ ] Diagnostics serialized output passes synthetic-canary privacy tests; operator reviews example output.
- [ ] Full-tree Ruff check and format check pass after parallel lanes finish; do not exclude safety code to manufacture a pass.
- [ ] Official hassfest passes on final tree; resolve warnings, including setup/config-schema declaration.
- [ ] Full HACS Action runs against authorized public candidate and succeeds; local shape tests are NOT this validation. No ignored checks to conceal missing publication/catalog/branding requirements.
- [x] Identified owner-source rights clarification recorded in PROVENANCE.md: Mischa Fürst confirmed on 2026-10-15 that the legacy planner/card were owner-created with AI assistance; generic icon has documented original provenance.
- [ ] Final release diff/source-ancestry review confirms no additional third-party material with unresolved rights or missing notices. Owner-source confirmation is not blanket publication approval.
- [ ] Scan final tracked tree, release archive AND every commit intended for publication for real source IDs, Home URLs, household traces, tokens, paths, backups, snapshots and diagnostics. Secret-pattern scans alone cannot find household IDs: compare privately with inventory too.
- [x] Local inherited README history sanitized on 2026-10-15; all 14 commits retained, only two historical README snapshots changed, original affected blobs removed, all local objects scanned and open worktree/index preserved. See HISTORY-PRIVACY.md. Private original history/backups MUST NOT be pushed.
- [x] GitHub history cleanup closed at operator request: authorized main rewrite and fresh-clone audit completed; obsolete Actions run/cache removed. Operator reports contacting GitHub Support and explicitly waives further server-side purge verification. Cache/object deletion is NOT independently confirmed. Do not merge pre-rewrite history. See HISTORY-PRIVACY.md.
- [ ] Manifest and project version consistent. Future SemVer release/tag/name match; change log includes minimum HA version, migration, breaking changes and rollback. Release from an accepted immutable commit, not moving default branch alone.
- [ ] Confirm HACS offers the actual GitHub Release (not merely a local tag), installed version and loaded HA entry after a future separately authorized installation. No success claim based on guessed HACS REST endpoints or inaccessible filesystem.
- [ ] Backup and rollback readback rehearsed safely without forcing hardware; explicit supervised cutover approval obtained. Legacy and new writers never overlap.

This task does not publish, tag, push, create accounts, install HACS content, disable automations or run hardware tests. Open gates remain visible for the pre-created integration/review tasks. Green packaging checks are not a production acceptance.
