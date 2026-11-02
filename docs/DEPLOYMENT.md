# Installing and running Phoenix

Three ways to run Phoenix, from quickest to production. All of them use the
same `.env` at the repository root; `scripts/setup.sh` creates it and fills in
secrets, and keeps your edits on later runs.

## 1. Development (your machine)

Needs Node.js 20+, Python 3.11+ (3.12 recommended), Docker with Compose v2.

```bash
scripts/setup.sh --seed   # install, .env, database in Docker, migrations, sample events
pnpm start                # API and web with hot reload (tmux session "phoenix")
```

- Web http://localhost:23000 · API docs http://localhost:28000/docs
- Sign in without a mail server: the sign-in link is shown in the browser
  (`AUTH_DEV_RETURN_LINK=true`, refused in production).
- Put your address in `PLATFORM_ADMIN_EMAILS` to approve organisations.
- `pnpm doctor` checks the toolchain, database, settings and data feeds.
- Already have PostgreSQL with PostGIS? Set `DATABASE_URL` in `.env` and run
  `scripts/setup.sh --no-docker`.

Stop with `pnpm stop`; `pnpm status` shows what is running.

## 2. Everything in Docker (local or a test server)

```bash
scripts/setup.sh          # once, for .env
pnpm start:docker         # or: pnpm docker:up
```

Builds and starts PostgreSQL (PostGIS + TimescaleDB), Redis, the API (which
applies migrations on start) and the web app. Ports are bound to the host as in
development; use mode 3 for anything public.

## 3. Production on one server (HTTPS)

Needs a Linux server with Docker and Compose v2, ports 80 and 443 open, and a
DNS record for your domain pointing at it.

```bash
git clone https://github.com/mepysto/Phoenix.git && cd Phoenix
scripts/setup.sh --prod phoenix.example.org ops@example.org
```

This writes `.env` from `.env.production.example` with fresh secrets
(database, Redis, API key, Web Push), builds the images and starts:

| Service                                        | Reachable from             |
| ---------------------------------------------- | -------------------------- |
| Caddy (HTTPS, certificates from Let's Encrypt) | the internet, ports 80/443 |
| Web app (Next.js)                              | Caddy only                 |
| API (FastAPI; `/api`, `/ws`, `/health`)        | Caddy only                 |
| PostgreSQL, Redis                              | the internal network only  |

Browser and API share one origin, so sessions are first-party HTTPS cookies
and no CORS is involved.

Then edit `.env` and run the same command again:

- `PLATFORM_ADMIN_EMAILS` — who approves and verifies organisations.
- `SMTP_*` — required: sign-in links are e-mailed. `pnpm doctor` fails in
  production without it.
- Optional keys: `ANTHROPIC_API_KEY` (map assistant), `AISSTREAM_API_KEY`
  (ships), `NEXT_PUBLIC_CESIUM_ION_TOKEN`.
- `CONFLICT_ZONE_POLICY=grid` is the production default; see
  `docs/RESPONSIBLE_USE.md` §3.
- Commercial deployments set `NEXT_PUBLIC_COMMERCIAL_DEPLOYMENT=1`
  (see `docs/DATA_SOURCES.md`).

`NEXT_PUBLIC_*` values are built into the web app: changing them needs a
rebuild, which re-running `setup.sh --prod` (or `pnpm docker:prod`) does.

### Updating

```bash
git pull
scripts/backup-db.sh
scripts/setup.sh --prod phoenix.example.org ops@example.org
```

Migrations run automatically when the API container starts.

### Backups

```bash
scripts/backup-db.sh                 # ./backups, keeps the newest 14
scripts/backup-db.sh /srv/backups 30 # elsewhere, keep 30
```

Each dump is verified with `pg_restore --list` before it is kept. Daily from
cron, and copy `backups/` off the server:

```
20 3 * * * cd /srv/phoenix && scripts/backup-db.sh >> backups/backup.log 2>&1
```

Restore (replaces all data; stop the API first):

```bash
docker stop phoenix-api
scripts/restore-db.sh backups/phoenix-20261102T032000Z.dump --yes
docker start phoenix-api
```

### Logs and health

```bash
docker compose -f infrastructure/docker/docker-compose.yml \
  -f infrastructure/docker/docker-compose.prod.yml --env-file .env logs -f api
curl https://phoenix.example.org/health
```
