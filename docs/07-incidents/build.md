# Set up the incident practice session

**Environment:** dedicated local or cloud lab. **Prerequisite:** normal behavior verified and a reset plan available.

## 1. Record your healthy baseline

On **Runner**, as **ec2-user**:

```bash
python3 scripts/lab.py status
```

Confirm which backend is active. These two service incidents are intended for the source-stage lab, not for a completed target-stage cutover.

## 2. Inject a gateway failure

On **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/chaos.py inject gateway-down
```

The command stops only the named practice gateway. Visit the portal through the existing SSM tunnel and record the failure. Check whether source Hydra's readiness endpoint is still reachable from the runner.

Restore the failed service using your diagnosis. If needed, the instructor recovery path is:

On **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/chaos.py recover gateway-down
```

On **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/chaos.py validate gateway-down
```

Require `pass: true`, then verify the actual browser login/refresh flow.

## 3. Rehearse source service failure

On **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/chaos.py inject source-down
```

Observe which pages continue working and which OAuth operations fail. Restore source and validate with the matching scenario name.

## 4. Select cloud migration incidents

Use the earlier SURVIVE pages to rehearse a missing DMS source rule, interrupted task, omitted relationship table, and pre-write cutover abort. Only the two Compose incidents are automated in this initial implementation; the cloud scenarios use explicit instructor-operated changes and recovery steps.

**Evidence:** one report per incident, screenshots of symptoms without tokens, corrective commands, and application-level validation.
