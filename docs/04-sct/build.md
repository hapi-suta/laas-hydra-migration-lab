# Assess with SCT and prepare the target

**Choose your interface:** the CLI steps are below. For click-by-click instructions, use the [AWS Console / GUI path](console.md).

**Environment:** Runner for schema inspection; Laptop for SCT. **Prerequisite:** both native schemas initialized, target Hydra stopped.

## 1. Capture the actual schema inventory

On **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/inventory.py
```

The script queries both databases and writes `evidence/inventory.json`. Read every table, primary key, exclusion, and source/target column type. Investigate missing keys or mismatched column sets. Preserve the source network ID and associated rows.

## 2. Connect SCT to the private databases

Install SCT and the JDBC drivers using the official vendor instructions in Sources. The target comparison database `sct_compare` was created by bootstrap.

On **Laptop**, as **your user**, open a dedicated MySQL tunnel. Replace the runner ID and native source endpoint with your Terraform outputs:

```bash
aws ssm start-session --target i-REPLACE --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters '{"host":["SOURCE.cluster-REPLACE.us-east-1.rds.amazonaws.com"],"portNumber":["3306"],"localPortNumber":["13306"]}'
```

In a second **Laptop** terminal, as **your user**, open the target tunnel:

```bash
aws ssm start-session --target i-REPLACE --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters '{"host":["TARGET.cluster-REPLACE.us-east-1.rds.amazonaws.com"],"portNumber":["5432"],"localPortNumber":["15432"]}'
```

The remote-host document connects from the runner to the named private endpoint. Keep both sessions open. Stop local database containers first if they occupy those laptop ports.

Create an SCT project with MySQL source and Aurora PostgreSQL target. Configure the source at `127.0.0.1:13306` and target comparison database at `127.0.0.1:15432`, database `sct_compare`. Retrieve only the dedicated lab credentials privately; do not place them in the site or reports. Use TLS with the RDS CA bundle. Local tunnel hostnames do not match the RDS certificate: configure supported CA verification for this SCT tunnel, or use native-hostname resolution with a correctly configured tunnel. Do not disable certificate checking to conceal a mismatch. Hydra and DMS use direct native endpoints with hostname verification.

## 3. Produce the assessment and conversion

In SCT, select source database `hydra`, create the assessment report, and review every action item. Export the report and converted SQL into your private evidence directory. Apply conversion only to `sct_compare` after checking the target connection.

Compare the SCT result with the native `hydra.public` schema. Create a worksheet with columns: object, source definition, SCT result, native Hydra definition, chosen mapping, reason, and validation query. Resolve discrepancies before migration.

## 4. Approve the inventory and generate mappings

On **Runner**, as **ec2-user**:

```bash
vi evidence/inventory.json
```

Set `reviewed` to `true` only after the review. Do not change `column_match` to hide a real mismatch; correct the underlying schema decision and regenerate inventory.

On **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/mappings.py
```

This creates exact selection rules and a `hydra` → `public` schema transformation in `runtime/table-mappings.json`.

On **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/lob_check.py
```

Require `pass: true` in `evidence/lob-check.json`. The scan can take time on the large dataset.

Hydra's native migrations seed a `networks` row even when its server has never
started. In this disposable target, remove that seed so the source network row can
be loaded. Keep target Hydra stopped. The helper refuses to clear a target that
contains application data or multiple networks.

On **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/target_check.py prepare --disposable-target --hydra-stopped
```

On **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/target_check.py empty
```

Require every selected target data table to be empty. Preserve migration bookkeeping. If target Hydra already seeded data, restore a fresh target or use an instructor-reviewed cleanup; `DO_NOTHING` does not empty tables for you.

**Evidence:** SCT report, conversion SQL, reviewed discrepancy worksheet, inventory, mappings, passing LOB scan, and empty-target check.
