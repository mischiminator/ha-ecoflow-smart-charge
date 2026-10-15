# Validation commands and boundaries

## Reproducible product tests and Ruff

From repository root, with Python 3.14.7 available:

    uv venv --python 3.14.7 .venv
    uv pip sync --python .venv/bin/python --require-hashes requirements-test.lock
    uv pip install --python .venv/bin/python -r requirements-lint.txt
    uv pip check --python .venv/bin/python
    .venv/bin/python tools/run_tests.py --junitxml=pytest-results.xml
    .venv/bin/python tools/run_tests.py tests/packaging -q
    .venv/bin/python -m ruff check .
    .venv/bin/python -m ruff format --check .
    git diff --check

Do not run a broad unpinned `pip install homeassistant` or upgrade the shared supplied test environment. Lock: HA2026.10.1, pytest-homeassistant-custom-component0.13.372, pytest9.0.3, 152 exact hashed distribution pins. Lint tool is separately pinned Ruff0.17.0. The runner rejects IP sockets, permitting local Unix sockets required by the HA harness; no live device/network authority is needed.

During parallel development, test/lint output may show unfinished files belonging to another lane. Record it; do not edit another lane's or frozen foundation files just to make this lane's check green. Final reconciliation must run the ENTIRE tree, not only packaging tests. Packaging JSON/YAML/locale tests are deliberately offline and do not call themselves official HACS validation.

## Official hassfest: Docker route

On a machine with Docker, from repo root, the upstream action currently runs:

    docker run --rm -v "$PWD:/github/workspace" ghcr.io/home-assistant/hassfest

This image is mutable. Record resolved digest and logs in the eventual release evidence. Do not claim a container test happened if Docker is missing. The workflow pins the wrapper action, not its transitive image.

## Official hassfest: executed source route

A valid non-Docker alternative was executed for this lane: official Home Assistant Core tag2026.10.1, commit `abe1fdd7cd6b4de1715c87b6fd87d92699514ef9`, its complete custom-integration plugin run (none skipped), using the supplied exact HA environment read-only. The extra runner-only imports were installed in a separate validation venv, not the product lock.

Reproduce with absolute variables for YOUR isolated work directory; these commands intentionally do not include private machine paths:

    git clone --depth 1 --branch 2026.10.1 --filter=blob:none --sparse https://github.com/home-assistant/core.git "$WORK/core"
    git -C "$WORK/core" sparse-checkout set script/hassfest script/translations
    uv venv --python "$TEST_PYTHON" "$WORK/validation-venv"
    uv pip install --python "$WORK/validation-venv/bin/python" ruff==0.17.0 infrared-protocols==10.1.0 probatio==0.13.0 tqdm==4.70.1
    cd "$WORK/core"
    PATH="$WORK/validation-venv/bin:$PATH" PYTHONPATH="$TEST_SITE_PACKAGES" "$WORK/validation-venv/bin/python" -m script.hassfest --integration-path "$REPO/custom_components/ecoflow_smart_charge"

Set `WORK` to an isolated scratch directory, `REPO` to the absolute product checkout, `TEST_PYTHON` to the existing locked test interpreter, and `TEST_SITE_PACKAGES` to that interpreter's site-packages directory (discover with `TEST_PYTHON -c 'import site; print(site.getsitepackages()[0])'`, substituting its actual executable). The extra PYTHONPATH makes the verified HA packages available without modifying them. Pin/check the Core commit above. This source run verifies the declared tested Core version, not every future mutable hassfest image.

Executed result at packaging time: Exit0, 1 integration, 0 invalid; warning that adapter `async_setup` lacks CONFIG_SCHEMA. Adapter/reconciliation owns that warning. Re-run after final entity/service keys are settled.

## Official HACS Action

Workflow uses `hacs/action@1ebf01c408f29afcb6406bd431bc98fd8cbb15aa`, category `integration`, explicit repository, comments disabled and read-only workflow permissions. That official wrapper itself uses the mutable image `ghcr.io/hacs/action:main`. Its `action.yml` and README were inspected from the real upstream checkout; a pinned wrapper does NOT pin the transitive image.

The full HACS Action was NOT executed here: Docker is absent, and this local-only task cannot publish/create the public GitHub repository that network repository/metadata checks require. Do not fabricate a GitHub response, ignore all remote checks or claim offline structure tests equal HACS acceptance. Future authorized publication must run the workflow in the actual repository and retain the check URL, commit, image digest and logs. The official `action.yml` defines inputs; do not guess an undocumented CLI invocation.

Official docs checked: HACS publish/integration requires one integration below custom_components, all runtime files inside it, manifest domain/documentation/issue_tracker/codeowners/name/version and root brand/icon.png. Releases are optional in HACS, but this project requires a tested named release for deployment. Custom-repository installation is distinct from default-catalog inclusion.

## CI supply chain

Direct action refs were resolved with `git ls-remote` and pinned to immutable commits on2026-10-15:

| Action | Commit |
|---|---|
| actions/checkout | f548e57e544e1ff5a4c46bf1e1b8685f8e4a348a |
| actions/setup-python | ff73b2463e2f3baa703f830da214b8dfeeaeccf8 |
| hacs/action | 1ebf01c408f29afcb6406bd431bc98fd8cbb15aa |
| home-assistant/actions/hassfest | 50baf3a307f87100cf550d4ae127746595030d5d |

CI validates on PR/push/manual/schedule; no publish/deploy job, no long-lived token, no production secret. Wrapper transitive images remain an explicit reproducibility limitation. Never use pull_request_target to run untrusted PR code with credentials.

## Primary references

- https://www.hacs.xyz/docs/publish/integration/
- https://www.hacs.xyz/docs/publish/start/
- https://www.hacs.xyz/docs/publish/action/
- https://github.com/hacs/action/blob/1ebf01c408f29afcb6406bd431bc98fd8cbb15aa/action.yml
- https://github.com/home-assistant/actions/blob/50baf3a307f87100cf550d4ae127746595030d5d/hassfest/action.yml
- https://github.com/home-assistant/core/tree/abe1fdd7cd6b4de1715c87b6fd87d92699514ef9/script/hassfest
- https://developers.home-assistant.io/docs/creating_integration_manifest/
- https://developers.home-assistant.io/docs/core/integration/diagnostics/

Do not interpret manifest version0.1.0 as a created tag, GitHub Release, HACS installation or accepted controller.
