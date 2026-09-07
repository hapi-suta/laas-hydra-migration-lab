# Recover when the source works but CDC has stopped

Use [the stop/resume exercise](build.md#3-stop-and-resume-cdc-from-its-checkpoint).
The source portal can continue issuing tokens while DMS is stopped. Check task
status, last successful checkpoint, metric timestamps, errors and source binlog
retention. Do not infer replication health from a working login.

Resume only while the required binlogs remain available. Prove the missing client
arrives, finish update/delete checks, drain CDC and rerun validation. If the logs
expired, record the gap and rebuild a fresh migration baseline.
