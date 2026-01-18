# Postgres + pgAdmin Setup Guide

Spin up a ready-to-use Postgres database and pgAdmin UI with one command.
All data stays inside this repo. No global installs required.

> ⚠️ Please don't change the names or passwords because the DATABSE_URL expects them and changing them will cause connection issues.

## 1. Requirements

Docker Desktop installed and running
-  install on Mac: https://docs.docker.com/desktop/setup/install/mac-install/
-  install on Windows: https://docs.docker.com/desktop/setup/install/windows-install/


## 2. Files / Folders That Matter
For this setup, following files and folders are relevant.
```
docker-compose.yml ← what we run to start Postgres + pgAdmin
.env              ← store your passwords + ports here
pgdata/           ← DB + pgAdmin data stored here
src/config/pgadmin/servers.json  ← allows in pgAdmin to see the DB automatically on left panel
```

Everything runs relative to where `docker-compose.yml` lives.


## 3. First-Time Setup

Make sure you `cd\backend` and then run:

```bash
docker compose up -d
```

### Heads up:

* First pull will take a while (images are large). Future runs are almost instant.
* pgAdmin takes ~30–60+ seconds to boot.
  If you see connection errors at first, just wait and try again.

## 4. Access pgAdmin

Open your browser:
>its port 5050 because we defined it in .env

```
http://localhost:5050
```
> You can also get this from docker desktop → containers → pgadmin → ports

Admin Dashboard Credentials are in `.env`:

* Email: `admin@memoria.com`
* Password: `deeznuts`

You’ll see **Memoria Local DB** automatically added in the left sidebar (because of servers.json).

**Click it** in the left pane → pgAdmin will ask for the DB password (`longterm`).

> Hit “save password” if you don’t want to type it again.

## 5. Data Persistence

Your data (tables, rows etc) lives here:

```
pgdata/db       ← Postgres tables & data
pgdata/pgadmin  ← Saved pgAdmin state
```

Delete those folders to reset everything to factory default.

## 6. Stopping / Resetting

Stop containers (data will persist):

```bash
docker compose down
```
---

