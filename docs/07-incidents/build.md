# Practice failures and recover them yourself

**Where:** runner for application incidents; CloudShell for DMS/network incidents.
Use only your disposable lab. Complete these exercises **before cutover**, while
source is active and target Hydra is stopped. Recover fully between cases.
[Console alternatives](console.md).

## 1. Record a healthy baseline

On the runner, as ec2-user in `/opt/hydra-practice`:

```bash
docker compose ps -a
```

```bash
curl -fsS http://127.0.0.1:4445/health/ready
```

Confirm source readiness and a working browser login/refresh. In CloudShell,
record the running task and successful endpoint tests using Module 05's commands.

## 2. Stop the gateway and diagnose the symptom

On the runner:

```bash
docker compose stop gateway
```

Reload the portal browser. It should fail while source readiness still succeeds.
Inspect `docker compose ps -a` and `docker compose logs --tail=30 gateway`.
Explain why a healthy database is insufficient for a working application.
Restore only gateway:

```bash
docker compose up -d --no-deps gateway
```

Reload the portal and refresh the existing Alice session. Keep portal running
throughout so you do not lose its in-memory test session.

## 3. Stop and resume CDC from its checkpoint

In CloudShell, with `TASK_ARN` from your worksheet:

```bash
aws dms stop-replication-task --replication-task-arn "$TASK_ARN"
```

```bash
aws dms wait replication-task-stopped --filters Name=replication-task-arn,Values="$TASK_ARN"
```

While stopped, execute only the INSERT in [the CDC exercise](../05-dms/use.md#1-insert-one-identifiable-client).
Prove it exists in MySQL and does not yet exist in PostgreSQL. Record the time.
Resume within your 72-hour binlog-retention window:

```bash
aws dms start-replication-task --replication-task-arn "$TASK_ARN" --start-replication-task-type resume-processing
```

Use Module 05's task/statistics commands. Require running, arrival of the row,
healthy validation and drained backlog. Finish the update/delete exercise.
`resume-processing` uses the saved checkpoint. `reload-target` restarts loading
and is not a substitute on a populated DO_NOTHING target.
[AWS start/resume task semantics](https://docs.aws.amazon.com/cli/latest/reference/dms/start-replication-task.html).

## 4. Remove only the DMS source network rule

Stop the task using step 3 and wait for stopped. In CloudShell, restore SOURCE_SG
and DMS_SG from your worksheet. Inspect the source rule first:

```bash
aws ec2 describe-security-groups --group-ids "$SOURCE_SG" --query 'SecurityGroups[0].IpPermissions'
```

Remove only DMS's TCP 3306 ingress reference:

```bash
aws ec2 revoke-security-group-ingress --group-id "$SOURCE_SG" --protocol tcp --port 3306 --source-group "$DMS_SG"
```

Run the source endpoint test:

```bash
aws dms test-connection --replication-instance-arn "$DMS_ARN" --endpoint-arn "$SOURCE_ENDPOINT"
```

```bash
aws dms describe-connections --filters Name=endpoint-arn,Values="$SOURCE_ENDPOINT" --query 'Connections[].{Status:Status,Error:LastFailureMessage}'
```

Security groups track established connections, so an existing connection can
survive a rule removal. Wait for a newly established endpoint test to fail; do
not broaden the disruption if a cached connection still works. Compare the
healthy Aurora writer and runner connection with the missing DMS network path.
Restore exactly the removed rule:

```bash
aws ec2 authorize-security-group-ingress --group-id "$SOURCE_SG" --protocol tcp --port 3306 --source-group "$DMS_SG"
```

Repeat test-connection and describe-connections until successful, then resume the
task with `resume-processing`. Require CDC catch-up and validation before ending.
[AWS security-group connection tracking](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/security-group-connection-tracking.html).

## 5. Investigate a validation failure without hiding it

Use an actual failure encountered in your run. In DMS Table statistics, identify
the table and failure count. Inspect task logs, your LOB maximum scan, source/target
column definitions and the [cutover comparison queries](../06-cutover/build.md).
Keep target Hydra stopped. Record the mismatched type/key/column without exposing
row secrets. Correct the underlying mapping or schema preparation and repeat the
migration into a fresh target if needed. Do not edit the report or omit a table
to produce a pass.

If the required binlog has expired, checkpoint resume cannot recover its missing
changes. Start a fresh lab baseline and rerun restore, schema preparation, full
load and CDC. Record the retention lesson and actual recovery time.

**Evidence per case:** healthy baseline, symptom, cause, exact correction, restored
application/CDC behavior and elapsed time.
