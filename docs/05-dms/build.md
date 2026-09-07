# Configure and run the DMS task

**Environment:** Runner for database grants; Laptop with sandbox AWS credentials for DMS control. **Prerequisite:** reviewed mappings, compatible schema, passing LOB and empty-target checks.

## 1. Establish migration permissions

On **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/cloud.py grants
```

This creates source replication credentials, target DML/control-schema permissions, and the DMS-session parameter grant. It stores new credentials directly in the Terraform-created Secrets Manager entries. Do not rerun during a task: doing so rotates the passwords.

Verify source binlog configuration and the 72-hour retention set during bootstrap. Freeze schema deployments for the exercise.

## 2. Move non-secret setup artifacts to the operator workspace

Your **Laptop** project needs the same `runtime/cloud.json`, `runtime/table-mappings.json`, `evidence/lob-check.json`, and reviewed inventory as the runner. These contain configuration and schema evidence, not passwords. Transfer them through your approved instructor file-transfer method, or copy their contents using `vi`. Do not copy `.env` or `runtime/databases.json` to the public repository.

## 3. Create and test endpoints

On **Laptop**, as **your user**, with the sandbox profile selected:

```bash
.venv/bin/python scripts/cloud.py endpoints
```

The script imports the RDS CA bundle, creates source and target endpoints using Secrets Manager, and selects `verify-full`. It writes endpoint ARNs to `runtime/dms.json`. If endpoints already exist, it preserves them; inspect their configuration for drift before reuse.

On **Laptop**, as **your user**:

```bash
.venv/bin/python scripts/cloud.py test-endpoints
```

On **Laptop**, as **your user**:

```bash
.venv/bin/python scripts/cloud.py status
```

Wait until **both** connection states are `successful`. A `testing` state is not a pass. Investigate IAM, TLS, routes, and database grants for failures.

## 4. Create the migration task

Review `migration/task-settings.json`. Confirm exact mappings, `DO_NOTHING`, all three DDL-handling flags false, 64 KiB limited LOB mode, row validation, control schema, and stop-on-error policies.

On **Laptop**, as **your user**:

```bash
.venv/bin/python scripts/cloud.py create-task
```

This creates a full-load-and-CDC task but does not start it. Verify it is ready and inspect its actual endpoint configuration in AWS.

On **Laptop**, as **your user**:

```bash
.venv/bin/python scripts/cloud.py start
```

Use this only for the initial start. Recovery uses an explicitly selected `resume-processing` action in AWS; reloading a target is a different operation and requires a fresh reconciliation plan.

## 5. Monitor while application activity continues

Keep the bounded workload running on **Runner**. On **Laptop**, as **your user**:

```bash
.venv/bin/python scripts/cloud.py status
```

Save `evidence/dms-status.json`. Require full-load completion for every selected table, no table errors, and validation progress. In CloudWatch, graph `CDCLatencySource`, `CDCLatencyTarget`, CDC incoming changes, CPU, memory, swap, and available storage.

Do not start target Hydra while DMS is applying changes. Use the validation and cutover module for the handoff.
