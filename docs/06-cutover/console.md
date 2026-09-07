# Validate and cut over from the Console

**Environment:** DMS/CloudWatch Console and runner Session Manager terminal.
**CLI equivalent:** [Validation and cutover commands](build.md). **Prerequisite:**
full load complete, no table errors, validation understood, target Hydra stopped.

## 1. Preserve the continuity test

Before fencing, sign in as Alice through the private portal and leave that browser
session open. In the runner terminal, as **ec2-user** in `/opt/hydra-practice`:

```bash
.venv/bin/python scripts/oauth_probe.py login
```

Keep `runtime/probe.cookies` private and unchanged. It references the existing
portal session and will be used to verify the same pre-cutover credentials.

## 2. Fence every source writer

Stop the generator and workload in their original terminals. If the instructor
started them as managed jobs, confirm their finished/stopped status. Confirm no
other client or deployment process can write to the source.

In **EC2 → runner → Connect → Session Manager**, as **ec2-user** in the project:

```bash
docker compose stop gateway source
```

Keep the portal process running: it holds the synthetic browser session. Record
the fence timestamp. Do not stop Aurora or revoke DMS's source access; DMS still
needs to read and drain its captured changes.

## 3. Prove drain and compare the data

1. In **DMS → Database migration tasks → your task → Table statistics**, confirm
   full load is complete for every selected table and there are no failed or
   suspended tables. Inspect validation results and resolve failures.
2. In **Monitoring / CloudWatch**, check the task's incoming-change queue and
   source/target latency over several samples after fencing. A single low-latency
   point is insufficient evidence.
3. In the runner terminal, execute the complete comparison:

```bash
.venv/bin/python scripts/reconcile.py --writers-fenced
```

`--writers-fenced` records your assertion; it does not stop writers for you. Require
every table to pass both count and canonical hash comparison. Save the report.
If the check fails, leave target Hydra stopped and investigate the mismatch.

## 4. Stop DMS and prepare normal application sessions

1. In **DMS → Database migration tasks**, select only your task.
2. Choose **Actions → Stop**, then confirm the selected task. Wait for **Stopped**.
   Recheck the status before permitting target writes.
3. In the runner terminal:

```bash
.venv/bin/python scripts/target_check.py integrity
```

Require zero orphan rows. The helper also resets owned sequences, including the
legacy minimum-value case. Trigger re-enablement alone does not validate old rows.

4. In the runner terminal:

```bash
python3 scripts/lab.py start-target
```

Wait for readiness, then:

```bash
python3 scripts/lab.py switch-target
```

The routing helper starts the gateway without restarting its source dependency.
It does not make a failed migration safe; the preceding gates are mandatory.

## 5. Prove retained and new sessions

In the runner terminal, as **ec2-user**:

```bash
.venv/bin/python scripts/oauth_probe.py check --expect-backend target
```

Then:

```bash
.venv/bin/python scripts/oauth_probe.py refresh --expect-backend target
```

Both must pass. Refresh the original browser's protected-account page; require
**Verified by target**. Use **Refresh existing token** there and verify it remains
authenticated. Open a separate session for Bob and prove a new login. Revoke that
new session and verify signed-out behavior. DMS must remain **Stopped** throughout.

## 6. Record the recovery boundary

After the target accepts new writes, the old source is stale. Do not choose a
source switch as a casual rollback: that can lose new tokens, client changes and
revocations. Keep the target fenced while diagnosing an unsuccessful cutover;
recover forward or execute a separately designed reverse migration.

**Evidence:** timestamps, writer fence, full-load/validation/queue state, complete
reconciliation, Stopped DMS task, zero-orphan/sequence report, retained refresh,
new login/revocation, and unchanged issuer/secrets configuration.
