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

The SCT build 677 assessment against RDS PostgreSQL 17.11 reported 17 JSON-type
action items and 12 date/default review items. The raw export did not apply
until the corrections below were made. Repeat the assessment for your own target.
Use the following inventory as a comparison aid, not as your assessment result.

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

### Apply the corrections found in the RDS rehearsal

Keep the original export. Open a copy named `evidence/sct/reviewed.sql` in your
editor. Make these changes only after comparing your source and native target
catalogs. They describe the tested Hydra v2.2.0 export from SCT build 677.

- For the 17 JSON columns listed above, change SCT's `VARCHAR(8000)` to `JSONB`.
   If a default exists, copy that column's actual native PostgreSQL default.
   An array default is `'[]'::jsonb`; an object default is `'{}'::jsonb`.
   MySQL `_utf8mb4` literals and MySQL backslash quoting cannot be pasted into
   PostgreSQL. Leave columns with no default without a default.
- For the 12 timestamp columns listed above, replace SCT's
   `DEFAULT 'epoch'::TIMESTAMP` with the verified native `DEFAULT now()`.
   The epoch is a fixed historical instant, not the current time.
- Remove each obsolete `WITH (OIDS=FALSE)` table option, retaining the closing
   parenthesis and semicolon. The tested export contained 15 such clauses.
   PostgreSQL 17 does not accept that old table option.
- In `hydra_oauth2_flow`, replace the incorrectly escaped `acr` default with
   `acr TEXT NOT NULL DEFAULT ''`, preserving the comma if another column follows.
   The native target uses an empty string here.
- SCT exported `ADD CONSTRAINT hydra_oauth2_flow_chk null;`. Replace `null`
   with the actual equivalent CHECK expression. Inspect the source in MySQL:

```sql
SELECT constraint_name,check_clause
FROM information_schema.check_constraints
WHERE constraint_schema='hydra';
```

In the **native PostgreSQL hydra database**, get the corresponding definition:

```sql
SELECT conname,pg_get_constraintdef(oid)
FROM pg_constraint
WHERE contype='c' AND conrelid='public.hydra_oauth2_flow'::regclass;
```

Compare the complete conditions: allowed flow states and the fields that must
be non-NULL for each state. In this pinned schema they are equivalent. Copy the
complete returned `CHECK (...)` expression after
`ADD CONSTRAINT hydra_oauth2_flow_chk` in the comparison SQL. Retain the final
semicolon. Do not delete this constraint to get past the syntax error.

### Put the reviewed SQL on the runner

If you used SCT on the runner, your file is already at `evidence/sct/reviewed.sql`; continue to **Apply the reviewed file** below.

If you used SCT desktop, save your edited file as `reviewed.sql` on your workstation. Transfer this SQL file only, not your SCT project or connection logs.

On **Windows**, open PowerShell in the folder containing `reviewed.sql` and run:

```powershell
Get-FileHash .\reviewed.sql -Algorithm SHA256
[Convert]::ToBase64String([IO.File]::ReadAllBytes("$PWD\reviewed.sql")) | Set-Clipboard
```

The first command prints the file's SHA-256 checksum. Save it. The second copies the file as encoded text to your clipboard and normally prints nothing.

On **Linux**, open a workstation terminal in that folder and run:

```bash
sha256sum reviewed.sql
base64 -w0 reviewed.sql
```

Save the checksum and copy the complete encoded line. Then, in your **runner Session Manager shell**, as ec2-user in `/opt/hydra-practice`:

```bash
mkdir -p evidence/sct
chmod 700 evidence/sct
vi evidence/sct/reviewed.sql.b64
```

Press **i**, paste the encoded text, press **Esc**, then type **:wq** and press **Enter**. Decode it and check that the file arrived unchanged:

```bash
base64 -d evidence/sct/reviewed.sql.b64 > evidence/sct/reviewed.sql
sha256sum evidence/sct/reviewed.sql
```

**Expected:** the runner checksum matches the workstation checksum exactly, ignoring letter case. If it differs or decoding fails, correct the transfer before continuing.

### Apply the reviewed file

On the runner, set the target endpoint from your worksheet. This command stores the value in your current terminal; it normally prints nothing:

```bash
export TARGET_HOST=YOUR_TARGET_INSTANCE_ENDPOINT
```

Open the PostgreSQL client against **sct_compare**. The `-v` option makes your reviewed file visible inside the client container:

```bash
docker run --rm -it --network host -e PSQL_HISTORY=/dev/null \
  -v "$PWD/runtime/certs:/certs:ro" -v "$PWD/evidence/sct:/review:ro" postgres:17.4 \
  psql "host=$TARGET_HOST port=5432 dbname=sct_compare user=hydra sslmode=verify-full sslrootcert=/certs/global-bundle.pem" -W
```

Enter the target `hydra` password from task 2. At the **psql prompt**, check the destination first:

```sql
SELECT current_database(),current_user;
```

**Expected:** `sct_compare` and `hydra`. If the database is `hydra`, exit with `\q` and correct the connection. Once the destination is correct, run:

```sql
\set ON_ERROR_STOP on
BEGIN;
\i /review/reviewed.sql
COMMIT;
```

**Expected:** SQL completion messages, including `CREATE TABLE` and `ALTER TABLE`, followed by `COMMIT`, with no `ERROR`. A transaction keeps a failed import from leaving only part of the schema behind. If an error occurs, run `ROLLBACK;`, fix the reviewed file and retry. Keep the error in your notes.

In the same **sct_compare** connection, verify:

```sql
SELECT current_database();
SELECT count(*) AS tables FROM information_schema.tables
WHERE table_schema='hydra' AND table_type='BASE TABLE';
SELECT count(*) AS jsonb_columns FROM information_schema.columns
WHERE table_schema='hydra' AND data_type='jsonb';
SELECT count(*) AS current_time_defaults FROM information_schema.columns
WHERE table_schema='hydra' AND column_default='now()';
SELECT count(*) AS foreign_keys FROM pg_constraint co
JOIN pg_namespace ns ON ns.oid=co.connamespace
WHERE ns.nspname='hydra' AND co.contype='f';
SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint
WHERE contype='c' AND conrelid='hydra.hydra_oauth2_flow'::regclass;
```

The corrected RDS rehearsal returned **15 tables, 17 JSONB columns, 12 now()
defaults, 28 foreign keys**, and the restored flow CHECK. The comparison schema
still illustrates conversion differences such as UUID strings and integer
booleans; the application destination remains its native `hydra.public` schema.
[AWS SCT assessment workflow](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_AssessmentReport.html)
and [PostgreSQL 17 CREATE TABLE syntax](https://www.postgresql.org/docs/17/sql-createtable.html).

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
Continue to [task 4](../lab/04-dms.md) and use this reviewed inventory to check its explicit DMS mappings. An optional checker can supplement these steps;
it cannot replace understanding and resolving a mismatch.
