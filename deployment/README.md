# VPS Deployment Contract

Production uses `/srv/brain/store` (durable), `/srv/brain/runtime`
(rebuildable), and `/srv/brain/cache` (disposable). The Compose service binds
only to `127.0.0.1:8085`; nginx owns the public MCP route, whose domain is
supplied out of band via `BRAIN_PUBLIC_MCP_URL` (readiness/smoke) and
`OPENSHIP_CUSTOM_DOMAIN` (adapter) and is intentionally not recorded in this
repository. `openship-redis` is neither mounted nor referenced by Brain OS.

`deploy-brain.sh` deliberately requires an installation-specific executable in
`OPENSHIP_DEPLOY_ADAPTER`. The adapter receives `deployment/openship.json` and
must deploy it through the existing Openship API/installation. This avoids
guessing a private Openship API while freezing the required contract values:
local target/build, Docker runtime, service mode, and no managed public endpoint.
The Store and token file must be owned by the configured container identity
(`BRAIN_UID`/`BRAIN_GID`, default `10001`) so gated writes and dynamic auth work
without making durable data broadly writable.

Run order on the VPS:

```sh
sudo BRAIN_ROOT=/srv/brain BRAIN_APP_PATH=/srv/brain/app \
  BRAIN_PUBLIC_MCP_URL='<out-of-band public MCP URL>' \
  OPENSHIP_DEPLOY_ADAPTER=/usr/local/bin/openship-brain-deploy \
  /srv/brain/app/deployment/deploy-brain.sh --preflight

# Only when migrating the legacy path, as a separate controlled action:
sudo BRAIN_ROOT=/srv/brain /srv/brain/app/deployment/deploy-brain.sh --migrate-store

sudo BRAIN_ROOT=/srv/brain BRAIN_SMOKE_TOKEN='<out-of-band token>' \
  BRAIN_PUBLIC_MCP_URL='<out-of-band public MCP URL>' \
  OPENSHIP_DEPLOY_ADAPTER=/usr/local/bin/openship-brain-deploy \
  /srv/brain/app/deployment/deploy-brain.sh --deploy
```

Each deployment tags the previously running local image as a timestamped
`brain-os:rollback-*` image and records that tag in
`/srv/brain/runtime/deployments.jsonl`. Roll the application container back
without changing Store data, tokens, nginx, or Openship Redis with:

```sh
sudo BRAIN_ROOT=/srv/brain BRAIN_ROLLBACK_IMAGE='brain-os:rollback-YYYYMMDDTHHMMSSZ' \
  BRAIN_SMOKE_TOKEN='<out-of-band token>' \
  BRAIN_PUBLIC_MCP_URL='<out-of-band public MCP URL>' \
  /srv/brain/app/deployment/deploy-brain.sh --rollback
```

Rollback is accepted only when live, ready, authenticated MCP, and Redis
continuity checks pass. A runtime-index failure is recovered by rebuilding only
`runtime/retrieval.sqlite`; it never rolls back Brain Store knowledge. Store
content restoration remains a separate operator action from the timestamped
critical backup or git history.
