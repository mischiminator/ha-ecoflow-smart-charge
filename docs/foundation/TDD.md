# Common vertical RED / GREEN protocol

All implementation lanes must load the test-driven-development skill. One
behavior at a time: failing test -> run -> smallest implementation -> run focused
test -> full owned suite -> refactor with green suite. Do not implement a batch
and retrofit tests. A collection typo is not a valid RED behavior failure.

Each lane owns docs/tdd/<lane>/<slice>.md (core, adapter, packaging). Format:

    criterion: Pxx / Sxx / Hxx / Dxx
    behavior: one sentence
    base_commit: actual Git HEAD before slice
    test_node: exact pytest node or unittest test
    RED_command: exact command, dependency version/context
    RED_exit: actual nonzero exit
    RED_observed: concise real assertion; raw log path if retained locally
    change: owned implementation files and reason
    GREEN_command: exact same test invocation
    GREEN_exit: actual zero exit
    GREEN_observed: actual count/output
    regression_command: full owned suite
    regression_result: count, errors, failures, skips and log
    refactor: none, or changes and rerun
    limitations: explicit, never replace output with invented results

Use sanitized fixtures and relative paths in publishable reports. Raw logs can
stay outside Git. Existing tests are baseline regression, not retroactive TDD.
Pure-core unit tests must run without HA installed (the package __init__ import
boundary is adapter-owned: coordinate lazy imports or an importlib-based pure
loader, not fake HA classes). Real HA tests use actual hass/MockConfigEntry and
real Recorder; mocks can isolate transport, not replace the system under test.

## Foundation slice F01 (executed)

criterion: D02, reproducible test entry point
behavior: runner works from outside repository using the invoking interpreter.
base_commit: 5206aab4261ad119a81f093dcf4a6b84093cf0d5
test_node: RunnerTests.test_runner_invokes_pytest_from_an_unrelated_directory
RED_command: python -m unittest discover -s tests/foundation -v
RED_exit: 1
RED_observed: AssertionError: reproducible test entry point is missing; 1 failure.
change: tools/run_tests.py; delegates to python -m pytest, root cwd, sockets off.
GREEN_command: same unittest command using pinned harness interpreter
GREEN_exit: 0
GREEN_observed: Ran 1 test; OK.
regression_command: python tools/run_tests.py
regression_result: 19 passed in 0.31s (includes existing 18 baseline tests).
refactor: none.
limitations: foundation/bootstrap evidence only, not product parity acceptance.
