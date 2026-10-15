# License and source provenance

The existing repository LICENSE is MIT, Copyright (c) 2026 Mischa Fürst. It is retained without changing the named holder or discarding its notice. Newly authored packaging documentation/tests and the generic battery icon are covered by that repository license. This is not a license grant for independently maintained upstream projects.

## Owner confirmation — 2026-10-15

Mischa Fürst confirmed in the project conversation that the legacy planner and
legacy card were created by him with assistance from this AI assistant, using
his own code rather than source copied from an independently maintained project.
He explicitly requested that this confirmation be recorded here.

This records the owner's statement, not an independent legal determination.
The earlier request for third-party permission for these owner-created sources
is resolved on that basis; the absence of a separate LICENSE/NOTICE in their
source folders is not an outstanding third-party authorization blocker.
The existing MIT license and copyright notice remain unchanged. The code-only
planner automation extracts used as Jinja test fixtures are documented in
`../core/PROVENANCE.md` and covered by this owner-source confirmation.

This confirmation does not grant rights to unrelated third-party material and
does not approve publication, deployment, a card modification or hardware control.
All separate technical, privacy and release-approval gates remain in force.

## Materials and boundaries

| Material | Use here | Rights/provenance boundary |
|---|---|---|
| Inherited isolated scaffold | Existing integration/tests and MIT LICENSE retained | Preserve notices; final reviewer audits all committed code |
| Private live migration evidence | Requirements/behavior reference only; never distributed | Contains household data; neither raw snapshots nor IDs belong in this repo/history |
| Legacy planner source repo and code-only planner automation fixtures | Behavioral reference; two extracted Jinja fixtures documented in core provenance | Owner-created with AI assistance, confirmed by Mischa Fürst on 2026-10-15; prior third-party authorization concern resolved. Preserve existing notices |
| Legacy card source repo | Interface/compatibility inspection only | Owner-created with AI assistance, confirmed by Mischa Fürst on 2026-10-15; prior third-party authorization concern resolved. No card JS copied or patched here; separate implementation/testing approval still required |
| Home Assistant / HACS | External runtime and validation tooling | Not vendored into the distribution; licenses remain with their projects |
| `brand/icon.png` | Original 256×256 generic battery symbol generated locally for this repo | Replaces inherited 1×1 placeholder; no vendor logo or downloaded artwork |

The owner-source rights clarification above is complete for the identified planner and card sources. Before publication the final reviewer must still check the final diff and source ancestry for any additional third-party material and preserve any applicable notices. No absent license is treated as a general reuse grant. This table records engineering provenance and the owner's confirmation, not a legal determination of ownership or blanket release approval.

No private inventory, source repository, foreign license, account, production device or dashboard was changed. Do not add vendor branding or suggest endorsement. Test fixtures and documented examples must be artificial, with provenance explained rather than copied measurements.
