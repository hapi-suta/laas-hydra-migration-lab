# Assess the schema using the AWS SCT CLI

**Where:** EC2 runner, Session Manager, ec2-user, `/opt/hydra-practice`.
**Before starting:** restore the source and exercise the application in task 2.
The PostgreSQL databases `hydra` and `sct_compare` were created by you in task 2.
Keep target Hydra stopped. [Desktop GUI alternative](console.md).

SCT produces the assessment and conversion. You examine its output in
`sct_compare`. The DMS destination remains `hydra.public`, initialized by the
pinned Hydra PostgreSQL migrations. This separates the schema-conversion lesson
from the application's version-specific database contract.

## 1. Install Java, SCT and both JDBC drivers

On the runner:

```bash
sudo dnf install -y java-17-amazon-corretto-headless unzip
```

```bash
mkdir -p runtime/sct evidence/sct
```

```bash
chmod 700 runtime/sct evidence/sct
```

```bash
curl -fL https://s3.amazonaws.com/publicsctdownload/jars/AWSSchemaConversionToolBatch.jar -o runtime/sct/AWSSchemaConversionToolBatch.jar
```

```bash
curl -fL https://repo.maven.apache.org/maven2/com/mysql/mysql-connector-j/26.7.0/mysql-connector-j-26.7.0.jar -o runtime/sct/mysql.jar
```

```bash
curl -fL https://jdbc.postgresql.org/download/postgresql-42.7.13.jar -o runtime/sct/postgresql.jar
```

```bash
unzip -t runtime/sct/AWSSchemaConversionToolBatch.jar | tail -n 1
```

```bash
unzip -p runtime/sct/AWSSchemaConversionToolBatch.jar META-INF/MANIFEST.MF
```

```bash
sha256sum runtime/sct/*.jar > evidence/sct/downloads.sha256
```

Record Java version with `java -version` and SCT build from the manifest.
The engineering run used SCT build 677, built with Java 17. AWS's general CLI page
still references Corretto 11. The command below reflects the tested build's Java
17 requirement. A locally calculated hash records what you downloaded; it is not
an independent vendor signature verification.
[AWS SCT CLI documentation](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Reference.html),
[JDBC setup](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Installing.JDBCDrivers.html),
[MySQL Connector/J](https://dev.mysql.com/downloads/connector/j/),
[PostgreSQL JDBC](https://jdbc.postgresql.org/download/).

## 2. Build your RDS trust store

Download the public regional CA bundle:

```bash
curl -fL https://truststore.pki.rds.amazonaws.com/us-east-1/us-east-1-bundle.pem -o runtime/sct/rds-region.pem
```

Split the PEM bundle into individual certificates. This awk command copies each
complete certificate to its own file; it does not contact a database:

```bash
awk '/-----BEGIN CERTIFICATE-----/{n++; f=sprintf("runtime/sct/ca-%d.pem",n)} f{print > f} /-----END CERTIFICATE-----/{close(f); f=""}' runtime/sct/rds-region.pem
```

Choose a long alphanumeric trust-store password privately. Avoid apostrophes
and newlines because the later SCT CLI parameter uses single-quoted text. This protects a store containing public
CA certificates, not database passwords:

```bash
read -rsp 'New SCT trust-store password: ' SCT_TRUST_PASSWORD
```

```bash
export SCT_TRUST_PASSWORD
```

Import every regional certificate into a new JKS store:

```bash
for cert in runtime/sct/ca-*.pem; do
  keytool -importcert -noprompt -alias "$(basename "$cert" .pem)" \
    -file "$cert" -keystore runtime/sct/rds-trust.jks -storetype JKS \
    -storepass:env SCT_TRUST_PASSWORD || break
done
```

```bash
keytool -list -keystore runtime/sct/rds-trust.jks -storepass:env SCT_TRUST_PASSWORD
```

Require one trusted entry per downloaded certificate. If an alias exists from an
earlier attempt, inspect the existing store rather than replacing it blindly.
[AWS RDS CA bundles](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/UsingWithRDS.SSL.html).

## 3. Open SCT interactive mode

On the runner:

```bash
java --add-opens=java.base/jdk.internal.loader=ALL-UNNAMED -Xmx2g \
  -Djdk.jar.maxSignatureFileSize=128000000 \
  -jar runtime/sct/AWSSchemaConversionToolBatch.jar -type interactive
```

`-Xmx2g` limits the Java heap. The signature-size setting and module opening were
needed for the tested batch build. They do not disable database TLS verification.
At the **SCT prompt**, enter each command below and its terminating `/` line.
These are SCT commands, not Bash or AWS CLI commands. Values use straight single
quotes. Replace placeholders before submitting. SCT output/project logs can echo
credentials; keep the entire SCT working directory private.

```text
help
/
```

```text
SetGlobalSettings -settings: '{"mysql_driver_file":"/opt/hydra-practice/runtime/sct/mysql.jar","postgresql_driver_file":"/opt/hydra-practice/runtime/sct/postgresql.jar"}' -save: 'true'
/
```

```text
CreateProject -name: 'hydra_assessment' -directory: '/opt/hydra-practice/runtime/sct'
/
```

```text
LoadTrustStore -name: 'RDS' -password: 'YOUR_TRUST_STORE_PASSWORD' -file: '/opt/hydra-practice/runtime/sct/rds-trust.jks'
/
```

Use the `sct_reader` password you created in task 2 and your native writer
endpoint. Runner connections use direct ports, without workstation tunnels:

```text
AddSource -name: 'MYSQL' -vendor: 'MYSQL' -host: 'YOUR_SOURCE_WRITER_ENDPOINT' -port: '3306' -user: 'sct_reader' -password: 'YOUR_SCT_PASSWORD' -useSSL: 'true' -requireSSL: 'true' -verifyServerCertificate: 'true' -trustServerCertificate: 'false' -trustStoreAlias: 'RDS'
/
```

Use the target `hydra` role password from task 2. The SCT CLI vendor token
for this RDS PostgreSQL connection is `POSTGRESQL`. Set the database to
`sct_compare`, on the RDS instance you created:

```text
AddTarget -name: 'POSTGRESQL' -vendor: 'POSTGRESQL' -host: 'YOUR_TARGET_INSTANCE_ENDPOINT' -port: '5432' -database: 'sct_compare' -user: 'hydra' -password: 'YOUR_POSTGRES_HYDRA_PASSWORD' -useSSL: 'true' -requireSSL: 'true' -verifyServerCertificate: 'true' -trustServerCertificate: 'false' -trustStoreAlias: 'RDS'
/
```

Require successful connections with no authentication/TLS errors. Do not continue
on a failed AddSource/AddTarget operation. The exact command parameters are in
[AWS's SCT CLI reference PDF](https://s3.amazonaws.com/publicsctdownload/AWS%20SCT%20CLI%20Reference.pdf).

## 4. Map, assess and export

At the SCT prompt:

```text
AddServerMapping -sourceTreePath: 'Servers.MYSQL' -targetTreePath: 'Servers.POSTGRESQL'
/
```

```text
PrintSourceTreeNodeChildren -treePath: 'Servers.MYSQL'
/
```

Expect the Schemas node. Select only your source hydra schema:

```text
CreateReport -treePath: 'Servers.MYSQL.Schemas.hydra'
/
```

```text
Convert -treePath: 'Servers.MYSQL.Schemas.hydra'
/
```

```text
SaveTargetSQL -treePath: 'Servers.POSTGRESQL.Schemas.hydra' -file: '/opt/hydra-practice/evidence/sct/converted.sql'
/
```

```text
SaveReportPDF -file: '/opt/hydra-practice/evidence/sct/assessment.pdf'
/
```

```text
SaveReportCSV -directory: '/opt/hydra-practice/evidence/sct'
/
```

```text
SaveProject
/
```

```text
quit
```

**Expected:** nonempty report and SQL files. Conversion warnings/errors remain
work to do even if export succeeds. The engineering assessment reported 17 JSON
action items and 12 date/default items. Record your own counts and resolutions.
[AWS assessment reports](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_AssessmentReport.html).

## 5. Review the converted SQL and apply only to the comparison database

Back in the runner shell:

```bash
vi evidence/sct/converted.sql
```

For each action item, locate its table/column and compare it with the catalog
queries in [schema checks](schema-checks.md). Record the original expression,
reviewed replacement and reason in `evidence/sct/decisions.md` using `vi`.
For example, when SCT leaves a MySQL JSON column unresolved, inspect the same
column in the native PostgreSQL target and use that actual JSON/JSONB definition
in the comparison conversion. PostgreSQL supports both types; a generic SCT
warning does not mean otherwise. Do not bulk-replace every JSON or timestamp.

Save the reviewed SQL as `evidence/sct/reviewed.sql`. Inspect every database/schema
name and any DROP statements. It must create objects only in the comparison
database. Reconnect with the PostgreSQL client from task 2, changing only
`dbname=hydra` to `dbname=sct_compare`, using the `hydra` role and its password.
Bind the evidence directory so psql can read the reviewed SQL. In a fresh shell,
first set `export TARGET_HOST=YOUR_TARGET_INSTANCE_ENDPOINT` from your worksheet:

```bash
docker run --rm -it --network host -e PSQL_HISTORY=/dev/null \
  -v "$PWD/runtime/certs:/certs:ro" -v "$PWD/evidence/sct:/review:ro" postgres:17.4 \
  psql "host=$TARGET_HOST port=5432 dbname=sct_compare user=hydra sslmode=verify-full sslrootcert=/certs/global-bundle.pem" -W
```

In **psql**:

```sql
SELECT current_database(),current_user;
\set ON_ERROR_STOP on
BEGIN;
\i /review/reviewed.sql
COMMIT;
\dn
\dt hydra.*
```

Require `sct_compare` before executing the file. If an error occurs, stop and
resolve its action item; do not declare the schema converted because some tables
exist. Run `ROLLBACK;` after an error before retrying the corrected file. Save the
error and corrected SQL. The reviewed RDS rehearsal passed after the
[documented export repairs](schema-checks.md#apply-the-corrections-found-in-the-rds-rehearsal).

Finish the [native schema, LOB and empty-target checks](schema-checks.md). The
real DMS target stays `hydra.public`. Continue to [DMS setup](../05-dms/build.md).
