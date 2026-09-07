# Watch individual changes move through DMS

**Where:** runner terminal for Hydra API calls and SQL; CloudShell or Console for
DMS. **Before starting:** full load is complete, task is running, source Hydra is
ready and target Hydra is stopped. Use the TLS SQL clients from Module 02.
The admin API is bound to runner loopback, not exposed to the internet.

## 1. Insert one identifiable client

On **Runner**, as **ec2-user**, create a public synthetic client. It has no client
secret and is separate from the portal client:

```bash
curl --fail-with-body -sS -X POST http://127.0.0.1:4445/admin/clients \
  -H 'Content-Type: application/json' \
  -d '{"client_id":"cdc-visible-demo","client_name":"CDC exercise","grant_types":["authorization_code"],"response_types":["code"],"redirect_uris":["http://localhost:8080/callback"],"token_endpoint_auth_method":"none","metadata":{"exercise":"insert","revision":1}}'
```

**Expected:** a created client with ID `cdc-visible-demo`. If it already exists,
inspect the previous exercise before retrying. In the **source MySQL prompt**:

```sql
SELECT id,nid,metadata FROM hydra_client WHERE id='cdc-visible-demo';
```

In the **target PostgreSQL prompt**, database hydra:

```sql
SELECT id,nid,metadata FROM public.hydra_client WHERE id='cdc-visible-demo';
```

Repeat the target SELECT until the row arrives. Record elapsed time, not its
private fields. Compare revision=1 and the same network ID. JSON key ordering
can differ while the value is equivalent.

## 2. Update the same client

On the runner, submit the complete client definition with revision 2:

```bash
curl --fail-with-body -sS -X PUT http://127.0.0.1:4445/admin/clients/cdc-visible-demo \
  -H 'Content-Type: application/json' \
  -d '{"client_id":"cdc-visible-demo","client_name":"CDC exercise updated","grant_types":["authorization_code"],"response_types":["code"],"redirect_uris":["http://localhost:8080/callback"],"token_endpoint_auth_method":"none","metadata":{"exercise":"update","revision":2}}'
```

Repeat both SQL queries. Require revision=2 on source and target before moving
on. Sending all fields avoids accidentally changing unrelated client settings
through replacement semantics.

## 3. Delete and prove disappearance

On the runner:

```bash
curl --fail-with-body -sS -X DELETE http://127.0.0.1:4445/admin/clients/cdc-visible-demo -o /dev/null -w '%{http_code}\n'
```

**Expected:** HTTP 204. Repeat the two SELECTs. Require zero rows on both sides.
Do not delete directly from PostgreSQL to make the check pass.
[Ory Hydra client management](https://www.ory.com/docs/hydra/guides/oauth2-clients).

## 4. Observe token activity from the portal

In the browser, use **Sign in → Alice → consent → Protected account → Refresh
existing token**. In a private browser window, repeat for Bob, then choose
**Revoke token and sign out**. These actions issue and revoke actual Hydra tokens.
The [restore lesson](../03-data/build.md#6-create-actual-oauth-state-through-the-browser)
shows the exact portal steps and tunnel command.

Before and after the actions, run these counts in **source MySQL**:

```sql
SELECT COUNT(*) AS access_rows FROM hydra_oauth2_access;
SELECT COUNT(*) AS refresh_rows FROM hydra_oauth2_refresh;
SELECT COUNT(*) AS flow_rows FROM hydra_oauth2_flow;
```

Run the same queries in PostgreSQL with the `public.` prefix on each table.
Counts can change while writers are active. Revocation can update a flag rather
than delete a row, so a count alone does not prove revocation. Prove the signed-out
behavior through the portal as well. Final equality is checked after fencing.

## 5. Correlate the changes with DMS

In **CloudShell**, restore `TASK_ARN` from your worksheet:

```bash
aws dms describe-table-statistics --replication-task-arn "$TASK_ARN" \
  --query 'TableStatistics[].{Table:TableName,State:TableState,Inserts:Inserts,Updates:Updates,Deletes:Deletes,Validation:ValidationState,Failed:ValidationFailedRecords,Pending:ValidationPendingRecords}' --output table
```

**Console:** DMS → Database migration tasks → your task → Table statistics.
Refresh and inspect hydra_client's CDC insert/update/delete counters and validation.
Open **Monitoring**, then its CloudWatch links. Compare **CDCLatencySource** and
**CDCLatencyTarget** over the same interval. Check timestamps and the
**CDCIncomingChanges** backlog; missing metrics do not mean zero lag.
[AWS DMS monitoring](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Monitoring.html).

**Gate:** observed insert, update and delete on both databases, application
login/refresh/revocation evidence, healthy task and a written plan to fence all
writers. Continue to [cutover](../06-cutover/build.md).
