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
record the running task and successful endpoint tests using task 4's commands.

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

Use task 4's task/statistics commands. Require running, arrival of the row,
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

## 6. Recover a failed UUID CDC test in this disposable lab

Use this only **before target Hydra has ever served the application**, while
MySQL is the complete source of truth. It discards the target's incomplete copy.
It is not a recovery procedure for a PostgreSQL system that has accepted writes.
Keep source Hydra and the portal running; keep target Hydra stopped.

The author found this failure: full load completed, but a CDC insert failed with
PostgreSQL `22P02` and invalid UUID syntax. The corrected mapping transfers the
17 UUID source columns as DMS `string(36)`. A fresh CDC test passed. Resuming did
not replay the earlier rejected insert, so the author repeated full load.

1. In **DMS → your task**, save the error, checkpoint and table statistics. If
   the task is running, stop it with step 3 above and wait for Stopped. If it is
   already Failed, leave it failed for modification. Do not try to conceal the
   error by changing its handling policy.
2. Replace your local `table-mappings.json` with the complete reviewed mapping in
   [task creation](../05-dms/build.md#7-write-and-review-the-exact-table-mappings).
   Verify your 14 tables, range boundaries and all 17 UUID transformations.
3. In **CloudShell**, apply the correction:

```bash
aws dms modify-replication-task --replication-task-arn "$TASK_ARN" \
  --table-mappings file://table-mappings.json
```

```bash
aws dms describe-replication-tasks --filters Name=replication-task-arn,Values="$TASK_ARN" \
  --query 'ReplicationTasks[0].{State:Status,Mappings:TableMappings}'
```

Repeat the describe command until modification finishes and the task is Stopped.
**Console alternative:** task → Actions → Modify → Table mappings → JSON editor;
replace the mapping, save, wait for Stopped and reopen it to verify the saved JSON.

4. On the **runner**, `docker compose ps -a` must show target stopped. In the
   **target PostgreSQL prompt**, connected as hydra to database hydra, run the
   following only after confirming this is your incomplete training copy:

```sql
SELECT current_database(),current_user;
SELECT COUNT(*) AS native_migrations FROM public.schema_migration;
```

Require database hydra, owner hydra and 206 native migration records for this
pinned version. Then empty the 14 data tables in one transaction:

```sql
BEGIN;
TRUNCATE TABLE
 public.hydra_client,
 public.hydra_jwk,
 public.hydra_oauth2_access,
 public.hydra_oauth2_authentication_session,
 public.hydra_oauth2_code,
 public.hydra_oauth2_flow,
 public.hydra_oauth2_jti_blacklist,
 public.hydra_oauth2_logout_request,
 public.hydra_oauth2_obfuscated_authentication_session,
 public.hydra_oauth2_oidc,
 public.hydra_oauth2_pkce,
 public.hydra_oauth2_refresh,
 public.hydra_oauth2_trusted_jwt_bearer_issuer,
 public.networks;
SELECT COUNT(*) AS native_migrations FROM public.schema_migration;
COMMIT;
```

Require 206 again. `schema_migration` is preserved. No CASCADE is used: an
unexpected dependency must stop the reset. Rerun the target counts from
[cutover comparisons](../06-cutover/build.md#4-compare-exact-table-counts-while-writes-are-stopped)
and require all 14 data tables empty. Keep target Hydra stopped.

5. In **CloudShell**, restart the full load:

```bash
aws dms start-replication-task --replication-task-arn "$TASK_ARN" \
  --start-replication-task-type reload-target
```

**Console alternative:** task → Actions → Restart/Resume → choose Restart, which
reloads existing data, and confirm the action. This is safe here because you
explicitly emptied your incomplete target copy. DO_NOTHING preserves the native
schema and does not empty it for you.

6. Repeat full-load monitoring, the visible CDC exercise, final validation and
   cutover. If the previous test client still exists on MySQL, let full load copy
   it and use a new unique test ID in every command of the fresh CDC exercise.
   Do not insert a duplicate client or edit target rows to make validation pass.

[AWS modifying a task](https://docs.aws.amazon.com/cli/latest/reference/dms/modify-replication-task.html),
[restart and resume](https://docs.aws.amazon.com/cli/latest/reference/dms/start-replication-task.html),
[datatype transformation limits](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TableMapping.SelectionTransformation.Transformations.html).
