# Foundation F3 — ECR 429 immutable-digest registry mirror, 2026-11-24

The build of SHA df0fd86 failed in disposable CI when public.ecr.aws returned HTTP 429 Data limit exceeded. This was not a code pass. The registry endpoint of the 3 official base images was changed to docker.io/library, retaining the exact same **linux/amd64 immutable platform manifest digest**:

- Python official 3.13 slim bookworm: `sha256:f3dac913ab53b78c64f26d5518fcd7043d5a1a46522d6a493b598c3ed12f62a6`
- Node official 22 bookworm slim: `sha256:47725aca53d3295ec2d3be8f62726599b3033cc262edc2c7e429909b3ac599fc`

Public official tag references: https://hub.docker.com/_/python/tags?name=3.13-slim-bookworm and https://hub.docker.com/_/node/tags?name=22-bookworm-slim

The SHA/digest/architecture guard runs before all expensive integration jobs. If Docker Hub cannot resolve the pinned image digest, build fails closed; there is NO fallback to an unpinned latest tag. The second-opinion independent scan workflow is manual-only because every push is already scanned within the same tested-container job. Workflow concurrency cancels obsolete runs on the branch, reducing abuse of public mirrors.

No owner-approved registry release manifest or Mac/production approval is implied. The user-facing signed runtime, API, and Web image ID must still be independently verified by the CI at the new SHA.
