# Configure and operate DMS in the Console

**Environment:** AWS Console in your assigned account/region, plus the runner's
Session Manager terminal. **CLI equivalent:** [DMS build commands](build.md).
**Prerequisite:** SCT comparison reviewed, target prepared and empty, LOB scan
passes, source writer/binlogs ready, DMS instance Available.

## 1. Create the SQL users, secrets and role yourself

Open **EC2 → your runner → Connect → Session Manager**. Switch to `ec2-user`
and enter `/opt/hydra-practice`. Open the MySQL and PostgreSQL clients from the
[application setup](../02-aws/application.md) and execute the complete SQL in
[CLI lesson steps 1-2](build.md#1-create-the-source-replication-user-using-sql).
Those SQL statements are shared by both interfaces: AWS Console cannot create a
MySQL/PostgreSQL user merely by creating a Secrets Manager secret.

Choose and privately retain separate source and target DMS passwords. Verify
the grants and binlog queries before continuing. Then create the secrets:

1. Open **Secrets Manager → Store a new secret**.
2. Select **Other type of secret** and the **Key/value pairs** editor.
3. Enter exactly these four keys for the source:

| Key | Value |
|---|---|
| username | dms_repl |
| password | The source DMS password you just set in SQL |
| host | Your native source cluster writer endpoint |
| port | 3306 |

4. Select the default **aws/secretsmanager** encryption key → **Next**.
5. Name the secret `your-prefix/dms-source`. Add your Project tag → **Next**.
6. Leave automatic rotation off for this bounded lab → **Next → Store**.
7. Repeat to create `your-prefix/dms-target` with `dms_apply`, its own password,
   the target writer endpoint and port `5432`.
8. Open each secret and copy its **complete ARN** to your worksheet. Do not select
   the RDS-managed master secret as a DMS endpoint credential.

Create the role that DMS assumes to read these secrets:

1. Open **IAM → Roles → Create role → Custom trust policy**.
2. Paste this policy for us-east-1, then continue and name the role
   `your-prefix-dms-secrets`:

```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"dms.us-east-1.amazonaws.com"},"Action":"sts:AssumeRole"}]}
```

3. On the new role open **Permissions → Add permissions → Create inline policy**.
4. Select **JSON** and paste this complete policy, replacing both ARN placeholders:

```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["secretsmanager:GetSecretValue","secretsmanager:DescribeSecret"],"Resource":["YOUR_SOURCE_DMS_SECRET_ARN","YOUR_TARGET_DMS_SECRET_ARN"]}]}
```

5. Name it `ReadLabEndpoints`, create it, and record the role ARN.
6. Confirm the Resource array names only your two endpoint secrets. Your Console
   identity needs permission to pass this role to DMS.

**Expected:** two populated secrets and a scoped read role, with SQL users already
created. [AWS's Console secret/role procedure](https://docs.aws.amazon.com/dms/latest/userguide/security_iam_secretsmanager.html).

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
   [task-settings JSON shown in the CLI lesson](build.md#8-write-and-explain-the-task-settings). Review the saved settings:
   `DO_NOTHING`, full load + CDC, all source-DDL flags false, limited LOB mode
   with a 64 KiB limit, validation enabled, dedicated control schema, and strict
   error handling.
4. Under **Table mappings → JSON editor**, paste the complete reviewed
   [14-table mapping JSON shown in the CLI lesson](build.md#7-write-and-review-the-exact-table-mappings). It selects exact tables including `networks`
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
5. Perform the [manual CDC exercise](use.md). Confirm insert/update/delete counters
   advance on the affected tables; retain the successful workload evidence.

## 7. Add an alarm and practice recovery

In **CloudWatch → Alarms → Create alarm → Select metric → DMS**, select this
task's `CDCLatencyTarget`. Use one-minute periods, Maximum, threshold >60 seconds
for five periods as an initial lab threshold. Name it with your project prefix.
Choose **Missing data: Treat missing data as missing**. Configure no notification
action for this exercise. Review the exact task dimensions, create the alarm and
record its name. The Console displays state; this exercise does not send messages.
The [CloudWatch CLI alternative](build.md#11-inspect-cloudwatch-and-create-your-own-lab-alarm)
shows metric discovery, sample retrieval and the equivalent alarm command.

For a stopped task, first diagnose the cause. **Resume processing** continues from
the checkpoint; **Restart from beginning / Reload target** is a different action.
Do not choose reload on a populated native-schema target without the explicit
reset procedure. Follow [cutover](../06-cutover/console.md) once full load,
validation and CDC drain are ready.

**Evidence:** two successful TLS endpoint tests, reviewed actual task settings,
complete table statistics, validation status, CDC activity, graphs and task logs.
