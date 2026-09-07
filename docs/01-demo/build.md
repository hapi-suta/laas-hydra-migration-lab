# Start Hydra on MySQL

**Environment:** Laptop, your user. **Prerequisite:** Python dependencies and a running Docker engine. **Checkpoint:** sign in and refresh a token on source Hydra.

## 1. Initialize private lab configuration

On **Laptop**, as **your user**, in the project root:

```bash
python3 scripts/lab.py init
```

This creates random demo passwords and shared Hydra secrets in `.env`, plus the active-backend configuration in `runtime/`. Re-running preserves existing credentials.

The script reports that private configuration was created; it never prints the passwords.

## 2. Start the source application

On **Laptop**, as **your user**:

```bash
python3 scripts/lab.py up
```

The helper builds the portal, starts the databases, waits for database health checks, runs both Hydra schema migrations, and starts source Hydra and the gateway. Initial image downloads can take several minutes. The final readiness message identifies `http://localhost:8080`.

On **Laptop**, as **your user**:

```bash
python3 scripts/lab.py status
```

Verify MySQL, PostgreSQL, source, portal, and gateway are running. The migration containers should have exited with code 0. Target Hydra should not yet be running.

## 3. Exercise the browser flow

Open `http://localhost:8080` in your browser. Select **Sign in**, choose **alice**, and allow consent. The protected page should display `active: true`, Alice's subject, and `lab-portal` as the client. Select **Refresh existing token** and confirm the protected page still works.

Keep this browser session open for the migration rehearsal. Do not print or publish its tokens.

## 4. Save the baseline

On **Laptop**, as **your user**:

```bash
.venv/bin/python scripts/workload.py --seconds 30 --workers 1 --rps 1
```

`--seconds` bounds the run, `--workers` controls concurrency, and `--rps` sets token cycles per second. The script issues real tokens, revokes a subset, and creates/updates/deletes transient clients. It writes counts to `evidence/workload.json`. Require issued tokens and zero errors.

If startup fails, use `python3 scripts/lab.py logs` and distinguish database readiness from schema migration failure and portal registration failure. Do not repeatedly delete database volumes as a troubleshooting shortcut.

**Evidence:** source backend, successful login and refresh, container status, and workload report.
