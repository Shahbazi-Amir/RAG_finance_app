# Foundation — API137 exact source transfer and CI cross-version rollback

Base f2b743a1588cac76fddafc36e3b489deb59d42ac (#113, descended from #84), API #137 20567ad525933f7168e8ea04b8599bd450c297bb, run 45529798552. Transfer seven exact source objects, not the other branch's workflows or historical runtime. Only two application files change. Preserve Wave4 historical pins, verify new owner blobs and predecessor explicitly. Prior rollback is now actual API source delta, immutable contracts/DB/Web/locks. Before switching, take a fresh encrypted-verified backup of disposable restored PG and check archive catalog. No approval, target deploy, Engine, SQL011 or external secrets. All results require this candidate's own CI; predecessor green is not current proof.

## Additional independent lab checks and provenance correction
- Preserve the original 58 path audit and Wave4 source derivation; explicitly bind API137 supersession. The old exact-hash test correctly failed on dc3f501; this correction changes no historical owner decision or canonical criterion.
- A new pre-version-switch backup is checked through an actual third fresh PG volume, network none, no host ports; row fingerprints and RLS catalog equality are required before switching. No production backup/retention claim.
- A separate temporary Keycloak realm/container exercises synthetic password hashing, lockout, native events and recovery. Main login realm and production policy untouched.
- Phase4 draft is an inert design schema (no runtime, migration, user records, financial fields). Only version/shape/owner reference fixtures are tested; CENTRAL and DB approval still required.
- Browser CI concurrency is keyed by SHA so a previous exact run completing its scan cannot be cancelled by the next candidate. No result is reused as proof of a newer SHA.
