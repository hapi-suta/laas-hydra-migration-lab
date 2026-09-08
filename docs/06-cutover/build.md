# Validate the migration and cut over yourself

**Where:** CloudShell for DMS; EC2 runner for Docker and TLS SQL clients; your
browser for OAuth checks. **Before starting:** full load complete, CDC running,
all 14 tables selected and target Hydra stopped. [Console route](console.md).

## 1. Preserve a working source session

In the existing portal browser, sign in as Alice and select **Refresh existing
token**. Confirm **Verified by source**. Leave that session open. Use a private
window for later Bob tests. Do not restart portal: its demo browser sessions are
held in memory. Record the UTC time and displayed expiry, without token values.

On **Runner**, as ec2-user in `/opt/hydra-practice`, save the issuer and public
signing-key document for comparison:

```bash
curl -fsS http://127.0.0.1:8080/.well-known/openid-configuration -o evidence/discovery-before.json
```

```bash
curl -fsS http://127.0.0.1:8080/.well-known/jwks.json -o evidence/jwks-before.json
```

JWKS contains public signing keys. Never export the private hydra_jwk database
rows as a substitute.

## 2. Stop every source writer

Finish the CDC exercise and close other SQL write sessions. If you started any
optional workload job, stop it in its original terminal and confirm it exited.
Stop the gateway and source Hydra while keeping portal alive:

```bash
date -u '+%Y-%m-%dT%H:%M:%SZ' | tee evidence/fence-time.txt
```

```bash
docker compose stop gateway
```

```bash
docker compose stop source
```

```bash
docker compose ps -a
```

Expected: source and gateway stopped, portal running, target not running. In the
**source MySQL administrator prompt** from task 2:

```sql
SELECT trx_mysql_thread_id,trx_started,trx_state FROM information_schema.innodb_trx;
SHOW PROCESSLIST;
SHOW MASTER STATUS;
```

Investigate every application transaction; DMS's replication connection can remain.
Record the final binlog file/position. Repeat `SHOW MASTER STATUS` after a minute
and investigate changes from unknown writers. No application deployment, manual
SQL write or janitor may continue. Record the start of application downtime. The portal URL will now fail to load because you stopped its gateway. This is expected during the switch. Keep Alice's browser tab and the portal container open; do not sign out or restart portal.

## 3. Prove CDC has drained

In **CloudShell**, using your worksheet's `TASK_ARN`:

```bash
aws dms describe-replication-tasks --filters Name=replication-task-arn,Values="$TASK_ARN" \
  --query 'ReplicationTasks[].{Status:Status,Stats:ReplicationTaskStats,Checkpoint:RecoveryCheckpoint,Failure:LastFailureMessage}'
```

```bash
aws dms describe-table-statistics --replication-task-arn "$TASK_ARN" \
  --query 'TableStatistics[].{Table:TableName,Load:TableState,Validation:ValidationState,Pending:ValidationPendingRecords,Failed:ValidationFailedRecords,Suspended:ValidationSuspendedRecords}' --output table
```

Require task **running**, 14 selected tables fully loaded, validation completed
with zero pending, failed or suspended records. Unsupported validation is a gap
to resolve, not a pass. In **DMS → task → Monitoring / CloudWatch**, inspect fresh
**CDCIncomingChanges**, **CDCLatencySource** and **CDCLatencyTarget** samples over
several minutes after the fence. Require the incoming queue drained and no errors.
A zero-lag datapoint alone is insufficient. Save the task checkpoint and statistics.
[AWS DMS validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html)
and [monitoring](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Monitoring.html).

## 4. Compare exact table counts while writes are stopped

In the **source MySQL prompt**, run:

```sql
SELECT 'hydra_client' AS table_name,COUNT(*) AS row_count FROM hydra_client
UNION ALL
SELECT 'hydra_jwk' AS table_name,COUNT(*) AS row_count FROM hydra_jwk
UNION ALL
SELECT 'hydra_oauth2_access' AS table_name,COUNT(*) AS row_count FROM hydra_oauth2_access
UNION ALL
SELECT 'hydra_oauth2_authentication_session' AS table_name,COUNT(*) AS row_count FROM hydra_oauth2_authentication_session
UNION ALL
SELECT 'hydra_oauth2_code' AS table_name,COUNT(*) AS row_count FROM hydra_oauth2_code
UNION ALL
SELECT 'hydra_oauth2_flow' AS table_name,COUNT(*) AS row_count FROM hydra_oauth2_flow
UNION ALL
SELECT 'hydra_oauth2_jti_blacklist' AS table_name,COUNT(*) AS row_count FROM hydra_oauth2_jti_blacklist
UNION ALL
SELECT 'hydra_oauth2_logout_request' AS table_name,COUNT(*) AS row_count FROM hydra_oauth2_logout_request
UNION ALL
SELECT 'hydra_oauth2_obfuscated_authentication_session' AS table_name,COUNT(*) AS row_count FROM hydra_oauth2_obfuscated_authentication_session
UNION ALL
SELECT 'hydra_oauth2_oidc' AS table_name,COUNT(*) AS row_count FROM hydra_oauth2_oidc
UNION ALL
SELECT 'hydra_oauth2_pkce' AS table_name,COUNT(*) AS row_count FROM hydra_oauth2_pkce
UNION ALL
SELECT 'hydra_oauth2_refresh' AS table_name,COUNT(*) AS row_count FROM hydra_oauth2_refresh
UNION ALL
SELECT 'hydra_oauth2_trusted_jwt_bearer_issuer' AS table_name,COUNT(*) AS row_count FROM hydra_oauth2_trusted_jwt_bearer_issuer
UNION ALL
SELECT 'networks' AS table_name,COUNT(*) AS row_count FROM networks
ORDER BY table_name;
```

In the **target PostgreSQL prompt**, database hydra, run:

```sql
SELECT 'hydra_client' AS table_name,COUNT(*) AS row_count FROM public.hydra_client
UNION ALL
SELECT 'hydra_jwk' AS table_name,COUNT(*) AS row_count FROM public.hydra_jwk
UNION ALL
SELECT 'hydra_oauth2_access' AS table_name,COUNT(*) AS row_count FROM public.hydra_oauth2_access
UNION ALL
SELECT 'hydra_oauth2_authentication_session' AS table_name,COUNT(*) AS row_count FROM public.hydra_oauth2_authentication_session
UNION ALL
SELECT 'hydra_oauth2_code' AS table_name,COUNT(*) AS row_count FROM public.hydra_oauth2_code
UNION ALL
SELECT 'hydra_oauth2_flow' AS table_name,COUNT(*) AS row_count FROM public.hydra_oauth2_flow
UNION ALL
SELECT 'hydra_oauth2_jti_blacklist' AS table_name,COUNT(*) AS row_count FROM public.hydra_oauth2_jti_blacklist
UNION ALL
SELECT 'hydra_oauth2_logout_request' AS table_name,COUNT(*) AS row_count FROM public.hydra_oauth2_logout_request
UNION ALL
SELECT 'hydra_oauth2_obfuscated_authentication_session' AS table_name,COUNT(*) AS row_count FROM public.hydra_oauth2_obfuscated_authentication_session
UNION ALL
SELECT 'hydra_oauth2_oidc' AS table_name,COUNT(*) AS row_count FROM public.hydra_oauth2_oidc
UNION ALL
SELECT 'hydra_oauth2_pkce' AS table_name,COUNT(*) AS row_count FROM public.hydra_oauth2_pkce
UNION ALL
SELECT 'hydra_oauth2_refresh' AS table_name,COUNT(*) AS row_count FROM public.hydra_oauth2_refresh
UNION ALL
SELECT 'hydra_oauth2_trusted_jwt_bearer_issuer' AS table_name,COUNT(*) AS row_count FROM public.hydra_oauth2_trusted_jwt_bearer_issuer
UNION ALL
SELECT 'networks' AS table_name,COUNT(*) AS row_count FROM public.networks
ORDER BY table_name;
```

Every corresponding count must match. Save both results. Counts are a separate
check from DMS row validation: matching counts alone cannot detect changed values.
For the restored fixture, also compare semantic metadata totals. In MySQL:

```sql
SELECT COUNT(*) AS restored_clients,
 SUM(OCTET_LENGTH(JSON_UNQUOTE(JSON_EXTRACT(metadata,'$.description')))) AS description_bytes,
 SUM(CAST(JSON_UNQUOTE(JSON_EXTRACT(metadata,'$.ordinal')) AS UNSIGNED)) AS ordinal_sum
FROM hydra_client WHERE id LIKE 'lab-restored-%';
```

In PostgreSQL:

```sql
SELECT COUNT(*) AS restored_clients,
 SUM(OCTET_LENGTH(metadata::jsonb->>'description')) AS description_bytes,
 SUM((metadata::jsonb->>'ordinal')::bigint) AS ordinal_sum
FROM public.hydra_client WHERE id LIKE 'lab-restored-%';
```

All three values must match. Large metadata scans can take tens of minutes,
especially when the values are not in the database cache. Keep all writers
fenced until the evidence is complete. Investigate any mismatch before cutover.

## 5. Stop DMS apply

In **CloudShell**:

```bash
aws dms stop-replication-task --replication-task-arn "$TASK_ARN"
```

```bash
aws dms wait replication-task-stopped --filters Name=replication-task-arn,Values="$TASK_ARN"
```

```bash
aws dms describe-replication-tasks --filters Name=replication-task-arn,Values="$TASK_ARN" --query 'ReplicationTasks[].Status'
```

Require **stopped**. Preserve final statistics. Do not start target Hydra while DMS
is still applying data or validation is unresolved.
[AWS stop task](https://docs.aws.amazon.com/cli/latest/reference/dms/stop-replication-task.html).

## 6. Check that linked records still have their parent records

A foreign key links one record to another, such as an OAuth record to its network. An orphan is a record whose parent is missing. Check every link because DMS copied data with these checks disabled in its own connection.

In **target psql**, database hydra, as schema owner hydra, enable stop-on-error:

```sql
\set ON_ERROR_STOP on
SHOW session_replication_role;
```

Expected: **origin** for the normal application account. DMS used replica mode
only in its own sessions. Constraints marked valid do not prove that rows loaded
with disabled triggers satisfy them. Build a temporary list of orphan queries
from the actual foreign-key catalog:

```sql
CREATE TEMP VIEW lab_fk_checks AS
SELECT co.conname,
 format('SELECT %L AS constraint_name, COUNT(*) AS orphans FROM %I.%I c WHERE %s AND NOT EXISTS (SELECT 1 FROM %I.%I p WHERE %s);',
 co.conname,ns.nspname,child.relname,
 string_agg(format('c.%I IS NOT NULL',ca.attname),' AND ' ORDER BY ck.ord),
 pns.nspname,parent.relname,
 string_agg(format('c.%I = p.%I',ca.attname,pa.attname),' AND ' ORDER BY ck.ord)) AS check_sql
FROM pg_constraint co
JOIN pg_class child ON child.oid=co.conrelid
JOIN pg_namespace ns ON ns.oid=child.relnamespace
JOIN pg_class parent ON parent.oid=co.confrelid
JOIN pg_namespace pns ON pns.oid=parent.relnamespace
CROSS JOIN LATERAL unnest(co.conkey) WITH ORDINALITY ck(attnum,ord)
JOIN pg_attribute ca ON ca.attrelid=child.oid AND ca.attnum=ck.attnum
JOIN pg_attribute pa ON pa.attrelid=parent.oid AND pa.attnum=co.confkey[ck.ord]
WHERE co.contype='f' AND ns.nspname='public'
GROUP BY co.conname,ns.nspname,child.relname,pns.nspname,parent.relname;
SELECT check_sql FROM lab_fk_checks ORDER BY conname;
```

Read the generated SELECT statements. They contain no writes. Execute them with
psql's `\gexec`; do not put a semicolon before `\gexec` in this block:

```sql
SELECT check_sql FROM lab_fk_checks ORDER BY conname
\gexec
```

The pinned schema has 28 foreign keys. Require **orphans=0 for every result**.
If your schema differs, reconcile its constraint count before proceeding.

## 7. Set the next automatic ID values

A sequence supplies the next automatic number for a new record. Copying rows does not advance it. Set it from the copied data so a new write does not reuse an existing number.

In the same psql session:

```sql
CREATE TEMP VIEW lab_sequences AS
SELECT n.nspname,c.relname,a.attname,s.seqmin,s.seqincrement,
 pg_get_serial_sequence(format('%I.%I',n.nspname,c.relname),a.attname) AS sequence_name
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
JOIN pg_sequence s ON s.seqrelid=pg_get_serial_sequence(format('%I.%I',n.nspname,c.relname),a.attname)::regclass
WHERE n.nspname='public' AND c.relkind='r';
TABLE lab_sequences;
```

Inspect the two owned sequences expected for this pinned schema. Each increment
must be positive. Descending or unexpected sequences require a separate reset
policy. Generate the exact setval commands:

```sql
CREATE TEMP VIEW lab_sequence_resets AS
SELECT format('SELECT setval(%L::regclass,GREATEST(COALESCE(MAX(%I),%s),%s),COALESCE(MAX(%I)>=%s,false)) FROM %I.%I;',
 sequence_name,attname,seqmin,seqmin,attname,seqmin,nspname,relname) AS reset_sql
FROM lab_sequences WHERE seqincrement>0;
SELECT reset_sql FROM lab_sequence_resets;
```

After review, execute:

```sql
SELECT reset_sql FROM lab_sequence_resets
\gexec
```

This uses the migrated maximum when valid. An empty table or legacy maximum below
the sequence minimum resets to the minimum with `is_called=false`, so the next
insert uses that value. It avoids `setval: value 0 is out of bounds`.
[PostgreSQL sequence functions](https://www.postgresql.org/docs/17/functions-sequence.html).
Exit psql with `\q`.

## 8. Start target Hydra and change the application route

On **Runner**, as ec2-user, keep the original `.env` and portal process. Start only
the target service, without rerunning its initialization dependency:

```bash
docker compose --profile target up -d --no-deps target
```

```bash
curl -fsS http://127.0.0.1:5445/health/ready
```

Expected: HTTP success and a JSON body containing `"status":"ok"`. If it fails, inspect target logs and leave the gateway
stopped. Starting target can itself write database state; the recovery boundary
is no later than this point, not merely the first browser login.

Update both routing files in place, preserving the bind-mounted file inode:

```bash
printf '{"active":"target"}\n' > runtime/active.json
```

```bash
printf 'upstream hydra_active { server target:4444; }\n' > runtime/upstream.conf
```

```bash
chmod 644 runtime/upstream.conf
```

```bash
docker compose up -d --no-deps gateway
```

```bash
curl -fsS http://127.0.0.1:8080/ -o /dev/null -w '%{http_code}\n'
```

Expected: `200`. The container can show Started before the gateway accepts requests. If the first check reports a connection reset or refusal, wait a few seconds and repeat this curl check. If it still fails after a minute, inspect `docker compose logs --tail=50 gateway target` and resolve the error before the browser tests. Do not restart the portal.

The gateway uses target and the portal's admin selection reads
`active.json`. Source remains stopped. DMS remains stopped.

## 9. Prove continuity and record downtime

1. In Alice's **existing** browser session, open Protected account. Require
   **Verified by target**, active status and Alice's original subject.
2. Select **Refresh existing token**. Require the same subject and target backend.
   A new login does not substitute for this retained-refresh test.
3. In a private window, sign in as Bob and refresh. This proves new target writes.
4. Select **Revoke token and sign out** for Bob. Returning to Protected account
   must require sign-in again. Require the confirmation **Hydra rejected the revoked refresh token**; the portal checks reuse before discarding its session tokens.
5. On the runner, save discovery and JWKS again using step 1's curl commands with
   `after` filenames. Compare `issuer` and the public key IDs/material with before.
   Investigate a changed issuer or missing old signing key before accepting.
6. Record the first successful target request and elapsed time since fence.

After target writes, MySQL is stale. Returning traffic to it can lose new logins,
refresh rotations and revocations. Keep a failed target fenced and recover forward
or follow a separately designed reverse migration. This lab does not implement
reverse CDC.

**Deliverable:** restore size, load duration, CDC drain evidence, exact counts,
DMS validation, all foreign-key checks, sequence results, measured downtime,
retained refresh, new login/revocation and the recovery boundary.
