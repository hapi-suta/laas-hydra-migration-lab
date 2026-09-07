# Plan the migration before creating resources

This orientation creates no resources. Your complete AWS build begins in Module
02. You do not need a local prebuilt lab or an instructor's deployment.

## 1. Draw the two data paths

Draw the source application writing to Aurora MySQL. Add SCT's read connection
to MySQL and conversion connection to the separate PostgreSQL comparison database.
Add DMS's MySQL binlog read and PostgreSQL apply connections. Finally draw the
application's PostgreSQL route after cutover.

Use [the architecture concepts](concepts.md) to label ports, TLS, network routes,
security groups and the difference between assessment, full load and CDC.

## 2. Fill in your starting worksheet

Follow [Before you begin](../start.md). Record your assigned account, region,
new prefix, two nonoverlapping CIDRs, two available AZs, tool versions, budget and
cleanup date. Every later resource ID is added to this same worksheet.

## 3. Explain the application proof

The demo portal is a login/consent client for real open-source Hydra. You restore
the synthetic schema/data into MySQL, start Hydra and create actual OAuth state.
After migration you must refresh the same pre-cutover Alice session, then perform
a new Bob login and revocation against PostgreSQL.

The lab uses Hydra v2.2.0 on both engines. Changing Hydra version at the same time
as the database would add a separate variable. Confirm the customer's release
before treating this baseline as a customer migration plan.

**Checkpoint:** your worksheet and an explanation of how you will prove session
continuity. Continue to [Console infrastructure setup](../02-aws/console.md) or
[the AWS CLI build](../02-aws/build.md).
