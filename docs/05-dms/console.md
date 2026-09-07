# Configure and operate DMS in the Console

**Environment:** AWS Console in your assigned account/region, plus the runner's
Session Manager terminal. **CLI equivalent:** [DMS build commands](build.md).
**Prerequisite:** SCT comparison reviewed, target prepared and empty, LOB scan
passes, source writer/binlogs ready, DMS instance Available.

## 1. Create dedicated migration credentials

Open **EC2 → runner → Connect → Session Manager**. Switch to **ec2-user**, enter
`/opt/hydra-practice`, and run:

```bash
.venv/bin/python scripts/cloud.py grants
```

This creates the database users and fills the two existing DMS secrets. In
**Secrets Manager**, inspect the secret names/ARNs and recent version dates.
Never paste passwords into screenshots, guides or DMS task JSON. Do not rerun
the grants step while DMS is active because it rotates its passwords.

## 2. Import the database CA

1. Download the region's CA bundle from the
   [RDS trust store](https://truststore.pki.rds.amazonaws.com/us-east-1/us-east-1-bundle.pem)
   for this us-east-1 lab. The CLI endpoint helper downloads the same regional
   bundle; application clients may use the global bundle.
2. Open **DMS → Certificates → Import certificate**. Name it with your lab prefix
   and select the regional PEM file. Save the certificate identifier.
3. If using a different region, select its official regional bundle. Do not import
   an arbitrary certificate from a blog or disable validation to get a green test.

## 3. Create the source endpoint

Open **DMS → Endpoints → Create endpoint** and set:

| Field | Value |
|---|---|
| Endpoint type | Source |
| Identifier | your-prefix-source |
| Engine | Amazon Aurora MySQL |
| Access to endpoint database | AWS Secrets Manager |
| Secret | your dedicated dms-source secret |
| IAM role | your DMS secrets-access role |
| SSL mode | verify-full |
| CA certificate | the imported regional RDS certificate |

The secret holds the native **writer endpoint**, port 3306, and `dms_repl`
credentials. Do not select the RDS-managed master secret. In **Test endpoint
connection**, choose the target VPC and your replication instance, then **Run
test**. Require **successful** before continuing. Save the endpoint.

## 4. Create the target endpoint

Repeat **Create endpoint** with type **Target**, engine **Amazon Aurora
PostgreSQL**, your dms-target secret, the same scoped secrets role, database
`hydra`, `verify-full`, and the regional CA. Under **Endpoint settings**, add
`AfterConnectScript` with value:

```sql
SET session_replication_role=replica
```

The secret holds the native target writer endpoint, port 5432 and `dms_apply`.
Test using the same replication instance. Require **successful**. This session
setting is for DMS only; it must not become the Hydra application's default.
[AWS endpoint setup](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Endpoints.Creating.html).

If endpoints were already created through the CLI, select each one, inspect its
configuration, open **Connections**, and run its connection test instead of
creating duplicates. Resolve permission, network and TLS failures explicitly.

## 5. Create the task without starting it

1. Open **DMS → Database migration tasks → Create task**.
2. Enter your lab's task identifier, replication instance, source endpoint and
   target endpoint. Choose **Migrate existing data and replicate ongoing changes**.
3. Select the JSON editor for **Task settings** and paste the complete
   `migration/task-settings.json` from the lab bundle. Review the saved settings:
   `DO_NOTHING`, full load + CDC, all source-DDL flags false, limited LOB mode
   with a 64 KiB limit, validation enabled, dedicated control schema, and strict
   error handling.
4. Under **Table mappings → JSON editor**, paste the complete reviewed
   `runtime/table-mappings.json`. It selects exact tables including `networks`
   and maps MySQL `hydra` to PostgreSQL `public`. Do not replace it with a
   `hydra_%` wildcard or copy source migration bookkeeping.
5. For startup behavior, choose **Manually later**. Create the task and wait for
   **Ready**. Reopen its settings and verify the endpoint pair and both JSON
   configurations. Capture configuration evidence without secret values.

## 6. Start, monitor and inspect validation

1. Reconfirm the empty-target gate and that target Hydra is stopped.
2. Select the task → **Actions → Restart/Resume** (or **Start**, when offered).
   For its first run, choose the option to start the initial full load and CDC.
3. Open **Table statistics**. Require all selected tables to finish full load;
   investigate any error/suspended table. Inspect **Validation state**, pending,
   failed and suspended records. A running task alone does not prove validation.
4. Open the task's **Monitoring** tab and its **CloudWatch logs** link. In
   **CloudWatch → Metrics → DMS**, graph `CDCLatencySource`, `CDCLatencyTarget`,
   `CDCIncomingChanges`, task throughput and replication-instance CPU/memory/
   swap/free storage. Select the dimensions belonging to this task/instance.
5. Continue bounded source API activity. Confirm insert/update/delete counters
   advance on the affected tables; retain the successful workload evidence.

## 7. Add an alarm and practice recovery

In **CloudWatch → Alarms → Create alarm → Select metric → DMS**, select this
task's `CDCLatencyTarget`. Use one-minute periods, Maximum, threshold >60 seconds
for five periods as an initial lab threshold. Name it with your project prefix.
Use an existing instructor-approved notification destination, or create the alarm
without actions; the Console still displays alarm state. Do not send notifications
to a customer without the instructor's chosen destination.

For a stopped task, first diagnose the cause. **Resume processing** continues from
the checkpoint; **Restart from beginning / Reload target** is a different action.
Do not choose reload on a populated native-schema target without the explicit
reset procedure. Follow [cutover](../06-cutover/console.md) once full load,
validation and CDC drain are ready.

**Evidence:** two successful TLS endpoint tests, reviewed actual task settings,
complete table statistics, validation status, CDC activity, graphs and task logs.
