# Full load and continuous change capture

Full load copies existing rows. CDC reads committed changes from the source binary log and applies them to PostgreSQL. DMS needs the source writer, row-format binlogs, a full row image, sufficient retention, private connectivity, and independent source/target permissions.

The provided task uses `DO_NOTHING` because native Hydra migrations own the application schema. Separate DDL handling settings disable source table alterations, drops, and truncations. A source schema freeze is still required; ignoring DDL while the source changes schema is not a safe migration strategy.

Foreign keys are implemented using triggers on PostgreSQL. Loading related tables concurrently can violate them before parent rows arrive. This lab gives the DMS session permission to set `session_replication_role=replica` through its endpoint connection script. Application sessions do not receive that setting. Explicit post-load foreign-key checks are mandatory because bypassed checks are not retroactively enforced automatically.

DMS receives application-table DML grants and permission to create diagnostic objects in `awsdms_control`. It does not own Hydra's schema. The target user setup is a live-validation checkpoint, particularly the Aurora permission to set the replication-role parameter.

Strict error handling stops the task for data, truncation, and apply errors. This is intentional for teaching: silently continuing past a missing row would undermine the evidence. Validation is enabled and must be inspected at the table level.

Watch both source and target latency, incoming changes, table errors, validation failures, and replication instance memory/storage. A low lag value does not prove that a failed table was migrated. Save task and table statistics as well as the final application results.
