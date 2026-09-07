# Validate and cut over with the Console

**Before starting:** source application works, DMS full load is complete, CDC is
running and target Hydra is stopped. Both paths use the same native SQL and
application commands; the AWS Console controls the migration task.

## 1. Preserve Alice and fence the source

Follow [cutover steps 1-2](build.md): refresh Alice on source, preserve the browser
session, save issuer/public keys, stop source writers and record the binlog position.
Use **EC2 → runner → Connect → Session Manager** for the Docker and SQL commands.
Keep portal running and source Aurora available for DMS to finish reading.

## 2. Inspect DMS completion and validation

1. Open **DMS → Database migration tasks → your task**. Confirm **Running**.
2. Open **Table statistics**. Require all 14 selected tables loaded and no errors.
3. Inspect each table's validation state and counters. Require completed validation
   and zero pending, failed or suspended records. Unsupported validation needs
   another complete check; do not count it as validated.
4. Open **Monitoring** and its CloudWatch metric links. Set a recent time range
   covering the writer fence. Inspect CDCIncomingChanges, CDCLatencySource and
   CDCLatencyTarget over several fresh samples. Require the queue drained.
5. Save screenshots with the metric timestamps and task identity. Inspect task
   logs for apply errors. A low latency number does not prove row equality.
6. Execute [cutover step 4's exact SQL comparisons](build.md#4-compare-exact-table-counts-while-writers-are-frozen)
   in Session Manager. Require matching results while writers remain stopped.

[AWS DMS monitoring](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Monitoring.html)
and [validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html).

## 3. Stop migration apply

1. In **DMS → Database migration tasks**, select only your task.
2. Choose **Actions → Stop** and confirm the task identifier.
3. Wait for **Stopped** and save final table statistics/checkpoint.
4. Keep the task stopped throughout the following target tests.

The equivalent commands are [cutover step 5](build.md#5-stop-dms-apply).

## 4. Check integrity and switch the application

In the runner session, follow [steps 6-8](build.md#6-check-every-target-foreign-key-explicitly):
execute every generated FK query, review/reset owned sequences, start target,
verify readiness, change the two routing files and restart only gateway.
These steps have no RDS/DMS Console button: they operate on SQL and your application.
Every required SQL and Docker command is printed in the linked steps.

## 5. Prove the application works after cutover

Perform [step 9](build.md#9-prove-continuity-and-record-downtime) in the browser:
Alice's existing session/refresh, Bob's new login/refresh/revocation, unchanged
issuer/public keys, and measured downtime. Confirm source and DMS remain stopped.

**Checkpoint:** save actual results for every gate. Target startup can write data;
a simple return to MySQL is unsafe after that boundary.
