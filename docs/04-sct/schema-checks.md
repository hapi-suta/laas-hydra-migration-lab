# Inspect schemas and prepare the real DMS target

**Where:** MySQL and PostgreSQL clients on your runner. Both Console and CLI
learners perform these SQL checks. Open the TLS clients from [application setup](../02-aws/application.md).
SCT connects to `sct_compare`; DMS writes to the native `hydra.public` schema.
Do not confuse those two PostgreSQL databases.

## 1. List the source tables, columns and primary keys

In **MySQL**, database hydra:

```sql
SELECT table_name,table_type FROM information_schema.tables
WHERE table_schema='hydra' ORDER BY table_name;
SELECT table_name,column_name,column_type,is_nullable,column_default
FROM information_schema.columns WHERE table_schema='hydra'
ORDER BY table_name,ordinal_position;
SELECT table_name,column_name,ordinal_position
FROM information_schema.key_column_usage
WHERE table_schema='hydra' AND constraint_name='PRIMARY'
ORDER BY table_name,ordinal_position;
SHOW CREATE TABLE hydra_client;
SHOW CREATE TABLE hydra_oauth2_flow;
SHOW CREATE TABLE networks;
```

In **PostgreSQL**, database hydra:

```sql
SELECT current_database();
SELECT table_name,column_name,data_type,udt_name,is_nullable,column_default
FROM information_schema.columns WHERE table_schema='public'
ORDER BY table_name,ordinal_position;
SELECT tc.table_name,kcu.column_name,kcu.ordinal_position
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
USING (constraint_catalog,constraint_schema,constraint_name)
WHERE tc.table_schema='public' AND tc.constraint_type='PRIMARY KEY'
ORDER BY tc.table_name,kcu.ordinal_position;
\d+ public.hydra_client
\d+ public.hydra_oauth2_flow
\d+ public.networks
```

Record column names, types, nullability, defaults, keys and indexes for each table.
A matching table name alone is insufficient. The tested v2.2.0 inventory contains
these data tables:

- `hydra_client`
- `hydra_jwk`
- `hydra_oauth2_access`
- `hydra_oauth2_authentication_session`
- `hydra_oauth2_code`
- `hydra_oauth2_flow`
- `hydra_oauth2_jti_blacklist`
- `hydra_oauth2_logout_request`
- `hydra_oauth2_obfuscated_authentication_session`
- `hydra_oauth2_oidc`
- `hydra_oauth2_pkce`
- `hydra_oauth2_refresh`
- `hydra_oauth2_trusted_jwt_bearer_issuer`
- `networks`

The source `schema_migration` table is bookkeeping, not migrated application data.
Preserve the target's native migration history. A `hydra_%` selection misses
`networks`; that breaks relationships even if the other rows copied successfully.
[AWS table mapping rules](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TableMapping.SelectionTransformation.Selections.html)
and [Ory versioned schema source](https://github.com/ory/hydra/tree/v2.2.0).

## 2. Work through the SCT action items rather than accepting them blindly

SCT build 677 in the engineering assessment reported 17 JSON-type action items
and 12 date/default review items. Those are observations for the pinned source,
not results you can assume for your own version. Generate your own report.

| Object/type | What to compare | Decision to verify |
|---|---|---|
| MySQL JSON | SCT converted column versus native PostgreSQL JSON/JSONB | Use the native Hydra target type; inspect arrays/objects and canonical values |
| tinyint boolean fields | Native PostgreSQL boolean | Require source values only 0/1/NULL where applicable |
| char/varchar UUID IDs | Native UUID columns and FK columns | Check parseable UUIDs and preserve original network/client IDs |
| timestamps/defaults | Precision, timezone assumptions and zero-date defaults | Use native target definitions and test boundary values |
| indexes and composite PKs | Columns, ordering and uniqueness | Preserve lookup behavior and DMS row identity |
| CHECK constraints | Source condition versus native target condition | Inspect SCT export warnings; do not silently drop checks |
| sequences | Whether the native column owns a sequence | Reset applicable sequences after DMS before target writes |

The SCT report's JSON wording is a tool conversion limitation; PostgreSQL does
support JSON and JSONB. In the target client's `sct_compare` database you can
verify that directly with `SELECT '{"a":1}'::jsonb;`. Resolve the flagged column's
conversion using its actual native Hydra definition, not that generic wording.

For the tested v2.2.0 schema, these are the 17 MySQL JSON columns flagged by the
SCT assessment. Confirm them with your own catalog output before using this
reference; keep each column's actual nullability/default as well as its type.

| Table | Column | Source | Native PostgreSQL |
|---|---|---|---|
| `hydra_client` | `redirect_uris` | MySQL JSON | `jsonb` |
| `hydra_client` | `grant_types` | MySQL JSON | `jsonb` |
| `hydra_client` | `response_types` | MySQL JSON | `jsonb` |
| `hydra_client` | `audience` | MySQL JSON | `jsonb` |
| `hydra_client` | `allowed_cors_origins` | MySQL JSON | `jsonb` |
| `hydra_client` | `contacts` | MySQL JSON | `jsonb` |
| `hydra_client` | `request_uris` | MySQL JSON | `jsonb` |
| `hydra_client` | `post_logout_redirect_uris` | MySQL JSON | `jsonb` |
| `hydra_oauth2_flow` | `oidc_context` | MySQL JSON | `jsonb` |
| `hydra_oauth2_flow` | `context` | MySQL JSON | `jsonb` |
| `hydra_oauth2_flow` | `session_access_token` | MySQL JSON | `jsonb` |
| `hydra_oauth2_flow` | `session_id_token` | MySQL JSON | `jsonb` |
| `hydra_oauth2_flow` | `requested_scope` | MySQL JSON | `jsonb` |
| `hydra_oauth2_flow` | `requested_at_audience` | MySQL JSON | `jsonb` |
| `hydra_oauth2_flow` | `amr` | MySQL JSON | `jsonb` |
| `hydra_oauth2_flow` | `granted_scope` | MySQL JSON | `jsonb` |
| `hydra_oauth2_flow` | `granted_at_audience` | MySQL JSON | `jsonb` |

For example, inspect `hydra_client.redirect_uris` in both catalogs. In the SCT
comparison SQL, resolve its unsupported type to `jsonb` because that is what the
native Hydra target uses. Preserve the default's JSON array value with a valid
PostgreSQL expression such as `'[]'::jsonb` **only if your actual native definition
has that default**. Recheck nullability and each related action item before applying.
Do not use this example as a blanket default for all JSON columns.

The same assessment flagged these date defaults (action 8825). The reference
below comes from the actual local v2.2.0 schemas. `None` means no default in the
catalog, not a SQL string to paste. Query your own schemas and compare before
editing the SCT comparison SQL.

| Column | MySQL default | Native PostgreSQL default |
|---|---|---|
| `hydra_client.created_at` | `CURRENT_TIMESTAMP` | `now()` |
| `hydra_client.updated_at` | `CURRENT_TIMESTAMP` | `now()` |
| `hydra_jwk.created_at` | `CURRENT_TIMESTAMP` | `now()` |
| `hydra_oauth2_access.requested_at` | `CURRENT_TIMESTAMP` | `now()` |
| `hydra_oauth2_code.requested_at` | `CURRENT_TIMESTAMP` | `now()` |
| `hydra_oauth2_flow.requested_at` | `CURRENT_TIMESTAMP` | `now()` |
| `hydra_oauth2_jti_blacklist.expires_at` | `CURRENT_TIMESTAMP` | `now()` |
| `hydra_oauth2_oidc.requested_at` | `CURRENT_TIMESTAMP` | `now()` |
| `hydra_oauth2_pkce.requested_at` | `CURRENT_TIMESTAMP` | `now()` |
| `hydra_oauth2_refresh.requested_at` | `CURRENT_TIMESTAMP` | `now()` |
| `hydra_oauth2_trusted_jwt_bearer_issuer.created_at` | `CURRENT_TIMESTAMP` | `now()` |
| `hydra_oauth2_trusted_jwt_bearer_issuer.expires_at` | `CURRENT_TIMESTAMP` | `now()` |

A valid-looking timestamp literal is not automatically a suitable application
default. Preserve the native target behavior, check timezone/precision, and test
new application writes after migration. Do not replace every date default with
`now()` or accept MySQL zero dates in PostgreSQL.

Create a worksheet: **object / source definition / SCT proposed definition /
native Hydra definition / chosen mapping / reason / verification query**.
Complete each migration-relevant item before starting DMS.
[AWS assessment reports](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_AssessmentReport.html)
and [AWS PostgreSQL target behavior](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.PostgreSQL.html).

## 3. Measure LOB sizes across the actual source schema

In **MySQL**, this catalog query builds one MAX byte-length check for every
character, JSON and binary column in the data tables, with one aggregate scan per table. It reads data but changes
no tables. Inspect the generated SQL before executing it:

```sql
SET SESSION group_concat_max_len=1000000;
SELECT GROUP_CONCAT(table_sql SEPARATOR ' UNION ALL ') INTO @lob_sql
FROM (
 SELECT CONCAT('SELECT ',QUOTE(table_name),' AS table_name,JSON_OBJECT(',
 GROUP_CONCAT(CONCAT(QUOTE(column_name),',MAX(OCTET_LENGTH(`',
 REPLACE(column_name,'`','``'),'`))') ORDER BY ordinal_position SEPARATOR ','),
 ') AS column_maxima FROM `hydra`.`',REPLACE(table_name,'`','``'),'`') AS table_sql
 FROM information_schema.columns
 WHERE table_schema='hydra' AND table_name<>'schema_migration'
 AND data_type IN ('char','varchar','tinytext','text','mediumtext','longtext',
                  'json','binary','varbinary','tinyblob','blob','mediumblob','longblob')
 GROUP BY table_name
) AS per_table;
SELECT @lob_sql;
PREPARE lob_check FROM @lob_sql;
EXECUTE lob_check;
DEALLOCATE PREPARE lob_check;
```

Each result is a table name and a JSON object of column names and their maximum
byte lengths. Record the largest value and owning column. Empty columns return
NULL. This lab's proposed DMS limited-LOB setting is 64 KiB; every relevant value
must fit. If one exceeds 65,536 bytes, revise LOB mode/size before loading. Repeat
this check after restoring the full dataset. Do not infer row size from Aurora
allocated storage.
[AWS LOB support](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.LOBSupport.html).

## 4. Inspect target row counts before removing its native seed

Keep target Hydra stopped. In the runner shell verify:

```bash
docker compose ps -a
```

In **PostgreSQL hydra**, begin a transaction and lock the selected tables to
prevent a concurrent writer during preparation:

```sql
BEGIN;
LOCK TABLE
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
  public.networks
IN ACCESS EXCLUSIVE MODE;
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
SELECT 'networks' AS table_name,COUNT(*) AS row_count FROM public.networks;
```

**Expected before DMS:** every application table has zero rows; `networks` can
contain exactly one row inserted by Hydra's native migration. If any other table
has rows, or networks has more than one, execute `ROLLBACK;` and investigate.
Do not use TRUNCATE CASCADE to conceal a populated target.

Only when that expected empty/one-seed state is confirmed, execute:

```sql
SELECT id,created_at FROM public.networks;
DELETE FROM public.networks;
COMMIT;
```

Run the count query again; every selected table must now be zero. Preserve
`public.schema_migration`. DMS will load the **source** network ID and all its
relationships. `DO_NOTHING` does not clear a target on your behalf.

## 5. Save your gate evidence

Keep your source/target inventory, SCT assessment/converted SQL, completed
comparison worksheet, LOB maxima, target counts and stopped-target observation.
Then write the [explicit DMS mappings](../05-dms/build.md#7-write-and-review-the-exact-table-mappings)
from this reviewed inventory. An optional checker can supplement these steps;
it cannot replace understanding and resolving a mismatch.
