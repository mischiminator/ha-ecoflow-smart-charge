# Docker validation after operator enabled Docker

This supersedes the historical Docker-unavailable note in lane reports.
Docker is installed. Normal daemon socket access is denied; `sudo -n docker`
provides verified daemon access. No daemon/group/permission configuration was changed.

## Official hassfest container: PASS

Resolved image:

    ghcr.io/home-assistant/hassfest@sha256:4b1adfb1e0a37710af0390708eb8000230b80b2193ccffbeed0a901fa9765181

Reproduce from repository root with your approved Docker invocation:

    sudo -n docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges -v "$PWD:/github/workspace:ro" ghcr.io/home-assistant/hassfest@sha256:4b1adfb1e0a37710af0390708eb8000230b80b2193ccffbeed0a901fa9765181

Exit0,23 validators,1 integration,0 invalid, no warnings. No check skipped. The
integration mount was read-only and network disabled. Actual log:
evidence/integration-hassfest-container.log. Pinned Core source hassfest also passes.

## Official HACS container: EXECUTED, FAIL / acceptance OPEN

Resolved image:

    ghcr.io/hacs/action@sha256:dc92fdad2f6ffbe74bffb7269d781ea8e064f52d9bb486cdf3925d74e7ab6ebf

Official action entrypoint inspected from this image: python3 /hacs/action.py.
Inputs are integration category, explicit target repository, comments=false,
GITHUB_WORKSPACE=/github/workspace and read-only repository mount. No checks ignored.
It validates remote GitHub repository content, not simply the mounted local tree.
The initial no-token offline preflight failed honestly; then the existing GitHub
CLI credential was streamed to Docker's --env-file /dev/stdin, without writing a
secret file, putting the token in process arguments or printing it. Output was
redacted against that token before log persistence. No credential values are
release assets. Do not create a fake GitHub event/response or dummy token to pass.

Authenticated action result: Exit1, GitHubNotFoundException: Not Found at remote
repository lookup, before integration validation. Independent read-only gh api
repository lookup returned HTTP404. That proves unavailable to the current
credential, not that no private repository can possibly exist. No repository was
created, changed or published, no comment posted. This is NOT a HACS passing result.

Actual logs: evidence/integration-hacs-container.log (no-token preflight) and
evidence/integration-hacs-authenticated-container.log (authenticated lookup).
Machine status: evidence/final-hacs.json. Future authorized publication must run
HACS on the actual exact candidate commit and retain check URL/digest/log. Current
CI action-wrapper pins still refer transitively to mutable image tags, although
these local executions use the recorded immutable digests.
