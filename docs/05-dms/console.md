# Configure and operate DMS in the Console

**Environment:** AWS Console in your assigned account/region, plus the runner's
Session Manager terminal. **CLI equivalent:** [DMS build commands](build.md).
**Prerequisite:** SCT comparison reviewed, target prepared and empty, LOB scan
passes, source writer/binlogs ready, DMS instance Available.

## 1. Create the SQL users, secrets and role yourself

In the AWS Console, search for **EC2**, select **Instances**, select your runner, then choose **Connect → Session Manager → Connect**. Run `sudo su - ec2-user`, then `cd /opt/hydra-practice`. You will use the SQL clients installed in task 2.

A database user controls what DMS can read or write. A Secrets Manager secret stores that user's password. Create the database users first, then store their matching credentials.

### Source: Create the source replication user using SQL

Before opening MySQL, run `openssl rand -hex 24` in the runner shell. Save the resulting 48 characters privately as your new **source DMS password**. You will use it in the SQL below and in Secrets Manager. Do not capture it in evidence.

In another browser tab, open **RDS → Databases → your source cluster → Configuration → Master credentials ARN**. In Secrets Manager, choose **Retrieve secret value**. Use its `labadmin` password for this connection; it is different from the new DMS password.

In the runner shell, set your source endpoint from the worksheet and open MySQL:

```bash
export SOURCE_HOST=YOUR_SOURCE_WRITER_ENDPOINT
```

```bash
docker run --rm -it --network host -e MYSQL_HISTFILE=/dev/null \
  -v "$PWD/runtime/certs:/certs:ro" mysql:8.0.41 \
  mysql --host="$SOURCE_HOST" --port=3306 --user=labadmin --password \
  --ssl-mode=VERIFY_IDENTITY --ssl-ca=/certs/global-bundle.pem hydra
```

Enter the managed administrator password at the prompt. **Expected:** a `mysql>` prompt. Replace `YOUR_NEW_SOURCE_DMS_PASSWORD` below with the new DMS password you generated, then execute:

```sql
CREATE USER 'dms_repl'@'%' IDENTIFIED BY 'YOUR_NEW_SOURCE_DMS_PASSWORD';
GRANT SELECT ON hydra.* TO 'dms_repl'@'%';
GRANT REPLICATION CLIENT, REPLICATION SLAVE ON *.* TO 'dms_repl'@'%';
SHOW GRANTS FOR 'dms_repl'@'%';
SELECT @@global.binlog_format,@@global.binlog_row_image;
CALL mysql.rds_show_configuration;
SHOW MASTER STATUS;
exit
```

**Expected:** SELECT on hydra, replication privileges, ROW/FULL, 72-hour retention,
and a nonempty binlog filename/position. Record the position without changing it.
Do not run a schema deployment or source cleanup during the migration.
[AWS source grants/binlogs](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.MySQL.html).

### Target: Create the target DMS user using SQL

The source SQL block ends with `exit`, which returns you to the runner shell. For the target administrator password, open **RDS → Databases → your target PostgreSQL instance → Configuration → Master credentials ARN → Retrieve secret value**.

Set the target endpoint from your worksheet and open PostgreSQL:

```bash
export TARGET_HOST=YOUR_TARGET_INSTANCE_ENDPOINT
```

```bash
docker run --rm -it --network host -e PSQL_HISTORY=/dev/null \
  -v "$PWD/runtime/certs:/certs:ro" postgres:17.4 \
  psql "host=$TARGET_HOST port=5432 dbname=hydra user=labadmin sslmode=verify-full sslrootcert=/certs/global-bundle.pem" -W
```

Enter the target's managed administrator password. **Expected:** a psql prompt for database `hydra`. Execute:

```sql
CREATE ROLE dms_apply LOGIN;
\password dms_apply
```

Generate another independent value with `openssl rand -hex 24` in a separate
runner terminal. Store it privately and enter it at both psql password prompts.
Do not reuse the source DMS password. Then:

```sql
GRANT dms_apply TO labadmin;
GRANT CONNECT ON DATABASE hydra TO dms_apply;
GRANT USAGE ON SCHEMA public TO dms_apply;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO dms_apply;
CREATE SCHEMA awsdms_control AUTHORIZATION dms_apply;
GRANT USAGE,CREATE ON SCHEMA awsdms_control TO dms_apply;
GRANT SET ON PARAMETER session_replication_role TO dms_apply;
SELECT has_database_privilege('dms_apply','hydra','CONNECT');
SELECT has_schema_privilege('dms_apply','public','USAGE');
SELECT has_parameter_privilege('dms_apply','session_replication_role','SET');
\q
```

**Expected:** all three privilege checks true. Application tables are already
created by Hydra's native migrations. DMS receives DML permissions there and can
create its own control tables in awsdms_control. The role membership resolves
PostgreSQL's `must be able to SET ROLE dms_apply` ownership error.
[AWS PostgreSQL target permissions/constraints](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.PostgreSQL.html).

Verify the setting in a connection authenticated as `dms_apply`, not as labadmin.
On the runner, use your target DB instance endpoint and the new DMS password:

```bash
docker run --rm -it --network host -e PSQL_HISTORY=/dev/null \
  -v "$PWD/runtime/certs:/certs:ro" postgres:17.4 \
  psql "host=$TARGET_HOST port=5432 dbname=hydra user=dms_apply sslmode=verify-full sslrootcert=/certs/global-bundle.pem" -W
```

```sql
SELECT current_user;
SET session_replication_role=replica;
SHOW session_replication_role;
RESET session_replication_role;
SHOW session_replication_role;
\q
```

Require current_user=dms_apply, then replica, then origin. This verifies the
DMS session setting without changing the application's defaults. If permission
is denied, stop and review the target grants before creating the endpoint.
The author verified this permission on RDS PostgreSQL 17.11 by connecting as
dms_apply, setting session_replication_role to replica, and resetting it to origin.


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
   the target DB instance endpoint and port `5432`.
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

Repeat **Create endpoint** with type **Target**, engine **PostgreSQL** (RDS for PostgreSQL), your dms-target secret, the same scoped secrets role, database
`hydra`, `verify-full`, and the regional CA. Under **Endpoint settings**, add
`AfterConnectScript` with value:

```sql
SET session_replication_role=replica
```

The secret holds the native target DB instance endpoint, port 5432 and `dms_apply`.
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
   **Task settings JSON** printed below. Review the saved settings:
   `DO_NOTHING`, full load + CDC, all source-DDL flags false, limited LOB mode
   with a 64 KiB limit, validation enabled, dedicated control schema, and strict
   error handling.
4. Under **Table mappings → JSON editor**, paste the complete reviewed
   **Table mappings JSON** printed below. It selects exact tables including `networks`
   and maps MySQL `hydra` to PostgreSQL `public`. Do not replace it with a
   `hydra_%` wildcard or copy source migration bookkeeping. The table-settings rule loads
   hydra_client in four ID ranges. Use the accompanying SQL count check to verify
   that the boundaries suit your restored fixture before creating the task.
   Also retain all 17 UUID column transformations to `string(36)`. Compare them
   against the target catalog query below. These rules are required
   for CDC into Hydra's native PostgreSQL UUID columns.
5. For startup behavior, choose **Manually later**. Create the task and wait for
   **Ready**. Reopen its settings and verify the endpoint pair and both JSON
   configurations. Capture configuration evidence without secret values.

### Task settings JSON

Copy the JSON block into **Task settings → JSON editor**. Copy only the text from the opening `{` through the final `}`. The explanation table afterward is for reading, not pasting.

<details class="configuration" markdown="1">
<summary>Open the complete task settings JSON, then copy it into the matching DMS editor</summary>

```json
{
  "TargetMetadata": {
    "SupportLobs": true,
    "FullLobMode": false,
    "LimitedSizeLobMode": true,
    "LobMaxSize": 64,
    "BatchApplyEnabled": false
  },
  "FullLoadSettings": {
    "TargetTablePrepMode": "DO_NOTHING",
    "CreatePkAfterFullLoad": false,
    "MaxFullLoadSubTasks": 4,
    "TransactionConsistencyTimeout": 600,
    "CommitRate": 250
  },
  "ChangeProcessingDdlHandlingPolicy": {
    "HandleSourceTableDropped": false,
    "HandleSourceTableTruncated": false,
    "HandleSourceTableAltered": false
  },
  "ValidationSettings": {
    "EnableValidation": true,
    "ValidationMode": "ROW_LEVEL",
    "ThreadCount": 4
  },
  "Logging": {
    "EnableLogging": true
  },
  "ControlTablesSettings": {
    "ControlSchema": "awsdms_control"
  },
  "ErrorBehavior": {
    "DataErrorPolicy": "STOP_TASK",
    "DataTruncationErrorPolicy": "STOP_TASK",
    "TableErrorPolicy": "STOP_TASK",
    "ApplyErrorDeletePolicy": "STOP_TASK",
    "ApplyErrorInsertPolicy": "STOP_TASK",
    "ApplyErrorUpdatePolicy": "STOP_TASK"
  }
}
```

</details>

| Setting | Reason for this lab |
|---|---|
| DO_NOTHING | Keep Hydra's existing target tables; you checked that they were empty |
| Full load + CDC | Copy existing rows, then continue applying new changes |
| 4 full-load subtasks | Parallel table loading; not a guarantee of parallelizing the one largest table |
| 64 KiB limited LOB | Bound memory; require measured source values below the limit |
| Validation enabled | DMS compares migrated rows; inspect pending/failed/suspended counts |
| No source DDL handling | Keep the table layout fixed during the copy |
| STOP_TASK error policies | Stop the task if a value cannot be copied correctly |
| awsdms_control | Keep DMS tracking tables separate from Hydra tables |

If any measured LOB exceeds 65,536 bytes, stop and select/review a suitable LOB
configuration using AWS's LOB guidance before starting. Changing the limit without
understanding memory and truncation implications is not a completed exercise.
[AWS task settings](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TaskSettings.html),
[LOB handling](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.LOBSupport.html),
[validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html).

The 250-row commit rate limits per-worker buffering for this table with many
LOB columns. Four full-load workers can run concurrently. Monitor DMS free memory
and swap during the load; these settings are a lab starting point, not a
production throughput guarantee.

### Table mappings JSON

Copy this complete JSON block into **Table mappings → JSON editor**. Run the SQL checks below it in the named database terminals before saving the task. The rules tell DMS exactly which tables and values to copy.

<details class="configuration" markdown="1">
<summary>Open the complete table mappings JSON, then copy it into the matching DMS editor</summary>

```json
{
  "rules": [
    {
      "rule-type": "selection",
      "rule-id": "1",
      "rule-name": "1",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_client"
      },
      "rule-action": "explicit"
    },
    {
      "rule-type": "selection",
      "rule-id": "2",
      "rule-name": "2",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_jwk"
      },
      "rule-action": "explicit"
    },
    {
      "rule-type": "selection",
      "rule-id": "3",
      "rule-name": "3",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_access"
      },
      "rule-action": "explicit"
    },
    {
      "rule-type": "selection",
      "rule-id": "4",
      "rule-name": "4",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_authentication_session"
      },
      "rule-action": "explicit"
    },
    {
      "rule-type": "selection",
      "rule-id": "5",
      "rule-name": "5",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_code"
      },
      "rule-action": "explicit"
    },
    {
      "rule-type": "selection",
      "rule-id": "6",
      "rule-name": "6",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_flow"
      },
      "rule-action": "explicit"
    },
    {
      "rule-type": "selection",
      "rule-id": "7",
      "rule-name": "7",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_jti_blacklist"
      },
      "rule-action": "explicit"
    },
    {
      "rule-type": "selection",
      "rule-id": "8",
      "rule-name": "8",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_logout_request"
      },
      "rule-action": "explicit"
    },
    {
      "rule-type": "selection",
      "rule-id": "9",
      "rule-name": "9",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_obfuscated_authentication_session"
      },
      "rule-action": "explicit"
    },
    {
      "rule-type": "selection",
      "rule-id": "10",
      "rule-name": "10",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_oidc"
      },
      "rule-action": "explicit"
    },
    {
      "rule-type": "selection",
      "rule-id": "11",
      "rule-name": "11",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_pkce"
      },
      "rule-action": "explicit"
    },
    {
      "rule-type": "selection",
      "rule-id": "12",
      "rule-name": "12",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_refresh"
      },
      "rule-action": "explicit"
    },
    {
      "rule-type": "selection",
      "rule-id": "13",
      "rule-name": "13",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_trusted_jwt_bearer_issuer"
      },
      "rule-action": "explicit"
    },
    {
      "rule-type": "selection",
      "rule-id": "14",
      "rule-name": "14",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "networks"
      },
      "rule-action": "explicit"
    },
    {
      "rule-type": "transformation",
      "rule-id": "100",
      "rule-name": "100",
      "rule-target": "schema",
      "object-locator": {
        "schema-name": "hydra"
      },
      "rule-action": "rename",
      "value": "public"
    },
    {
      "rule-type": "table-settings",
      "rule-id": "200",
      "rule-name": "client-full-load-ranges",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_client"
      },
      "parallel-load": {
        "type": "ranges",
        "columns": [
          "id"
        ],
        "boundaries": [
          [
            "lab-restored-000000560000"
          ],
          [
            "lab-restored-000001120000"
          ],
          [
            "lab-restored-000001680000"
          ]
        ]
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "300",
      "rule-name": "uuid-hydra_client-pk",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_client",
        "column-name": "pk"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "301",
      "rule-name": "uuid-hydra_client-nid",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_client",
        "column-name": "nid"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "302",
      "rule-name": "uuid-hydra_jwk-pk",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_jwk",
        "column-name": "pk"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "303",
      "rule-name": "uuid-hydra_jwk-nid",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_jwk",
        "column-name": "nid"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "304",
      "rule-name": "uuid-hydra_oauth2_access-nid",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_access",
        "column-name": "nid"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "305",
      "rule-name": "uuid-hydra_oauth2_authentication_session-nid",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_authentication_session",
        "column-name": "nid"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "306",
      "rule-name": "uuid-hydra_oauth2_code-nid",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_code",
        "column-name": "nid"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "307",
      "rule-name": "uuid-hydra_oauth2_flow-nid",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_flow",
        "column-name": "nid"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "308",
      "rule-name": "uuid-hydra_oauth2_jti_blacklist-nid",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_jti_blacklist",
        "column-name": "nid"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "309",
      "rule-name": "uuid-hydra_oauth2_logout_request-nid",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_logout_request",
        "column-name": "nid"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "310",
      "rule-name": "uuid-hydra_oauth2_obfuscated_authentication_session-nid",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_obfuscated_authentication_session",
        "column-name": "nid"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "311",
      "rule-name": "uuid-hydra_oauth2_oidc-nid",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_oidc",
        "column-name": "nid"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "312",
      "rule-name": "uuid-hydra_oauth2_pkce-nid",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_pkce",
        "column-name": "nid"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "313",
      "rule-name": "uuid-hydra_oauth2_refresh-nid",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_refresh",
        "column-name": "nid"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "314",
      "rule-name": "uuid-hydra_oauth2_trusted_jwt_bearer_issuer-id",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_trusted_jwt_bearer_issuer",
        "column-name": "id"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "315",
      "rule-name": "uuid-hydra_oauth2_trusted_jwt_bearer_issuer-nid",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "hydra_oauth2_trusted_jwt_bearer_issuer",
        "column-name": "nid"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "316",
      "rule-name": "uuid-networks-id",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "hydra",
        "table-name": "networks",
        "column-name": "id"
      },
      "rule-action": "change-data-type",
      "data-type": {
        "type": "string",
        "length": 36
      }
    }
  ]
}
```

</details>

[AWS selection rules](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TableMapping.SelectionTransformation.Selections.html)
and [transformation rules](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TableMapping.SelectionTransformation.Transformations.html).

The `table-settings` rule divides the large client table into four full-load
ranges using its indexed, non-NULL `id` column. These boundaries are for the
supplied `lab-restored-*` fixture. Other client IDs still fall into the first or
last range; the boundaries do not filter rows out. DMS manages the adjoining
ranges. The other 13 tables keep their ordinary full-load behavior.

For the full fixture, check the approximate balance in **MySQL** before creating
the task:

```sql
SELECT CASE
 WHEN id <= 'lab-restored-000000560000' THEN 1
 WHEN id <= 'lab-restored-000001120000' THEN 2
 WHEN id <= 'lab-restored-000001680000' THEN 3
 ELSE 4 END AS load_range,COUNT(*) AS rows_in_range
FROM hydra_client GROUP BY load_range ORDER BY load_range;
```

Expect roughly one quarter of the full fixture per range. A small fixture may
occupy just one range. For a different dataset, choose three ordered boundaries
from its actual IDs and rerun the count query. Do not use a nullable or LOB
column for segmentation. The author cloud dataset uses `rds-volume-*` IDs, so
its rehearsal uses different boundary values with this same DMS mechanism.
[AWS range-based parallel load](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TableMapping.SelectionTransformation.Tablesettings.html).

### Why the UUID rules are required

Hydra stores 17 UUID columns as MySQL `CHAR(36)` and native PostgreSQL `uuid`.
The explicit column rules send those values through DMS as `string(36)`.
The target columns remain native UUIDs because target preparation is DO_NOTHING.
The author rehearsal copied every table successfully without these rules, but
its first CDC insert failed with PostgreSQL error `22P02`, invalid UUID syntax.
With these rules, client insert, update and delete replicated successfully.

Check the 17 destinations yourself in the **target PostgreSQL prompt**:

```sql
SELECT table_name,column_name FROM information_schema.columns
WHERE table_schema='public' AND udt_name='uuid'
ORDER BY table_name,column_name;
```

Compare every result to a `change-data-type` rule above. Add these rules before
you first start the task. A successful full load does not prove CDC conversion.
If you already started with different mappings, stop and review the failure and
recovery point. Do not assume Resume replays a rejected record. The author
rehearsal repeated the full load into an empty target after correcting the rules.
Follow the [exact disposable-lab recovery steps](../07-incidents/build.md#6-recover-a-failed-uuid-cdc-test-in-this-disposable-lab) if you encounter that failure before cutover.
[AWS datatype transformations and restart limitations](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TableMapping.SelectionTransformation.Transformations.html).

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
