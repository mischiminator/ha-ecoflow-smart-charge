# Native adapter safety and lifecycle

## Executable boundary

`reader.py` reads only selected HA states, the configured Tibber tariff response,
and eight distinct Recorder statistics. Recorder work uses Recorder's executor.
Wh is converted to kWh by the Recorder unit API after metadata validation. Joins
are UTC; local profile/day semantics use HA's configured timezone. The pure core
receives original individual reserves while a session is pending, not the
100-percent temporary target. Missing data remains invalid; there is no meter,
price/home, zero-history or charging-power substitution.

`runtime.py` is the sole device writer. Each entry serializes events, timer jobs,
entities, services, learning and imports through one asyncio lock. Native settings
never write physical reserve numbers directly. The only hardware transport is
selected `number.set_value`, with `blocking=True` and a 10-second call timeout.
Mode selects cannot activate hardware. Economic settings and master are bounded
native entities, not aliases for legacy helpers.

## Journal guarantees and limitations

The integration-owned HA Store envelope is schema version 1: session, learning,
and full_marker_day are distinct. Before a session, all three original individual
reserves are captured. Before each command/retry an awaited save records its
unique command ID, target and timestamp. In-memory commits occur only after
successful saves. Save exceptions or cancellation therefore cannot authorize the
following command. HA Store/filesystem completion is the durability boundary;
this is not a claim about disk-controller caches or arbitrary physical power loss.

Session fields include session_id, created_at, reserves_before, pending_targets,
phase, command_ids, intent_at, intent_targets, readback, solar_day and
restore_started_at. Additive evidence fields default empty for older version-1
records. Wrong versions, malformed fields and a missing previously initialized
journal block recovery instead of being treated as idle. The source/config entry
stores only a journal-initialized flag through supported manager APIs, never
through direct HA `.storage` access. The importer accepts a validated explicit
session mapping; runtime refuses commands if configured reserve targets differ.

Readback must independently observe each selected number, match within 0.001
percentage points, be less than 120 seconds old, and have a timestamp strictly
AFTER session, restoration and latest per-target intent boundaries. ACK alone,
unchanged pre-command state, stale matching state, unavailable targets and partial
success cannot clear the journal. Confirmed slots are not commanded again. A
per-target persisted target/timestamp limits identical command retries to once
per 30 seconds; the first changed safety-restoration target is not delayed by a
recent charge command. Physical device reporting may itself be optimistic;
commissioning must validate the underlying integration's state semantics.

Full SOC evidence is collected independently of economic-source success. Before
restoration when full is observed, the selected solar-day marker is saved. It
survives session deletion, restart and imports independently of the session.

## Shadow, cutover and recovery

Startup is always shadow, even with persisted active options. Shadow is absolute:
recalculate, timer, restore, unload and replay send zero hardware calls. A pending
session remains visible, blocks cutover and is not automatically recovered.

Cutover requires `confirmed:true` AND `commissioning_confirmed:true` attesting
separately authorized independent legacy/meter/device commissioning. The stored
comparison matches operator-supplied values to native output, not authenticated
legacy output; it is not independent parity proof. Missing/false attestation or
any changed expected value blocks activation. Cutover also requires a successfully
persisted recent comparison, valid current sources, master permission, no session, three
fresh original reserves and all selected legacy writers explicitly off. Unknown,
unavailable or absent writer entities fail closed. Ownership and charging gates
are rechecked before every hardware call, including after the save that yields
to HA. This protects known configured writers, not arbitrary external users,
cloud actions or undisclosed automations. No legacy automation is automatically
disabled and no operating mode is changed by this integration.

Explicit confirmed recovery temporarily authorizes a separate recovery mode,
never writes while shadow, and returns to shadow in `finally`. Repeating the same
service is necessary until every fresh readback confirms. Restoration requires
exclusive ownership, saved targets and a valid journal but NOT charging economics,
master, price-window or operating-mode permission. Fetch/source failures do not
become permission to charge; restoration still uses the same ownership executor.

## Lifecycle and migration

Minute safety checks, quarter-hour planning at second 5, source-state listeners,
hourly learning at minute 5, midnight learning and HA-start learning are tracked
in runtime cancellation callbacks. Setup itself remains passive while sources
become ready. Stop/unload cancels registrations before serialized restoration.
Even if a stop's save fails, `finally` revokes active authorization and returns
shadow with the journal retained. No successful unload is reported with pending
or blocked safety state. In HA 2026.10 a manager FAILED_UNLOAD is nonrecoverable;
explicit recovery service can resolve the persisted session, then HA restart is
required (do not claim a second manager unload works).

OptionsFlow changes reload through an entry listener; settings entities update
supported entry options without spawning duplicate runtimes. Reconfigure rejects
pending/blocked journals, including unloaded entries, and overlapping reserve
writers in other entries. Ordinary disable/unload removes timer and entity
subscriptions. Restart never reenters active automatically.

`import_state` provides preview by default, validates the versioned envelope,
requires every economic setting and preserves supplied learning/session/marker
values. Apply is shadow-only with no existing pending or blocked record; it saves
the journal before supported options updates. Preview and apply never command
hardware. Existing dashboards and source repositories remain unchanged.
See ENTITY-SERVICE-CONTRACT.md and ../migration/ACTIONS-IMPORT.md. Card support is
an explicit opt-in adaptation specification, not a shipped JavaScript patch.
Integration reconciliation connected native entity translation keys to complete
EN/DE inventories; a real HA registry test covers all six platforms. Stable unique
IDs are unchanged. Raw reason/status machine codes remain untranslated.

## Verification boundary

All tests use synthetic values. Real HA config-entry manager, state machine,
service registry, platforms, flows and populated SQLite Recorder are exercised;
transport is substituted, never connected to devices. Some executor failure
matrices use isolated transport/store doubles to inject cancellation and disk
errors. This is not a productive installation, hardware cycle, HACS validation,
verification of a particular household meter's history, or release approval.
Cross-lane reconciliation owns final full-suite/release acceptance.
