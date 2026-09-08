# Recover from a failed restore

| Symptom | Inspect | Recovery |
|---|---|---|
| Checksum mismatch | Download URL, filename, checksum output | Delete only the failed download and download it again. Do not import it. |
| Connection timeout | Source SG, runner SG, subnet routes, writer endpoint | Repair the specific route or rule from task 1. Retest TLS before importing. |
| Access denied | Client username and password, grants from task 2 | Correct the private client file. Use the schema owner, not dms_repl. |
| Table already exists | Empty-database check, earlier restore logs | Stop. Identify the prior attempt. Never add --force to conceal it. |
| Session disconnected | `tmux ls` and restore log | Reattach to the existing job. Do not run a second import. |
| SQL error or interrupted import | First error in restore.stderr, row counts | Treat the database as partially restored. Restart only into a clean destination. |

For a failed attempt in **your disposable source only**, stop source, portal and
gateway first with `docker compose stop source portal gateway`. Confirm the
writer hostname against your worksheet. Connect as the source administrator
using [task 2's MySQL connection](../02-aws/application.md#4-connect-to-the-source-using-its-managed-administrator-password).
Do not run this reset on a customer or completed migration source.

In that MySQL prompt, inspect `SELECT DATABASE(),@@hostname;` and `SHOW TABLES;`.
After deciding to discard this failed practice import, execute:

```sql
DROP DATABASE hydra;
CREATE DATABASE hydra CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON hydra.* TO 'hydra'@'%';
```

The drop permanently removes this practice schema. Preserve your failure evidence
first. Run the restore lesson again from its zero-table check. If you have already
started DMS, stop here and use a new lab: resetting a live CDC source invalidates
its migration baseline.

**Recovery evidence:** original error, identified cause, successful clean import,
matching counts/bytes and a new application login.
