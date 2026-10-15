# License and source provenance

The existing repository LICENSE is MIT, Copyright (c) 2026 Mischa Fürst. It is retained without changing the named holder or discarding its notice. Newly authored packaging documentation/tests and the generic battery icon are covered by that repository license. This is not a license grant for independently maintained upstream projects.

## Materials and boundaries

| Material | Use here | Rights/provenance boundary |
|---|---|---|
| Inherited isolated scaffold | Existing integration/tests and MIT LICENSE retained | Preserve notices; final reviewer audits all committed code |
| Private live migration evidence | Requirements/behavior reference only; never distributed | Contains household data; neither raw snapshots nor IDs belong in this repo/history |
| Legacy planner source repo | Behavioral reference | No LICENSE/NOTICE file was found at its root during packaging inspection. Do not infer permission to copy substantial source or relicense it |
| Legacy card source repo | Interface/compatibility inspection only | No LICENSE/NOTICE file found at root; no card JS copied or patched here. Separate opt-in patch must verify rights and preserve any applicable notices |
| Home Assistant / HACS | External runtime and validation tooling | Not vendored into the distribution; licenses remain with their projects |
| `brand/icon.png` | Original 256×256 generic battery symbol generated locally for this repo | Replaces inherited 1×1 placeholder; no vendor logo or downloaded artwork |

There is no claim that an absent license grants reuse rights. Before publication the owner/reviewer must check the final diff and source ancestry, establish authorization for any actual reused source, and preserve required notices or replace unlicensed copied material with original implementation. Do not publish while this gate is unresolved. This table records an engineering provenance check, not a legal determination of ownership.

No private inventory, source repository, foreign license, account, production device or dashboard was changed. Do not add vendor branding or suggest endorsement. Test fixtures and documented examples must be artificial, with provenance explained rather than copied measurements.
