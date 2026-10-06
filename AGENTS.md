# Agent guide — gotify2apprise

Homelab notification bridge: listeners → YAML v2 routes → receivers, plus SQLite delivery queue and NiceGUI.

Python package `gotify2apprise/`. Keep new listener/receiver types behind the existing protocols; do not introduce a plugin marketplace.

## Layout

| Path | Role |
|---|---|
| `gotify2apprise/main.py` | Entry: env, v1 preflight, NiceGUI |
| `gotify2apprise/bridge.py` | Orchestrator: load config, start listeners, route, enqueue |
| `gotify2apprise/models/config.py` | Pydantic YAML v2 schema |
| `gotify2apprise/config/manager.py` | Load/validate/save, `AUTO_MIGRATE_V1` |
| `gotify2apprise/listeners/` | `gotify`, `smtp` |
| `gotify2apprise/receivers/` | `apprise` |
| `gotify2apprise/routing/` | Tag OR matching, priority filters, templates |
| `gotify2apprise/storage/` | SQLite + repos |
| `gotify2apprise/delivery/worker.py` | Retry worker |
| `gotify2apprise/web/` | NiceGUI pages |
| `gotify2apprise/legacy/migrate_v1.py` | v1 → v2 converter |
| `config.example.yaml` | Sample v2 config |
| `readme.md` / `readme.ru.md` | English / Russian docs |
| `program.py` | Shim → `main()` |

## Runtime flow

1. `Settings.from_env()`, refuse v1 YAML unless `AUTO_MIGRATE_V1=true`.
2. NiceGUI starts; `on_startup` opens SQLite, bootstraps the single user, loads YAML, starts enabled listeners + delivery worker.
3. Listener emits `NormalizedMessage` → persist → `RoutingEngine.route` → one `deliveries` row per (route, receiver).
4. Worker sends via receiver; failures use route/default `delivery` backoff; `dead` after `max_attempts` (`0` = unlimited; exponential unlimited requires explicit `max_delay_sec`).
5. UI can Save & reload YAML (restart changed listeners only) and Retry a delivery.

## Conventions

- Match existing module style: typed functions/classes, `logging`, no extra frameworks.
- YAML is source of truth; SQLite is history/auth/queue, not routing config.
- Gotify token in listener options is a **client** token. App tokens live in `app_tokens`.
- HTTP/WS vs HTTPS/WSS is per-listener `ssl` (default false). Do not silently switch.
- Route `from`/`to`: **OR** of ids and tags (union). Tag lists are also OR (any overlap).
- Integer in `priorities` = that exact priority (v1 bug must not return).

## Adding a listener or receiver

1. Pydantic options model + `type` literal on `ListenerConfig` / `ReceiverConfig`.
2. Class with `start`/`stop` or `send`.
3. Register in `listeners/factory.py` or `receivers/factory.py`.
4. Document YAML in `readme.md`, `readme.ru.md`, and `config.example.yaml`.
5. SMTP is internal-only; do not add open-relay behaviour.

## Do not

- Split into microservices or add Redis/Postgres for v2.
- Commit secrets, filled `.env`, or SQLite files.
- Break env contract: `CONF_FILE`, `DATA_DIR`, `GOTIFY_*`, `AUTO_MIGRATE_V1`, `ADMIN_*`.
- Auto-migrate v1 without the flag.

## Checks

```bash
pip install -r requirements-dev.txt
pytest
python -m gotify2apprise.main
```
