# Create and operate DMS with native AWS CLI commands

[Console alternative](console.md). **You create the users, secrets, role,
endpoints, mappings and task yourself.** No `cloud.py`, generated manifest or
instructor-prepared endpoint is required. Complete the [schema checks](../04-sct/schema-checks.md)
first. Keep target Hydra stopped. Use your own worksheet values throughout.

## 1. Create the source replication user using SQL

On the runner, reconnect to MySQL as `labadmin` using the TLS client command in
[application setup](../02-aws/application.md#4-connect-to-the-source-using-its-managed-administrator-password).
Generate a separate password privately with `openssl rand -hex 24` on the runner.
Keep its 48 hexadecimal characters in your password manager and use that value
in the SQL below. Do not capture it in evidence. Execute:

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

## 2. Create the target DMS user using SQL

Reconnect to PostgreSQL database `hydra` as `labadmin`. Execute:

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


## 3. Store the dedicated credentials in Secrets Manager

**Where:** CloudShell, your lab directory. Restore LAB, AWS_REGION, SOURCE_HOST,
TARGET_HOST and DMS_ARN from your worksheet if this is a new shell. Create two
private JSON files with an editor (not a password in a shell command):

```bash
umask 077
```

```bash
vi source-secret.json
```

```json
{"username":"dms_repl","password":"YOUR_SOURCE_DMS_PASSWORD","host":"YOUR_SOURCE_WRITER_ENDPOINT","port":3306}
```

```bash
vi target-secret.json
```

```json
{"username":"dms_apply","password":"YOUR_TARGET_DMS_PASSWORD","host":"YOUR_TARGET_INSTANCE_ENDPOINT","port":5432}
```

Use the exact passwords you just assigned in SQL. Create each secret:

```bash
export SOURCE_SECRET=$(aws secretsmanager create-secret --name "$LAB/dms-source" \
  --secret-string file://source-secret.json --tags Key=Project,Value="$LAB" --query ARN --output text)
```

```bash
export TARGET_SECRET=$(aws secretsmanager create-secret --name "$LAB/dms-target" \
  --secret-string file://target-secret.json --tags Key=Project,Value="$LAB" --query ARN --output text)
```

```bash
aws secretsmanager describe-secret --secret-id "$SOURCE_SECRET" --query '{Name:Name,ARN:ARN}'
```

```bash
aws secretsmanager describe-secret --secret-id "$TARGET_SECRET" --query '{Name:Name,ARN:ARN}'
```

```bash
rm source-secret.json target-secret.json
```

Record the returned ARNs. The commands use the default Secrets Manager KMS key.
Do not substitute RDS-managed master secrets: DMS requires a compatible secret
with host and port. Creating a secret does not itself create the SQL user.
[AWS DMS secret authentication](https://docs.aws.amazon.com/dms/latest/userguide/security_iam_secretsmanager.html)
and [create-secret CLI](https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/create-secret.html).

## 4. Create the role DMS uses to read those two secrets

```bash
cat > dms-secrets-trust.json <<'JSON'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"dms.us-east-1.amazonaws.com"},"Action":"sts:AssumeRole"}]}
JSON
```

```bash
cat > dms-secrets-policy.json <<JSON
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["secretsmanager:GetSecretValue","secretsmanager:DescribeSecret"],"Resource":["$SOURCE_SECRET","$TARGET_SECRET"]}]}
JSON
```

```bash
export DMS_SECRET_ROLE=$(aws iam create-role --role-name "$LAB-dms-secrets" \
  --assume-role-policy-document file://dms-secrets-trust.json --query Role.Arn --output text)
```

```bash
aws iam put-role-policy --role-name "$LAB-dms-secrets" --policy-name ReadLabEndpoints \
  --policy-document file://dms-secrets-policy.json
```

```bash
aws iam get-role-policy --role-name "$LAB-dms-secrets" --policy-name ReadLabEndpoints
```

**Expected:** exactly your two secret ARNs in the resource list. Your operator role
must be allowed to pass this role to DMS. The service principal includes this
lab's region; change it if using another region. With a customer-managed KMS key,
additional decrypt/key-policy grants are needed; this baseline uses the default key.
[AWS secret role setup](https://docs.aws.amazon.com/dms/latest/userguide/security_iam_secretsmanager.html).

## 5. Import the regional RDS certificate and create the endpoints

```bash
curl -fL https://truststore.pki.rds.amazonaws.com/us-east-1/us-east-1-bundle.pem -o rds-region.pem
```

```bash
export DMS_CA=$(aws dms import-certificate --certificate-identifier "$LAB-rds-ca" \
  --certificate-pem file://rds-region.pem --query Certificate.CertificateArn --output text)
```

```bash
cat > source-endpoint-settings.json <<JSON
{"SecretsManagerAccessRoleArn":"$DMS_SECRET_ROLE","SecretsManagerSecretId":"$SOURCE_SECRET"}
JSON
```

```bash
cat > target-endpoint-settings.json <<JSON
{"SecretsManagerAccessRoleArn":"$DMS_SECRET_ROLE","SecretsManagerSecretId":"$TARGET_SECRET","AfterConnectScript":"SET session_replication_role=replica"}
JSON
```

```bash
export SOURCE_ENDPOINT=$(aws dms create-endpoint --endpoint-identifier "$LAB-source" \
  --endpoint-type source --engine-name aurora --ssl-mode verify-full --certificate-arn "$DMS_CA" \
  --my-sql-settings file://source-endpoint-settings.json --tags Key=Project,Value="$LAB" \
  --query Endpoint.EndpointArn --output text)
```

```bash
export TARGET_ENDPOINT=$(aws dms create-endpoint --endpoint-identifier "$LAB-target" \
  --endpoint-type target --engine-name postgres --database-name hydra \
  --ssl-mode verify-full --certificate-arn "$DMS_CA" \
  --postgre-sql-settings file://target-endpoint-settings.json --tags Key=Project,Value="$LAB" \
  --query Endpoint.EndpointArn --output text)
```

The DMS engine tokens are `aurora` for Aurora MySQL and `postgres` for RDS PostgreSQL. Target
`hydra` is the application database; SCT's `sct_compare` is not the DMS destination.
`AfterConnectScript` disables FK triggers in DMS sessions while tables load in
parallel. It does not change the normal Hydra session setting and does not remove
the need for explicit post-load foreign-key validation.
[AWS create-endpoint](https://docs.aws.amazon.com/cli/latest/reference/dms/create-endpoint.html),
[DMS TLS](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Security.SSL.html),
[PostgreSQL endpoint settings](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.PostgreSQL.html).

## 6. Test both endpoints

```bash
aws dms test-connection --replication-instance-arn "$DMS_ARN" --endpoint-arn "$SOURCE_ENDPOINT"
```

```bash
aws dms test-connection --replication-instance-arn "$DMS_ARN" --endpoint-arn "$TARGET_ENDPOINT"
```

```bash
aws dms describe-connections --filters Name=replication-instance-arn,Values="$DMS_ARN" \
  --query 'Connections[].{Endpoint:EndpointIdentifier,State:Status,Failure:LastFailureMessage}' --output table
```

Repeat only the describe command until both are **successful**. If either fails,
read LastFailureMessage. Check secret username/password/host/port, role trust and
permissions, private Secrets Manager endpoint, SG ports, both peering routes,
RDS CA, SQL grants and the target database name. Do not disable TLS to pass.
[AWS test-connection](https://docs.aws.amazon.com/cli/latest/reference/dms/test-connection.html).

## 7. Write and review the exact table mappings

In CloudShell create `table-mappings.json` with the complete JSON below. Compare
each table to your own SQL inventory from task 3 before saving. This baseline
has 14 data tables. Stop and revise the review if your Hydra version differs.
`explicit` avoids wildcard interpretation of table-name characters. `networks`
is included. Native migration bookkeeping is deliberately not selected.

```bash
vi table-mappings.json
```

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

## 8. Write and explain the task settings

Create `task-settings.json` in the same directory:

```bash
vi task-settings.json
```

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

## 9. Create the task, inspect it, then start it yourself

```bash
export TASK_ARN=$(aws dms create-replication-task --replication-task-identifier "$LAB" \
  --source-endpoint-arn "$SOURCE_ENDPOINT" --target-endpoint-arn "$TARGET_ENDPOINT" \
  --replication-instance-arn "$DMS_ARN" --migration-type full-load-and-cdc \
  --table-mappings file://table-mappings.json --replication-task-settings file://task-settings.json \
  --tags Key=Project,Value="$LAB" --query ReplicationTask.ReplicationTaskArn --output text)
```

```bash
aws dms describe-replication-tasks --filters Name=replication-task-arn,Values="$TASK_ARN" \
  --query 'ReplicationTasks[0].{State:Status,Source:SourceEndpointArn,Target:TargetEndpointArn,Migration:MigrationType,Settings:ReplicationTaskSettings,Mappings:TableMappings}'
```

Wait for Ready. Recheck target emptiness and that the target Hydra container is
stopped. Save the displayed settings and both input JSON files as your evidence.
Only then start the first full load:

```bash
aws dms start-replication-task --replication-task-arn "$TASK_ARN" --start-replication-task-type start-replication
```

[AWS create task](https://docs.aws.amazon.com/cli/latest/reference/dms/create-replication-task.html)
and [start task](https://docs.aws.amazon.com/cli/latest/reference/dms/start-replication-task.html).

## 10. Observe full load, then demonstrate live changes

```bash
aws dms describe-replication-tasks --filters Name=replication-task-arn,Values="$TASK_ARN" \
  --query 'ReplicationTasks[].{State:Status,Progress:ReplicationTaskStats,Failure:LastFailureMessage,Checkpoint:RecoveryCheckpoint}'
```

```bash
aws dms describe-table-statistics --replication-task-arn "$TASK_ARN" \
  --query 'TableStatistics[].{Table:TableName,State:TableState,Loaded:FullLoadRows,Inserts:Inserts,Updates:Updates,Deletes:Deletes,Validation:ValidationState,Pending:ValidationPendingRecords,Failed:ValidationFailedRecords,Suspended:ValidationSuspendedRecords}' --output table
```

**Expected:** all 14 tables loaded, no table errors, and validation progressing.
A Running task is not proof of success. Keep the source application working and
perform the [visible insert/update/delete exercise](use.md) yourself. Observe each
change on PostgreSQL before moving to the next change.

In **DMS → task → Monitoring**, open CloudWatch metrics and graph source/target
CDC latency and incoming changes. Add replication-instance CPU, free memory,
swap and free storage from **CloudWatch → Metrics → DMS**. Use your exact task
and instance dimensions. Record timestamps around the changes you made.
[AWS DMS monitoring](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Monitoring.html).

## 11. Inspect CloudWatch and create your own lab alarm

In CloudShell, list the published latency metrics after CDC has started:

```bash
aws cloudwatch list-metrics --namespace AWS/DMS --metric-name CDCLatencyTarget
```

Find the metric for your task/replication instance. Compare it with **DMS → your
task → Monitoring** and record its complete Dimensions array. Metric dimension
values may use internal resource identifiers; do not guess them from display names.
Create `metric-dimensions.json` with `vi` and copy that exact array. It has this
shape, with your observed values:

```json
[
  {"Name":"ReplicationInstanceIdentifier","Value":"YOUR_OBSERVED_INSTANCE_DIMENSION"},
  {"Name":"ReplicationTaskIdentifier","Value":"YOUR_OBSERVED_TASK_DIMENSION"}
]
```

Set a recent time window in CloudShell (GNU date):

```bash
export METRIC_START=$(date -u -d '15 minutes ago' +%Y-%m-%dT%H:%M:%SZ)
```

```bash
export METRIC_END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

Retrieve the actual samples:

```bash
aws cloudwatch get-metric-statistics --namespace AWS/DMS --metric-name CDCLatencyTarget \
  --dimensions file://metric-dimensions.json --start-time "$METRIC_START" --end-time "$METRIC_END" \
  --period 60 --statistics Maximum --query 'sort_by(Datapoints,&Timestamp)'
```

Repeat with `CDCLatencySource` and `CDCIncomingChanges`. Verify that each metric
has the same task dimensions using list-metrics first. Empty output is missing
data, not zero latency. Refresh the time variables when observing a later window.

Create an alarm with no notification action for this exercise:

```bash
aws cloudwatch put-metric-alarm --alarm-name "$LAB-cdc-target-latency" \
  --namespace AWS/DMS --metric-name CDCLatencyTarget --dimensions file://metric-dimensions.json \
  --statistic Maximum --period 60 --evaluation-periods 5 --datapoints-to-alarm 5 \
  --threshold 60 --comparison-operator GreaterThanThreshold --treat-missing-data missing \
  --no-actions-enabled
```

```bash
aws cloudwatch describe-alarms --alarm-names "$LAB-cdc-target-latency" \
  --query 'MetricAlarms[].{Name:AlarmName,State:StateValue,Reason:StateReason}'
```

The initial training threshold is more than 60 seconds for five one-minute
periods; choose production thresholds from measured requirements. It may start
in INSUFFICIENT_DATA until enough samples arrive. With actions disabled, inspect
state in Console; it does not send a notification. Record the alarm name for
cleanup. Do not treat the absence of an alert as proof that a stopped task is healthy.
[AWS alarm creation](https://docs.aws.amazon.com/cli/latest/reference/cloudwatch/put-metric-alarm.html)
and [DMS metrics](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Monitoring.html).

**Checkpoint:** successful endpoint tests, reviewed schema/mappings/settings,
complete full load, no unresolved validation failures, visible CDC operations.
Proceed to [validation and cutover](../06-cutover/build.md). Do not start target
Hydra while DMS is applying changes.
