# Diagnose a stopped migration task

Use a small dedicated incident rehearsal before the full-size timed run. Follow the [student stop/resume exercise](../07-incidents/build.md#3-stop-and-resume-cdc-from-its-checkpoint) while source application activity continues briefly within the binlog retention window.

First distinguish a deliberately stopped task from a running task with lag. Record its recovery checkpoint, last failure message, and table states. Verify that the required binary logs still exist before resuming.

Resume processing using the AWS console's recovery action. Do not choose reload-target reflexively: the prepared target may already contain data and the task uses `DO_NOTHING`.

**Validation:** task running, backlog draining, no suspended tables, subsequent update/delete visible on target, and final reconciliation after fencing writers. If the required logs are gone, document the need for a new full load instead of claiming a resume succeeded.
