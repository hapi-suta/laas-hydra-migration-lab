# Cutover is a controlled handoff of writers

A safe migration needs an identifiable last source write and a clear first target write. While both applications can write independently, there is no single authoritative database and one-way DMS replication cannot merge their histories.

Fence the application writers, background workers, and data generators. Drain in-flight transactions and capture the final source position. Let DMS apply all remaining changes, validate every selected table, and retain the final checkpoint and observations.

Reconciliation in this lab compares all selected columns in every row. It uses exact counts and a canonical SHA256 aggregate that normalizes reviewed JSON, boolean, time, and binary representations. It is bounded in memory but scans the entire dataset. Compare on a stable dataset, not while an application is still updating it.

PostgreSQL foreign keys bypassed by the DMS session need explicit orphan checks. Sequences, if present, must be moved past migrated values before new inserts. Then DMS must stop cleanly before target Hydra becomes the writer.

The gateway preserves the issuer URL and selects the active deployment. Existing browser sessions survive only if the migrated state and configuration agree. Refresh the same session you created on MySQL; a new login alone would miss lost refresh-token state.

Before target writes, rollback can return to the frozen source. After target writes, MySQL is stale. The project has no reverse replication. A post-write rollback requires a separately tested reconciliation or recovery method and an agreed data-loss decision. A switch-source command is routing, not such a recovery method.
