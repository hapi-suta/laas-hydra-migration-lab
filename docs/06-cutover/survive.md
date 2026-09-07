# Recover before target writes

Rehearse this on a fresh reset, before target Hydra starts. The instructor introduces a target readiness failure after source fencing but before the first target write.

Keep the source frozen while you diagnose. Check endpoint configuration, TLS, schema state, and required secrets. Decide whether the time budget supports a fix or a return to source service.

If returning to source, keep target stopped, restore source Hydra, restore source gateway selection, and resume traffic only after its health and authentication checks pass. Retain the migration failure evidence for the next run.

**Success:** the customer can identify why this rollback was safe and contrast it with a rollback after PostgreSQL accepted refreshes or new logins. The lab intentionally does not pretend to support automatic reverse replication.
