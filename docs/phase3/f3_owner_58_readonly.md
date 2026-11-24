# F3 owner conflict textual audit (read-only)

Inputs are the exact pinned four-owner 58-path manifest plus the local full
Git history. CI verifies 58 paths, 36 exact source selections, six Foundation
security choices, and all sixteen **retained pending owner review** files.

Each historical owner commit SHA and path is matched against its Git blob
object SHA. Candidate and owner nonempty lines are compared as *sets* only.
All raw text remains inside disposable CI and is never uploaded: the artifact
only has counts, SHA, owner labels and specific file paths.

This is not a three-way semantic merge, not independent UI/API/DB/Engine
behavior proof, not product release and not CENTRAL or owner acceptance.
It must not alter current source files or Git refs; any mismatch exits nonzero.
