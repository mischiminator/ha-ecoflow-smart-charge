# Foundation status

Foundation prepares implementation, it does not certify the product controller.
The existing local scaffold was reused; no source repos or live HA were changed.

Read SOURCES, OWNERSHIP, INTERFACE, PARITY, DEVELOPMENT and TDD in this directory
before implementation. The private handoff resolves mandatory evidence labels.
35 parity rows cover core planning, session safety, HA and release boundaries.
Only the runner bootstrap behavior has new failed-first implementation evidence.
Existing 18 regression tests plus the initial new runner test passed (19 total).
Final verification log/count is recorded in the private handoff and task result.

Known inherited gaps: partial rather than exact projection, no real tariff/
Recorder ingestion, no complete learning/import, no validated active cutover,
shadow restoration bypass and no durable standalone full marker. These are the
assigned downstream implementations, not blockers to this foundation contract.
No claim of installed HACS integration, completed product parity or hardware
exercise is made. Current-tree privacy cleanup does NOT sanitize old commits;
packaging/reconcile must not publish inherited Git history unchanged.
