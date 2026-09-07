# Load the source and generate CDC traffic

**Environment:** Runner, ec2-user. **Prerequisite:** source portal registration completed. **Checkpoint:** measured data size and zero-error API workload.

## 1. Test a small profile

On **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/scale.py --gib 0.05
```

`--gib` sets the target logical client-data size in GiB. The script prints progress without exposing client credentials. Inspect `evidence/scale.json` and require `meets_goal: true`.

## 2. Exercise real application operations

On **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/workload.py --seconds 120 --workers 2 --rps 4
```

`--seconds` bounds runtime; `--workers` caps concurrency; `--rps` is the total token-cycle rate, not per worker. Additional admin requests occur in some cycles. Require `errors: 0` and nonzero issued, revoked, and client lifecycle counts.

Sign in as Alice and Bob through the portal to populate actual authorization-code, consent, login, and refresh state. Client-credentials traffic alone does not exercise those relationships.

## 3. Build the full-size profile

After the small profile passes and the AWS budget is agreed, on **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/scale.py --gib 35 --full-scale --batch 500
```

`--full-scale` explicitly enables large generation. `--batch` sets rows per committed batch. Run in a durable terminal session on the runner; if interrupted, rerun to continue. Do not start a second copy concurrently.

Require `measured_client_logical_bytes` of at least **37,580,963,840** and `meets_goal: true`. Save generation duration, row count, database CPU, I/O, and free storage. A smaller run is development evidence only.

## 4. Keep activity running during migration

In a separate **Runner** terminal, as **ec2-user**:

```bash
.venv/bin/python scripts/workload.py --seconds 3600 --workers 4 --rps 8
```

This creates a one-hour bounded workload. Choose a longer duration if full load takes longer. Track errors and latency rather than assuming a requested rate is achieved.

Do not run cleanup jobs or upgrade Hydra between inventory and migration. Keep the schema stable.

**Evidence:** scale report, workload counts, a manual browser login/refresh result, elapsed time, and a note stating this is a client/metadata-heavy synthetic profile.
