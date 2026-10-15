# Adapter vertical TDD evidence

The required test-driven-development skill was loaded. Each slice below was
executed failed-first, then implemented and retested before the next slice.
Raw failed-first output is retained in `evidence/` (absolute workspace/tool paths
normalized to `$WORKSPACE`, `$REPO`, `$HARNESS` and trailing whitespace removed;
no outcome text invented).
`green.log` and `green.xml` are the final scoped test execution, not a prediction.

| Slice | Actual RED evidence file | GREEN behavior |
|---|---|---|
| Absolute shadow restore | adapter-shadow-red.log | pending restore makes no hardware calls in shadow |
| Awaited session/phase journal | adapter-journal-red.log | malformed store blocked, failed save never commits memory |
| Authorized single executor | adapter-executor-red.log | durable capture/intents, explicit approval, ACK != readback, partial failures |
| Actual source acquisition | adapter-reader-red.log | selected published tariff parsing and eight-stream Recorder joins |
| Native flows/platforms/services | adapter-native-red.log | actual HA setup, entities and targeted service schema, no mode bypass |
| Import/restart recovery | adapter-import-red.log | versioned preview/apply, nondefault settings preserved, restart shadow |
| Full source-to-plan path | adapter-pipeline-red.log | actual HA states and Tibber service response feed pure planner |
| Crash/readback/full marker | adapter-crash-red.log | latest intent timestamp, independent full marker, missing initialized store blocked |
| Recorder unit validation | adapter-units-red.log | metadata required; no unknown-unit-as-kWh assumption |
| Completed PV learning | adapter-learning-red.log | incomplete day does not finalize/overwrite prior probe |
| Malformed journal fields | adapter-corruption-red.log | five observed failures corrected; invalid mapping/readback stays blocked |
| Reconfigure safety | adapter-reconfigure-red.log | overlapping reserves and blocked/pending journal rejected |
| Stop on persistence failure | adapter-stop-red.log | both observed failures corrected; close/shadow revoke authorization in finally |
| Bounded identical retries | adapter-ratelimit-red.log | persisted target-aware 30-second retry interval |
| Config-entry-only schema | adapter-schema-red.log | CONFIG_SCHEMA declared using supported HA validation helper |
| Forecast Wh equivalence | adapter-forecast-unit-red.log | 6000Wh probe equals 6kWh, limits applied in source unit |

Additional regression evidence (tests passed immediately because testing already
implemented behavior, NOT claimed as failed-first implementation): supported
manager options reload/disable; native full service→reader→core→journal→writer
chain with shadow comparison/cutover/conflict/restore; PV-only real SQLite query.
The native end-to-end test additionally exposed equal-timestamp pre-command
readback and a charge-versus-restore retry-target ambiguity; both were fixed and
re-executed in the real harness before final GREEN.

Two initial retry failures were TEST issues and are not represented as product
fixes: sampling depended on actual HA local hour (before 05:00 in the harness
zone), now frozen explicitly; Recorder fixture's async_block_till_done alone did
not await queued-import commit reliably, now uses official
async_wait_recording_done. Tests continue to query actual SQLite, not mocked
Recorder output. Plain --disable-socket without --allow-unix-socket blocks the
asyncio self-pipe and is not a valid product RED.

## Reproduction

With the pinned compatible HA environment, from repository root:

    python -m pytest tests/ha tests/test_runtime.py tests/test_config_flow.py tests/test_safety_regressions.py tests/test_ha_integration.py -q --disable-socket --allow-unix-socket --junitxml=adapter-tests.xml
    uvx --from ruff==0.17.0 ruff check custom_components/ecoflow_smart_charge --exclude planner tests/ha tests/test_runtime.py tests/test_config_flow.py tests/test_safety_regressions.py tests/test_ha_integration.py
    uvx --from ruff==0.17.0 ruff format --check custom_components/ecoflow_smart_charge --exclude planner tests/ha tests/test_runtime.py tests/test_config_flow.py tests/test_safety_regressions.py tests/test_ha_integration.py

Final scoped result: 64 passed, zero failures/errors/skips. HA 2026.10.1,
pytest-homeassistant-custom-component 0.13.372, Python 3.14.7. IP sockets disabled;
local Unix sockets permitted for asyncio. Hardware transport is substituted.

Whole-tree check after scoped GREEN is recorded separately; frozen foundation's
standalone-file import loader still cannot load core's legitimate relative
imports. Reconciliation owns that test, global lint, release validation and
privacy/history gates. This lane does not falsely mark the whole product green.
