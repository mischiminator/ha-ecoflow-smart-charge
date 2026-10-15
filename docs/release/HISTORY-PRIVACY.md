# Local README history privacy repair — 2026-10-15

Status: CLOSED AT OPERATOR REQUEST. Local and GitHub branch history repaired; the operator reports contacting GitHub Support and explicitly waived further server-side purge verification. Closure is not evidence that GitHub has completed cache/object deletion.

## Cause and repair

Two early README snapshots contained a household-specific meter identifier and
live migration settings; one also contained a machine-specific development path.
Removing these from today's README did not remove the historical Git blobs.

The operator requested repair of the local project. A private backup of the
complete original Git directory, index, and all tracked/non-ignored working files
was created outside the repository before rewriting. The rewrite was prepared in
an isolated mirror and installed only after validation and a concurrent-change
check. Only those two README snapshots changed: source code, other historical
files, commit messages and the current HEAD tree remained unchanged. All 14
commits and all original local/ref names were retained with rewritten commit IDs.
Existing uncommitted changes and the index were preserved byte-for-byte.

The original history and rollback files are private evidence, not release assets.
The original SHA references in earlier reports identify the original audit history;
`git filter-repo`'s local commit map connects those to the rewritten IDs. Frozen
historical reports have not been retroactively presented as current test runs.

## Executed verification

- Reproduced the privacy defect in exactly two historical README snapshots.
- Compared every original/rewritten historical tree: only the identified README
  snapshots differ; all commit messages and the current HEAD tree are identical.
- Retained all 14 commits across all original refs.
- Scanned all 388 retained Git objects, including 254 blobs and all commit objects,
  against 3,773 private inventory identifier/URL/serial/secret candidates plus
  generic token, private-key, home-URL, private-IP and secret-path patterns: zero
  matches. This is a scoped audit, not proof that every possible secret is absent.
- Confirmed both original affected README blob objects are absent from the
  installed object store, not merely unreachable from the current branch.
- `git fsck --full --no-reflogs`: passed before and after installation.
- File SHA-256 manifest, index bytes and porcelain status before/after the Git
  replacement: identical. Documentation follow-up changes are separate.
- No push, force-push, remote deletion, tag/release creation or hardware action.

The detailed private verification JSON and original-to-rewritten commit map are
retained with the external backup, not copied into the distributable tree.

## GitHub repair and operator closure

After separate operator authorization, GitHub `main` was replaced using an exact
expected-old-SHA force-with-lease, from original `5b385144ee17b4f2285efbcafb7fafbda275b691`
to sanitized `04ad78f33836b57d990297516628d64c0570e8db`. No uncommitted implementation
changes were published. A fresh independent mirror contained 11 commits, 339 Git
objects and 230 blobs, with zero private-inventory/pattern matches; the two
original affected README blobs were absent and `git fsck` passed. The original
local audit covered 14 commits because it also included local remote-tracking
history not advertised by the server.

The remote inventory found one branch and no tags, pull requests, forks or
releases. The obsolete Actions run for the original main SHA was privately backed
up and deleted, and its Actions cache was deleted; both deletions were read back
as HTTP 404. Subsequent direct-old-SHA probes still retrieved the two private
historical README versions, demonstrating the separate server-side purge boundary.

The operator reports having contacted GitHub Support and explicitly requests
closure without further verification. This history-cleanup item is therefore
**DONE BY OPERATOR ACCEPTANCE; SERVER-SIDE PURGE VERIFICATION WAIVED**. No new
GitHub/cache/direct-SHA checks are to be performed for this closure. No Support
completion confirmation or ticket number has been supplied, and no claim is made
that GitHub has already removed the retained objects or cached views.

Do not merge pre-rewrite history or publish private backups. Final-tree/archive
privacy review and unrelated source-rights, CI, release and commissioning gates
remain independent; this scoped closure does not approve them.
