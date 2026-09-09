# Migration practice path

Use this shorter path only when the AWS environment has already been created
for you, or when you are repeating the migration after completing the full
build. It does not replace the main sandbox setup. You do not create VPCs,
security groups, EC2, RDS or DMS from this page.

The migration you practise is **Aurora MySQL → Amazon RDS for PostgreSQL**.
SCT reviews the database design. DMS moves the rows and follows new changes.
The application is switched only after the data checks pass.

## Before you start

Before using this path, collect the following values from the person who
prepared the environment. If this is your first run in your personal sandbox,
return to [Start the full AWS build](start.md). Keep passwords in the approved
secret store, never in this worksheet or a screenshot.

| Check | What you need |
|---|---|
| Source | Aurora MySQL writer endpoint, port 3306, database name and SCT/DMS user |
| Target | RDS PostgreSQL DB instance endpoint, port 5432, database name and target user |
| Network | A workstation or runner that can reach both private endpoints |
| TLS | The approved RDS CA bundle and trust-store instructions |
| Data | Confirmation that the Hydra source data has been restored |
| Application | Hydra and the practice portal URL, plus the cutover owner |
| Access | AWS Console/CLI permissions for SCT, DMS, RDS and CloudWatch |

Stop here if any row is missing. A database endpoint that you cannot reach is
not ready for migration practice.

## 1. Prove the starting point

Open the portal and sign in as Alice. Record **Active backend: source** and
**Verified by source**. From the runner or approved workstation, test TLS login
to both databases. The target should contain the native Hydra schema and no
migrated application rows yet.

**Expected:** the application works on Aurora MySQL, both database connections
work, and the target is safe to receive data.

## 2. Assess the schema with SCT

Use the [SCT desktop path](04-sct/mac-desktop.md) if you want a graphical
assessment, or the [SCT CLI path](04-sct/build.md) from the Linux runner. Create
the comparison database specified by your platform owner. Do not apply SCT SQL
to the live application database.

Record every action item, review the converted SQL and compare it with Hydra's
native PostgreSQL schema. Pay special attention to UUIDs, booleans, JSON, time
defaults, keys, indexes and large values.

**Expected:** the assessment is saved, every important conversion decision is
explained, and the reviewed SQL works in the comparison database.

## 3. Prepare and start DMS

Follow the [DMS Console procedure](05-dms/console.md) first, then use the
[CLI procedure](05-dms/build.md) if you want to repeat it with commands.
Create source and target endpoints with TLS, select only the Hydra tables,
keep the target schema DDL under your control and choose full load plus CDC.

Start the task and watch the table statistics. Do not call full load complete
until every selected table has finished.

**Expected:** all selected tables load without errors and the task reaches CDC.

## 4. Exercise live changes

While CDC is running, create one controlled test change through the application
or the approved SQL procedure. Find that change in PostgreSQL. Repeat with an
update and a delete if the exercise owner allows it.

**Expected:** each change appears in the target and the DMS CDC latency remains
within the agreed practice limit.

## 5. Validate and cut over

Use the [cutover procedure](lab/05-cutover.md). Stop source writers, wait for
CDC to drain, compare counts and checksums, check foreign keys and sequences,
then stop DMS. Switch Hydra to the RDS PostgreSQL endpoint only after the
cutover owner approves the evidence.

**Expected:** the portal returns with **Active backend: target** and
**Verified by target**.

## 6. Prove the application and record the result

Refresh Alice's existing session. Sign in as Bob. Revoke Bob's token and prove
that the revoked token is rejected. Record the migration time, DMS task result,
validation evidence, cutover decision and rollback boundary.

If your company has not supplied the environment and you need to build it for
yourself, use the separate [full AWS build path](start.md) instead.
