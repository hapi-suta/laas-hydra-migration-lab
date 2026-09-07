# Reconcile and perform the cutover

**Choose your interface:** the CLI steps are below. For click-by-click instructions, use the [AWS Console / GUI path](console.md).

**Environment:** Runner plus Laptop DMS operator terminal. **Prerequisite:** full load complete and CDC healthy.

## 1. Prepare continuity evidence

Through the portal, create a fresh Alice login session shortly before the cutover window. Refresh it successfully on MySQL. Record the time and expiry, and preserve the browser session. Do not restart the portal process: its demo sessions are in memory.

## 2. Fence source writers

Stop the workload and bulk generator. Prevent new requests through the demo gateway while keeping the portal process alive. On **Runner**, as **ec2-user**:

```bash
docker compose stop gateway
```

On **Runner**, as **ec2-user**:

```bash
docker compose stop source
```

In this dedicated demo, those are the application writers. Verify no other SQL sessions, janitors, or manual clients are writing; capture source transaction state and final binlog position. Record the start of application unavailability.

## 3. Drain CDC and reconcile

On **Laptop**, as **your user**:

```bash
.venv/bin/python scripts/cloud.py status
```

Require all selected tables loaded, no errors, no pending/failed/suspended validation, and fresh lag/backlog observations showing final changes applied. Save the final task checkpoint. A zero lag metric alone is insufficient.

On **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/reconcile.py --writers-fenced
```

`--writers-fenced` is your assertion that every writer is stopped; the script cannot discover an unknown application. Require `pass: true` in `evidence/reconciliation.json`. It scans the entire dataset and prints only table names, counts, and pass/fail.

## 4. Stop apply and check target integrity

On **Laptop**, as **your user**:

```bash
.venv/bin/python scripts/cloud.py stop
```

On **Laptop**, as **your user**:

```bash
.venv/bin/python scripts/cloud.py status
```

Wait for the task to report `stopped`. On **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/target_check.py integrity
```

This runs explicit foreign-key orphan queries and adjusts owned sequences to migrated maxima where they exist. Require a passing report. Original validated constraint flags alone do not recheck rows inserted while triggers were bypassed.

## 5. Activate PostgreSQL

On **Runner**, as **ec2-user**:

```bash
python3 scripts/lab.py start-target
```

On **Runner**, as **ec2-user**:

```bash
python3 scripts/lab.py switch-target
```

The routing helper changes gateway/admin selection and starts the stopped gateway; it does not perform reconciliation. Keep source stopped. Reopen Alice's existing browser session and choose **Refresh existing token**. Verify the active backend shows `target` and the subject remains Alice. Then test new login, client authentication, introspection, and revocation.

Record the end of application unavailability and the first target write. **Do not use switch-source as a post-write rollback.**

**Deliverable:** full-load duration, catch-up duration, downtime, all-row reconciliation, integrity results, old-session refresh proof, and a stated rollback boundary.
