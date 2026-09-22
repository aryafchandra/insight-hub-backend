# InsightHub

Portfolio rebuild of a CSV-to-dashboard app. Backend: Django REST Framework + PostgreSQL + django-rq. See `files/` for the full specs (build spec, backend spec, engineering tickets).

## Local setup

### 1. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. PostgreSQL (project-local instance on port 5433)

A dedicated Postgres data directory is used so this doesn't collide with any other Postgres instance already running on the default port 5432.

```bash
# one-time setup
LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 /opt/homebrew/opt/postgresql@16/bin/initdb -D .pgdata --auth=trust -U insighthub --locale=C

# start (macOS needs LANG/LC_ALL set to avoid a libpq fork-locale crash)
LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 /opt/homebrew/opt/postgresql@16/bin/pg_ctl -D .pgdata -l .pgdata/logfile -o "-p 5433 -k /tmp" start

# create the database (one-time)
/opt/homebrew/opt/postgresql@16/bin/createdb -h /tmp -p 5433 -U insighthub insighthub

# stop
/opt/homebrew/opt/postgresql@16/bin/pg_ctl -D .pgdata stop
```

### 3. Redis (for django-rq)

```bash
mkdir -p .redisdata
/opt/homebrew/opt/redis/bin/redis-server --daemonize yes --port 6379 --dir "$(pwd)/.redisdata" --logfile "$(pwd)/.redisdata/redis.log"

# stop
/opt/homebrew/opt/redis/bin/redis-cli shutdown
```

### 4. Migrate + run

```bash
python manage.py migrate
python manage.py runserver
```

### 5. Background worker (required for CSV parsing)

macOS needs `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` set for the worker process — without it, the worker's forked work-horse crashes the first time pandas/numpy touch Objective-C runtime state after `fork()`.

```bash
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES python manage.py rqworker default
```

## Tests

```bash
python -m pytest
```

## API (Milestone 1)

- `POST /auth/register/` — `{username, email, password}`
- `POST /auth/login/` — `{username, password}` → `{access, refresh}`
- `POST /auth/refresh/` — `{refresh}` → `{access}`
- `POST /datasets/` — multipart `{name, raw_file}`, auth required → `{id, status: pending}`
- `GET /datasets/` — list the requesting user's datasets
- `GET /datasets/:id/` — status + (once ready) schema/row_count, or failure_reason if failed; 404 if not owned
