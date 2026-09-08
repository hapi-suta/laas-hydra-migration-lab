# Diagnose migration failures in the Console

**Environment:** AWS Console plus runner Session Manager. **CLI equivalent:**
[Incident exercises](build.md). Work on one assigned lab and one failure at a
time. Capture the healthy baseline before injection; recover fully before the
next exercise. You perform these exercises in your own disposable lab before cutover.

## Case 1. Source connectivity is lost

**Controlled injection:** before cutover, stop the DMS task and record its healthy
endpoint test. In **EC2 → Security Groups → source-db → Inbound rules → Edit**,
record and temporarily remove only the TCP 3306 rule whose source is the lab's
DMS SG. Keep the runner rule. Record the exact rule so you can restore it.

**Observe:** in **DMS → Endpoints → source → Connections**, run the test against
your replication instance. Require failure. Compare the reported error with the
source Aurora writer's Available status: database health does not prove network
reachability. Inspect peering Active state, both route tables, and the missing SG
rule. Do not widen access to the internet.

**Recover:** restore exactly the recorded SG rule, retest both endpoints until
successful, then resume the task from its checkpoint. Inspect table errors,
validation and CDC catch-up. Record recovery time and actual cause.

## Case 2. A DMS task stops unexpectedly

**Controlled injection:** use **DMS → task → Actions → Stop** during CDC while
source test traffic continues for a bounded period. Record the stop time.

**Observe:** inspect **Task details** for status/stop reason, **Table statistics**,
and its **CloudWatch logs**. Distinguish an operator stop from a database error.
Inspect source binlog retention and elapsed downtime before deciding to resume.

**Recover:** choose **Actions → Restart/Resume → Resume processing**. Do not choose
reload/restart-from-beginning. Require queue drain, no table failures and successful
reconciliation after writers are fenced. If the required binlog is no longer
available, a resume cannot recover missing changes: rebuild the migration target
through the explicit fresh-target process.

## Case 3. Target lag or resource pressure

Repeat the explicit client and browser operations from task 4 for a bounded interval. In
**CloudWatch → Metrics → DMS**, compare CPU, freeable memory, swap/free storage,
incoming changes and target latency. Compare the target DB instance's RDS metrics over
the same interval. Record dimensions, units and statistic.

Reduce the workload to its baseline and observe whether lag drains. Investigate
long transactions, LOB handling, indexes and instance capacity before resizing.
If you decide a larger instance is needed within your lab budget, stop the task,
choose the replication instance's **Modify** action, and select the reviewed size.
Wait for Available and recheck endpoint/task health after the modification. Do not conceal lag by disabling validation.

## Case 4. TLS endpoint test fails

Inspect **DMS → Endpoints → endpoint details**. Confirm `verify-full`, the correct
CA certificate, and the native writer hostname stored in the selected secret.
Compare with **RDS → cluster → Connectivity & security**. Common causes include
a stale CA, incorrect endpoint or hostname alias. Correct the configuration and
retest. Disabling certificate validation is not recovery evidence.

## Case 5. Data validation reports a mismatch

In **Table statistics**, find the failed table and inspect its validation status.
Use the native SQL comparison queries through Session Manager to narrow the column
type or row-count problem. Inspect LOB maximum size, booleans, UUIDs, timestamp
precision, JSON mapping and errors in the task logs. Do not copy token values or
private row payloads into the incident report.

Keep target Hydra stopped. Fix the underlying mapping or preparation defect, then
choose a documented reload/fresh-target path and rerun downstream checks. Never
edit a validation report or reduce its selection to make the migration pass.

**Incident record:** expected behavior, observed evidence, cause, exact correction,
recovery verification, elapsed time, and restored baseline settings.
