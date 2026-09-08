# Restore the MySQL source yourself

**Where:** EC2 runner, Session Manager, ec2-user, `/opt/hydra-practice`.
**Before starting:** complete [application setup](../02-aws/application.md).
Your source `hydra` database exists but has **zero tables**. Target Hydra is stopped.
[Console route](console.md).

This is a logical SQL restore into the Aurora MySQL cluster you created. AWS
explains this method in [Logical migration using mysqldump](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Migrating.ExtMySQL.mysqldump.html).
The downloadable fixture contains the pinned Hydra schema and synthetic clients.
It is a training artifact, not a customer backup. SQL expressions expand repeated
synthetic metadata during import. Compressed download size is not database size.

## 1. Choose and download your restore fixture

Use **small** to rehearse a restore. For the complete migration exercise choose
**35g**, which expands to at least 35 GiB of logical client data. Do not import both
into the same database. A small rehearsal requires a separate empty database or
a fresh lab before the full exercise.

On the runner:

```bash
export FIXTURE=hydra-source-demo-35g
```

For a small rehearsal use `export FIXTURE=hydra-source-demo-small` instead. Download
the SQL, checksum and manifest from the published release:

```bash
mkdir -p runtime/restore
```

```bash
curl -fL "https://github.com/hapi-suta/laas-hydra-migration-lab/releases/download/restore-fixtures-v1/$FIXTURE.sql.gz" -o "runtime/restore/$FIXTURE.sql.gz"
```

```bash
curl -fL "https://github.com/hapi-suta/laas-hydra-migration-lab/releases/download/restore-fixtures-v1/$FIXTURE.sha256" -o "runtime/restore/$FIXTURE.sha256"
```

```bash
curl -fL "https://github.com/hapi-suta/laas-hydra-migration-lab/releases/download/restore-fixtures-v1/$FIXTURE.manifest.json" -o "runtime/restore/$FIXTURE.manifest.json"
```

`-f` fails on HTTP errors; `-L` follows the release download redirect. A missing
asset is a stop condition. Do not import an HTML error page or substitute customer data.

```bash
(cd runtime/restore && sha256sum -c "$FIXTURE.sha256")
```

```bash
gzip -t "runtime/restore/$FIXTURE.sql.gz"
```

```bash
cat "runtime/restore/$FIXTURE.manifest.json"
```

**Expected:** checksum `OK`, gzip exits 0, manifest identifies Hydra v2.2.0,
synthetic data, exact row counts and logical bytes. Save the manifest in evidence.
The fixture is dominated by client metadata with Unicode and varied lengths.
The restored schema has OAuth relationships, but real login/token state is
created by you in step 6. Repeated padding makes this unsuitable as a production
storage or throughput benchmark.

Download links, if you want to inspect the release before using the runner:

| Profile | SQL archive | Verification files |
|---|---|---|
| Small, 3,200 clients | [Small SQL](https://github.com/hapi-suta/laas-hydra-migration-lab/releases/download/restore-fixtures-v1/hydra-source-demo-small.sql.gz) | [Checksum](https://github.com/hapi-suta/laas-hydra-migration-lab/releases/download/restore-fixtures-v1/hydra-source-demo-small.sha256), [manifest](https://github.com/hapi-suta/laas-hydra-migration-lab/releases/download/restore-fixtures-v1/hydra-source-demo-small.manifest.json) |
| Full, 2,236,700 clients | [35 GiB SQL](https://github.com/hapi-suta/laas-hydra-migration-lab/releases/download/restore-fixtures-v1/hydra-source-demo-35g.sql.gz) | [Checksum](https://github.com/hapi-suta/laas-hydra-migration-lab/releases/download/restore-fixtures-v1/hydra-source-demo-35g.sha256), [manifest](https://github.com/hapi-suta/laas-hydra-migration-lab/releases/download/restore-fixtures-v1/hydra-source-demo-35g.manifest.json) |

The complete published file was restored into a separate Aurora MySQL database
using the native MySQL client. All table counts and full byte measurements
matched the manifest. Hydra passed its schema and readiness checks and read the
first, middle and last sample clients. See [what has been tested](../validation.md),
and record your own results as you follow the steps below.

## 2. Create a private MySQL client configuration

On the runner, open a private file:

```bash
umask 077
```

```bash
vi runtime/restore/mysql.cnf
```

Enter the following. Replace the host with your **source writer** endpoint and
the password with `MYSQL_PASSWORD` from your `.env`. This account owns the source
schema; do not use the DMS read account.

```ini
[client]
host=YOUR_SOURCE_WRITER_ENDPOINT
port=3306
user=hydra
password=YOUR_MYSQL_HYDRA_PASSWORD
ssl-mode=VERIFY_IDENTITY
ssl-ca=/certs/global-bundle.pem
default-character-set=utf8mb4
```

```bash
chmod 600 runtime/restore/mysql.cnf
```

Check identity, TLS and the empty database using a native MySQL client:

```bash
docker run --rm --network host \
  -v "$PWD/runtime/restore/mysql.cnf:/run/mysql.cnf:ro" \
  -v "$PWD/runtime/certs:/certs:ro" mysql:8.0.41 \
  mysql --defaults-extra-file=/run/mysql.cnf hydra \
  -e "SELECT DATABASE(),CURRENT_USER(); SHOW SESSION STATUS LIKE 'Ssl_cipher'; SELECT COUNT(*) AS tables_before_restore FROM information_schema.tables WHERE table_schema='hydra';"
```

**Expected:** hydra, hydra account, nonempty cipher, **0 tables**. Stop if any
value differs. The native endpoint and `VERIFY_IDENTITY` check the server hostname.
[AWS MySQL TLS client connection](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ConnectToInstanceSSL.CLI.html).

## 3. Import the SQL yourself

Run the restore in tmux so closing Session Manager does not interrupt it:

```bash
sudo dnf install -y tmux
```

```bash
tmux new -s hydra-restore
```

Inside tmux, remain in `/opt/hydra-practice`. Set the fixture name again if needed.
The following command streams the compressed SQL into MySQL. It does not expand
a 35 GiB file onto the runner disk. `pipefail` makes either decompression or import
failure return an error. Do not add `--force`, which would continue after SQL errors.

```bash
set -o pipefail
```

```bash
gzip -dc "runtime/restore/$FIXTURE.sql.gz" | docker run --rm -i --network host \
  -v "$PWD/runtime/restore/mysql.cnf:/run/mysql.cnf:ro" \
  -v "$PWD/runtime/certs:/certs:ro" mysql:8.0.41 \
  mysql --defaults-extra-file=/run/mysql.cnf hydra \
  > evidence/restore.stdout 2> evidence/restore.stderr
```

Immediately record the exit status before running another command:

```bash
printf 'restore_exit=%s\n' "$?" | tee evidence/restore-result.txt
```

**Expected:** `restore_exit=0`. Detach with **Ctrl+B**, then **D** if you need to
leave the terminal while it runs. Reconnect with `tmux attach -t hydra-restore`.
In a second Session Manager terminal, inspect CPU, connections and volume I/O in
**RDS → source writer → Monitoring**. The import may take hours; do not start a
second import because the first appears quiet.

The fixture commits client data in batches of at most 10,000 rows. Earlier
committed batches remain after an interruption; the clean-restore recovery steps
are still required. It temporarily disables foreign-key checks only in its import session,
because table creation order crosses dependencies. Step 4 explicitly checks the
restored relationship. Re-enabling checks does not retroactively validate rows.

## 4. Verify the restore before starting Hydra

Inspect `evidence/restore.stderr`. Any SQL error requires investigation even if
other rows loaded. Open a native MySQL prompt using the same private configuration:

```bash
docker run --rm -it --network host -e MYSQL_HISTFILE=/dev/null \
  -v "$PWD/runtime/restore/mysql.cnf:/run/mysql.cnf:ro" \
  -v "$PWD/runtime/certs:/certs:ro" mysql:8.0.41 \
  mysql --defaults-extra-file=/run/mysql.cnf hydra
```

In the **source MySQL prompt**, run:

The metadata and logical-byte checks read the full dataset. They can take tens
of minutes and show no intermediate output. Leave the query running. You can
check database activity in the RDS **Monitoring** tab while you wait.

```sql
SELECT COUNT(*) AS tables_restored FROM information_schema.tables WHERE table_schema='hydra';
SELECT COUNT(*) AS clients, SUM(OCTET_LENGTH(metadata)) AS metadata_bytes FROM hydra_client;
SELECT COUNT(*) AS networks FROM networks;
SELECT COUNT(*) AS migration_entries FROM schema_migration;
SELECT COUNT(*) AS orphan_clients FROM hydra_client c LEFT JOIN networks n ON c.nid=n.id WHERE n.id IS NULL;
SELECT COUNT(*) AS signing_keys FROM hydra_jwk;
SELECT COUNT(*) AS access_tokens FROM hydra_oauth2_access;
SELECT COUNT(*) AS refresh_tokens FROM hydra_oauth2_refresh;
```

**Expected:** 15 tables; clients and metadata bytes exactly match the manifest;
1 network; 206 migration entries; zero orphan clients, signing keys and tokens.
For the full fixture, expect **2,236,700 clients** and **36,894,597,160 metadata bytes**.
Inspect the manifest for the other empty tables. Before starting Hydra, obtain
an exact logical client-byte measurement using the catalog to include every column:

```sql
SET SESSION group_concat_max_len=1048576;
SELECT CONCAT('SELECT SUM(',GROUP_CONCAT(CONCAT('COALESCE(OCTET_LENGTH(`',column_name,'`),0)') ORDER BY ordinal_position SEPARATOR '+'),') AS client_logical_bytes FROM hydra_client') INTO @measure_sql FROM information_schema.columns WHERE table_schema='hydra' AND table_name='hydra_client';
SELECT @measure_sql;
PREPARE measure_statement FROM @measure_sql;
EXECUTE measure_statement;
DEALLOCATE PREPARE measure_statement;
```

Match `expected_client_logical_bytes` in the manifest. For the full exercise,
expect **37,582,389,656 bytes**, which exceeds the required **37,580,963,840 bytes**
(35 GiB). This is logical column content, not
allocated Aurora volume size. Save counts and measurements without row payloads.
Exit MySQL with `exit`.

## 5. Start the source application explicitly

On the runner, first check that the restored migration history is compatible
with the pinned binary. The migration container must exit 0:

```bash
docker compose run --rm migrate-source
```

Then start only the intended services. `--no-deps` prevents Compose from repeating
initialization or starting another backend through dependency traversal:

```bash
docker compose up -d --no-deps source portal gateway
```

```bash
curl -fsS http://127.0.0.1:4445/health/ready
```

```bash
curl -fsS http://127.0.0.1:8080/ -o /dev/null -w '%{http_code}\n'
```

**Expected:** readiness succeeds and portal returns 200. If not, inspect
`docker compose ps` and `docker compose logs --tail=50 source portal gateway`.
Do not print `.env` or full container environment in shared evidence.

## 6. Create actual OAuth state through the browser

Return to **your laptop** for this step. Leave the runner's browser terminal
available in another tab. You will open a private connection from your laptop to
the app on the runner. Run the command for your laptop's operating system below.
Replace `YOUR_RUNNER_INSTANCE_ID` with the EC2 instance ID from your worksheet.

### On your Mac: Terminal

```bash
aws ssm start-session --profile hydra-lab --region us-east-1 --target YOUR_RUNNER_INSTANCE_ID \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["8080"],"localPortNumber":["8080"]}'
```

<details class="instructions" markdown="1">
<summary>Alternative for a Windows laptop: PowerShell</summary>

Open a new PowerShell window. Create a folder for the connection settings and
write the JSON file shown below. It contains port numbers, not credentials.

```powershell
New-Item -ItemType Directory -Force -Path "$HOME\hydra-lab-notes" | Out-Null
Set-Location "$HOME\hydra-lab-notes"
'{"portNumber":["8080"],"localPortNumber":["8080"]}' | Set-Content -Encoding ascii -Path portal-tunnel.json
```

```powershell
aws ssm start-session --profile hydra-lab --region us-east-1 --target YOUR_RUNNER_INSTANCE_ID --document-name AWS-StartPortForwardingSession --parameters file://portal-tunnel.json
```

</details>

**Expected:** the terminal reports the session and waits for connections. Leave
it open. If your login expired, run `aws sso login --profile hydra-lab` and try
again. If your organization supplied another CLI login method, use that method
and its assigned profile instead.

On **the same laptop**, open a new browser tab and browse to
**http://localhost:8080**. The app runs in AWS; the tunnel makes it reachable at
this local address. Use this exact
hostname because it is the configured OAuth issuer and callback URL.

If the browser connection resets after an idle period, inspect this terminal.
Session Manager may report that the forwarding session timed out. Rerun the same
forwarding command after it exits, then reload the browser. Reconnecting the
tunnel preserves the portal's existing session; restarting the portal does not.

1. Confirm **Active backend: source**.
2. Select **Sign in**, choose **Alice**, and continue through consent.
3. Open **Protected account**. Confirm **Verified by source** and Alice's subject.
4. Select **Refresh existing token**. Confirm it remains Alice on source.
5. In a separate private browser window, sign in as **Bob** and refresh once.
6. Use **Revoke token and sign out** for Bob. Leave Alice's browser open.
7. Repeat the MySQL token-table counts. Explain which tables are now populated.

The application generates its own signing keys and token records. Do not copy
keys or tokens into your report. Retest Alice shortly before cutover because a
long restore/assessment session can outlast token expiry.

**Checkpoint:** successful restore log, matching manifest counts/bytes, zero
orphans, source readiness, Alice/Bob login and refresh. Continue to
[SCT assessment](../04-sct/build.md). You will create visible CDC changes in
[task 4](../05-dms/use.md) after starting your migration task.

The portal verifies revocation by retrying the revoked refresh token. In the tested
Hydra v2.2.0 run, Hydra returned HTTP 401 with `token_inactive`. This is an expected
rejection for that test. A generic authentication failure such as `invalid_client`
does not pass the revocation check.
