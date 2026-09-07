# Install the application and create database users

**Where:** EC2 runner via Session Manager. **Before starting:** finish either the
[Console infrastructure steps](console.md) or [AWS CLI steps](build.md). You need
your two writer endpoints and the two RDS-managed master secret ARNs. No app,
SQL users, schemas, CA store or runtime configuration is assumed to exist.

## 1. Connect and install the packages

**Console:** EC2 → Instances → select your runner → Connect → Session Manager →
Connect. **CLI alternative**, in your authenticated workstation terminal:

```bash
aws ssm start-session --region us-east-1 --target YOUR_RUNNER_INSTANCE_ID
```

The CLI requires the [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html).
In the opened runner session, execute:

```bash
sudo dnf install -y docker git python3-pip openssl
```

```bash
sudo systemctl enable --now docker
```

```bash
sudo mkdir -p /usr/local/lib/docker/cli-plugins
```

```bash
sudo curl -fL https://github.com/docker/compose/releases/download/v2.35.1/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
```

```bash
sudo chmod 755 /usr/local/lib/docker/cli-plugins/docker-compose
```

```bash
sudo usermod -aG docker ec2-user
```

```bash
sudo install -d -m 0755 -o ec2-user -g ec2-user /opt/hydra-practice
```

```bash
sudo su - ec2-user
```

```bash
cd /opt/hydra-practice
```

```bash
docker version
```

```bash
docker compose version
```

**Expected:** Docker client and server information, and Compose v2.35.1. Switching
to a fresh ec2-user login activates its Docker group membership. If Docker says
permission denied, check `id` and open a fresh login; do not make its socket world-writable.
[AWS Session Manager sessions](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html).

## 2. Download and inspect the application source

```bash
git clone https://github.com/hapi-suta/laas-hydra-migration-lab.git .
```

```bash
git rev-parse HEAD
```

```bash
sed -n '1,180p' compose.cloud.yaml
```

```bash
sed -n '1,120p' app/nginx.conf
```

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -r requirements.txt
```

```bash
mkdir -p runtime/certs evidence
```

```bash
chmod 700 runtime evidence
```

```bash
curl -fL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem \
  -o runtime/certs/global-bundle.pem
```

```bash
chmod 755 runtime/certs
```

```bash
chmod 644 runtime/certs/global-bundle.pem
```

Record your commit ID. The downloaded files provide the demo application's code
and container definitions. You will issue the SQL, Docker and AWS commands
explicitly; no deployment/bootstrap helper is required. Public CA material must
be readable by the container UID; credential files remain private.
[AWS RDS certificates](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/UsingWithRDS.SSL.html)
and [Hydra database setup](https://www.ory.com/docs/hydra/self-hosted/dependencies-environment).

## 3. Create your own private application configuration

Generate six independent random values and save them directly to `.env`:

```bash
umask 077
```

```bash
printf 'MYSQL_PASSWORD=%s\n' "$(openssl rand -hex 24)" > .env
```

```bash
printf 'POSTGRES_PASSWORD=%s\n' "$(openssl rand -hex 24)" >> .env
```

```bash
printf 'HYDRA_SYSTEM_SECRET=%s\n' "$(openssl rand -hex 24)" >> .env
```

```bash
printf 'HYDRA_COOKIE_SECRET=%s\n' "$(openssl rand -hex 24)" >> .env
```

```bash
printf 'PORTAL_CLIENT_SECRET=%s\n' "$(openssl rand -hex 24)" >> .env
```

```bash
printf 'SCT_PASSWORD=%s\n' "$(openssl rand -hex 24)" >> .env
```

```bash
vi .env
```

Add these three lines, replacing only the host placeholders with your worksheet
values. Keep the generated passwords for the SQL user-creation steps below:

```text
MYSQL_HOST=YOUR_SOURCE_WRITER_ENDPOINT
POSTGRES_HOST=YOUR_TARGET_WRITER_ENDPOINT
COMPOSE_FILE=compose.cloud.yaml
```

Create the initial routing files. Keep the upstream file readable by nginx:

```bash
printf '{"active":"source"}\n' > runtime/active.json
```

```bash
printf 'upstream hydra_active { server source:4444; }\n' > runtime/upstream.conf
```

```bash
chmod 600 .env runtime/active.json
```

```bash
chmod 644 runtime/upstream.conf
```

`HYDRA_SYSTEM_SECRET` and `HYDRA_COOKIE_SECRET` are shared by the source and target
Hydra containers. Keep them and the issuer unchanged across the database cutover.
Do not regenerate `.env` once you have created OAuth sessions.
[Ory production configuration](https://www.ory.com/docs/hydra/self-hosted/production).

## 4. Connect to the source using its managed administrator password

**Console:** RDS → Databases → source cluster → Configuration → Master credentials
ARN → Secrets Manager → Retrieve secret value. Privately obtain `labadmin` and its
password. This is your source master secret; the target has a different one.

**AWS CLI equivalent**, in CloudShell, only when you need the credential for the
interactive prompt below:

```bash
aws secretsmanager get-secret-value --secret-id YOUR_SOURCE_MASTER_SECRET_ARN \
  --query SecretString --output text
```

This command displays a secret. Do not include its output in evidence or screen
recordings. Prefer Console retrieval when sharing your terminal. Back on the
runner, set the non-secret endpoint variable, then open the MySQL client:

```bash
export SOURCE_HOST=YOUR_SOURCE_WRITER_ENDPOINT
```

```bash
docker run --rm -it --network host -e MYSQL_HISTFILE=/dev/null \
  -v "$PWD/runtime/certs:/certs:ro" mysql:8.0.41 \
  mysql --host="$SOURCE_HOST" --port=3306 --user=labadmin --password \
  --ssl-mode=VERIFY_IDENTITY --ssl-ca=/certs/global-bundle.pem hydra
```

Enter the master password when prompted. `VERIFY_IDENTITY` validates the CA and
native hostname. Do not use a reader endpoint. In the SQL prompt:

```sql
SELECT VERSION(), DATABASE(), CURRENT_USER();
SHOW SESSION STATUS LIKE 'Ssl_cipher';
SELECT @@global.binlog_format, @@global.binlog_row_image,
       @@global.require_secure_transport, @@session.foreign_key_checks;
CALL mysql.rds_set_configuration('binlog retention hours',72);
CALL mysql.rds_show_configuration;
```

**Expected:** hydra database, nonempty cipher, ROW, FULL, secure transport enabled,
foreign_key_checks=1, retention=72. If binlog values differ, check the cluster
parameter group/reboot status before generating any data.
[AWS MySQL DMS prerequisites](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.MySQL.html).

Create the two source users. Replace each placeholder inside the quotes with the
corresponding generated value from your private `.env`; never use the literal
placeholder as a password:

```sql
CREATE USER 'hydra'@'%' IDENTIFIED BY 'MYSQL_PASSWORD_FROM_YOUR_ENV';
GRANT ALL PRIVILEGES ON hydra.* TO 'hydra'@'%';
CREATE USER 'sct_reader'@'%' IDENTIFIED BY 'SCT_PASSWORD_FROM_YOUR_ENV';
GRANT SELECT, SHOW VIEW ON *.* TO 'sct_reader'@'%';
SHOW GRANTS FOR 'hydra'@'%';
SHOW GRANTS FOR 'sct_reader'@'%';
exit
```

Hydra owns its application schema; SCT has metadata/read access. DMS receives a
separate account in Module 05. If a user already exists, investigate whether you
are reusing an old lab rather than blindly rotating its password.
[AWS SCT MySQL privileges](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Source.MySQL.html).

## 5. Connect to PostgreSQL and create its schema owner

Retrieve the **target** RDS master secret through the same Console path, or use
`aws secretsmanager get-secret-value` with your target secret ARN. On the runner:

```bash
export TARGET_HOST=YOUR_TARGET_WRITER_ENDPOINT
```

```bash
docker run --rm -it --network host -e PSQL_HISTORY=/dev/null \
  -v "$PWD/runtime/certs:/certs:ro" postgres:17.4 \
  psql "host=$TARGET_HOST port=5432 dbname=hydra user=labadmin sslmode=verify-full sslrootcert=/certs/global-bundle.pem" -W
```

Enter the target master password. In psql:

```sql
SELECT version(),current_database(),current_user;
SELECT ssl,version,cipher FROM pg_stat_ssl WHERE pid=pg_backend_pid();
CREATE ROLE hydra LOGIN;
\password hydra
```

At both password prompts, enter `POSTGRES_PASSWORD` from your `.env`. Then:

```sql
GRANT hydra TO labadmin;
GRANT CONNECT ON DATABASE hydra TO hydra;
ALTER SCHEMA public OWNER TO hydra;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE DATABASE sct_compare OWNER hydra;
\l
\q
```

**Expected:** TLS=true; `hydra` and `sct_compare` databases exist. Explicit role
membership lets the administrator create an object owned by hydra on the tested
PostgreSQL release; omitting it caused `must be able to SET ROLE hydra`.
`sct_compare` is the safe destination for examining SCT's converted schema.
[AWS PostgreSQL target guidance](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.PostgreSQL.html)
and [SCT target privileges](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Source.MySQL.html).

## 6. Initialize only the native PostgreSQL target schema

Inspect `migrate-target` in `compose.cloud.yaml`. It executes
`hydra migrate sql -e --yes` against your target database. On **Runner**, as
**ec2-user**, in `/opt/hydra-practice`:

```bash
docker compose pull migrate-target source gateway
```

On **Runner**, as **ec2-user**:

```bash
docker compose run --rm migrate-target
```

Require **Successfully applied migrations** and exit status 0. Keep target Hydra
stopped. Do not initialize the MySQL source tables here: you will restore the
supplied schema and data into that empty database in Module 03.

On **Runner**, as **ec2-user**:

```bash
docker compose build portal
```

## 7. Check the empty MySQL destination for your restore

Reconnect to the source MySQL client from step 4. In the **MySQL source prompt**,
as **hydra or labadmin**, run:

```sql
SELECT COUNT(*) AS tables_before_restore
FROM information_schema.tables WHERE table_schema='hydra';
```

Expected: **0**. An existing populated source is not a fresh restore destination.
Do not overwrite a previous lab. Stop here and identify the correct empty cluster.

Exit the SQL client. Continue to [restore the MySQL data yourself](../03-data/build.md).
That lesson starts the application after the restore and its checks pass.

**Evidence:** your commit/version record, TLS and binlog queries, source/target
grants, successful native PostgreSQL migration, and zero MySQL tables before
restore. Continue to [restore MySQL and start Hydra](../03-data/build.md).
