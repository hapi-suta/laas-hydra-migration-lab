# Research and implementation decisions

Reviewed 7 September 2026. This is an engineering decision log; successful
execution is recorded separately in the validation report.

## What the rehearsal must prove

Hydra supports SQL-backed persistence and initializes its schema through explicit
application migrations. Its database holds security-sensitive state, including
client records and token signatures. A row-count-only migration demonstration is
insufficient: the rehearsal also checks a pre-existing access token, refresh token,
new login, revocation, and the stable issuer URL.
[Ory's runnable OAuth server example](https://www.ory.com/blog/run-oauth2-server-open-source-api-security)
and [production guidance](https://www.ory.com/docs/hydra/self-hosted/production).

The implementation pins Hydra 2.2.0 for the first reproducible exercise. Its native
MySQL and PostgreSQL migrations produced 14 corresponding data tables in our local
test. Preserve `networks` and the original network IDs as well as `hydra_*` rows.
Retain each engine's native `schema_migration` history. Matching column names are
only the starting point: inspect type, nullability, keys, defaults, and semantics.
This schema decision is based on the pinned application's source and observed
schemas, not a claim that SCT output is always identical to application migrations.
[Pinned Hydra source](https://github.com/ory/hydra/tree/v2.2.0).

## Schema conversion and data movement

Use SCT to create an actual assessment and converted SQL. Apply the converted
result to the separate `sct_compare` database, then compare it to the native Hydra
PostgreSQL schema used by the application. This preserves a useful SCT learning
exercise while making discrepancies visible before data movement. SCT provides
a command-line workflow for project creation, connections, mappings, conversion,
and report export, suitable for the runner.
[SCT CLI reference](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Reference.html).

AWS's 2022 engineering example demonstrates that workflow on Amazon Linux. Its
Oracle-specific conversion rules are not reused for MySQL; only the documented
CLI process informs this implementation.
[AWS SCT CLI engineering walkthrough](https://aws.amazon.com/blogs/database/convert-database-schemas-and-application-sql-using-the-aws-schema-conversion-tool-cli/).

The migration is **Aurora MySQL to Amazon RDS for PostgreSQL**, matching the
customer's corrected requirement and original diagram. The practice target is a
Single-AZ PostgreSQL 17.x DB instance. Students discover an available minor
version and class in their region. The earlier engineering target used Aurora
PostgreSQL; its provisioning, SCT and DMS endpoint results do not establish RDS
target compatibility. Re-run those checkpoints against the new target.
[AWS RDS PostgreSQL creation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_CreateDBInstance.html)
and [SCT RDS PostgreSQL target selection](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_GettingStarted.SCT.html).

## Source capture and network

Connect DMS to the Aurora MySQL writer, enable row-based binlogs with full row
images, and retain binlogs long enough for the planned outage/recovery window.
The lab starts with 72 hours and verifies the setting. DMS source permissions are
separate from application and SCT access. Do not treat an Aurora read endpoint as
an interchangeable CDC source.
[AWS MySQL source prerequisites](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.MySQL.html).

The baseline uses private VPC peering and native database endpoints, so it does not
need an internet-facing NLB. Both database clients and DMS validate the RDS CA and
endpoint hostname. An arbitrary DNS alias can break hostname validation. The
single-account practice topology does not prove cross-account IAM or the customer's
EKS deployment; those remain explicit extensions.
[DMS network configurations](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_ReplicationInstance.VPC.html)
and [DMS TLS modes](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Security.SSL.html).

## Target preparation and integrity

Initialize the native PostgreSQL schema, keep target Hydra stopped, and verify that
every selected data table is empty. Use `DO_NOTHING` to preserve that schema.
Disable the three source-DDL propagation flags separately; table preparation mode
alone is not a DDL policy.
[DMS DDL handling](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TaskSettings.DDLHandling.html).

DMS sessions bypass foreign-key triggers during loading using
`session_replication_role=replica`. Application sessions retain normal constraint
behavior. After stopping replication, explicitly check for orphan rows and repair
owned sequence values before application writes. Merely enabling triggers again
does not retroactively check rows loaded while triggers were disabled. JSON is
handled as a LOB internally for heterogeneous migration, so measure actual maximum
column sizes and fail on truncation.
[AWS PostgreSQL target guidance](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.PostgreSQL.html).

DMS uses dedicated endpoint secrets rather than RDS-managed master credentials.
The student retrieves managed master credentials privately and creates SQL users explicitly. Endpoint roles receive
access to the two lab DMS secrets, and a private Secrets Manager endpoint serves
the replication instance.
[AWS endpoint secret authentication](https://docs.aws.amazon.com/dms/latest/userguide/security_iam_secretsmanager.html).

## Scale, validation, and cutover

AWS recommends both a small proof of concept and a full-size rehearsal. Start with
a small fixture, then measure at least 35 GiB of logical values without counting
indexes or Aurora storage overhead. The baseline volume profile is intentionally
client-metadata-heavy, with separate API-created OAuth flows and ongoing token/
client changes. It is not a measured production distribution. Capture table counts,
LOB sizes, load duration, CDC latency and database/DMS resource pressure.
[AWS DMS best practices](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_BestPractices.html).

At cutover, stop all source writers, prove CDC drain, compare exact counts and complete row-level validation, stop DMS, and then allow target application writes. Reuse the same
issuer and configured cryptographic secrets. Exercise retained and new sessions.
Once the target has accepted new writes, switching back to the old source can lose
those writes; reverse migration is a separate procedure, not an automatic rollback.
[DMS validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html)
and [monitoring](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Monitoring.html).

## Costs and evidence limits

Estimate Aurora MySQL and RDS PostgreSQL separately in the
[AWS Pricing Calculator](https://calculator.aws/). The old two-Aurora-writer
estimate does not apply to this topology. Include the RDS instance deployment
option, gp3 allocated storage, any additional IOPS/throughput, backups, DMS,
runner, interface endpoints and IPv4. Autoscaling can increase allocated storage
and cost; the worksheet records both its initial value and ceiling. A deadline
tag does not stop billing. Verify retained resources after teardown.
Local container checks, configuration validation and a completed AWS migration
remain separate evidence; none substitutes for another.
