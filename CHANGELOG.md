# Changelog

## [1.2.21] — 2026-06-23

### Added
- `sandbox.expose_info()` returns the full preview URL contract: `url`, `url_class`, `stable_for_embedding`, and `recommended_next_action`.

### Fixed
- Preview URL fallbacks use `miosa.ai`.

## [1.2.19] — 2026-06-23

### Fixed
- Normalize legacy duplicated sandbox preview hostnames returned by
  `sandbox.expose()` / `sandbox.preview.expose()` from
  `*.sandbox.sandbox.preview.*` to `*.sandbox.preview.*`.

## [1.2.17] — 2026-06-22

### Added
- Computer external viewer-password helpers:
  - `client.computers.viewer_password(computer_id)`
  - `client.computers.rotate_viewer_password(computer_id)`
  - `computer.viewer_password()`
  - `computer.rotate_viewer_password()`
- `ComputerSize.XS`.

### Changed
- `computers.create(size="xlarge")` normalizes the legacy alias to canonical `xl`.

## [1.1.0] — 2026-05-26

### Added — Phase 1-4 contract methods

**Tenant**
- `client.tenant.preview_domain.{get,set,verify,delete}`
- `client.tenant.branding.{get,set,delete}`

**Sandboxes**
- `sandbox.update(name, slug, tags, metadata, always_on, timeout_sec)` — PATCH
- `sandbox.preview_token(expires_in, scope)` — mint preview access token
- `sandbox.fork(snapshot_id, name, external_user_id)` — extended with `snapshot_id` and `external_user_id`
- `client.sandboxes.create()` — already had `slug`, `external_user_id`, `external_project_id`

**Files**
- `sandbox.files.tree(path, depth)` — recursive directory tree
- `sandbox.files.write_many([{path, content}])` — batch write via `/files/write-many`
- `sandbox.files.watch()` — alias for `watch_dir()` per contracts

**Env vars**
- `sandbox.env.get()` / `sandbox.env.list()` — list vars
- `sandbox.env.set([{key, value, encrypted?}])` — bulk set via PUT
- `sandbox.env.delete(key)` — remove one var

**Processes**
- `sandbox.processes.start(command, env, name)`
- `sandbox.processes.list()`
- `sandbox.processes.get(pid)`
- `sandbox.processes.stop(pid)`
- `sandbox.processes.logs(pid, tail)`
- `sandbox.processes.stream(pid)` — SSE iterator

**Share URLs**
- `sandbox.share.create(expires_in, scope)`
- `sandbox.share.list()`
- `sandbox.share.revoke(share_id)`

**Templates**
- `client.templates.list()` — alias for `client.sandbox_templates`

**Usage**
- `client.usage.get(external_user_id, group_by, period)` — rollup per contracts

**Quotas** (new resource)
- `client.quotas.get(external_user_id)`
- `client.quotas.set(external_user_id, max_sandboxes, max_concurrent, max_storage_gb, max_credit_cents)`
- `client.quotas.delete(external_user_id)`

**Audit log**
- `client.audit_log.list(after, limit, type, actor_id, resource_type, resource_id)` — explicit params

**Tenant events** (new resource)
- `client.events.stream(types)` — SSE iterator for tenant-level events

**Webhooks**
- `client.webhooks.verify_signature(body, header, secret)` — HMAC-SHA256, rejects stale timestamps

**Client aliases**
- `Client` = `Miosa`, `AsyncClient` = `AsyncMiosa`

All methods have async parity via `AsyncClient`.

## [1.0.0] — 2026-05-14

Initial stable release.
