# A healthy portal hides a failed migration

The source application is working. The instructor stops the DMS task while maintaining a small source workload. Your customer sees successful logins and assumes migration is healthy.

Diagnose the discrepancy using task status, table statistics, metric timestamps, and a source update that does not appear on target. Explain why application availability and replication health are independent.

Recover within the retained binlog window or document why a new full load is necessary. Stop the workload, drain CDC, and reconcile after recovery. Do not mark the scenario complete based only on a resumed task status.

**Deliverable:** a short incident report with source availability, replication gap, recovery action, final validation, and one monitoring improvement.
