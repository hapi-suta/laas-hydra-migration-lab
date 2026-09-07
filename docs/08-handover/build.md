# Package evidence and clean up the lab

**Choose your interface:** the CLI steps are below. For click-by-click instructions, use the [AWS Console / GUI path](console.md).

**Environment:** Laptop and Runner. **Prerequisite:** cutover and incident exercises complete, or an explicit decision to abandon this disposable run.

## 1. Write the handover report

On **Runner**, as **ec2-user**:

```bash
vi evidence/handover.md
```

Record the exact versions, dataset size/profile, selected tables, full-load duration, CDC catch-up time, interruption window, errors encountered, corrective actions, and acceptance results. Link the JSON reports in your private evidence directory. Include the post-write rollback limitation.

## 2. Repeat the critical path

Use a new lab name or an instructor-approved snapshot reset. Run the customer instructions from the beginning and compare outcomes. The second attempt should not depend on undocumented commands from the first.

## 3. Stop application activity

On **Runner**, as **ec2-user**:

```bash
python3 scripts/lab.py stop
```

This preserves data and stops practice containers. Export the non-secret evidence you need before terminating the runner.

## 4. Remove manually created DMS objects

In the sandbox AWS console, stop the named practice task and wait for `stopped`. Delete that task, its two endpoints, and the imported practice certificate after saving the evidence. These objects were created in the DMS lesson and are not managed by Terraform.

Verify each ARN against `runtime/dms.json` and the project tag. Do not delete another customer's tasks or shared service roles.

## 5. Review and execute Terraform teardown

On **Laptop**, as **your user**:

```bash
vi infra/terraform.tfvars
```

Set `deletion_protection=false` only for this disposable lab. On **Laptop**, as **your user**:

```bash
terraform -chdir=infra plan -out=cleanup-prep.tfplan
```

Review that the plan only disables deletion protection for the intended clusters. On **Laptop**, as **your user**:

```bash
terraform -chdir=infra apply cleanup-prep.tfplan
```

On **Laptop**, as **your user**:

```bash
terraform -chdir=infra plan -destroy -out=destroy.tfplan
```

`-destroy` produces a deletion plan without executing it. Verify all resources belong to this lab and the final snapshot names do not conflict with older retained snapshots.

On **Laptop**, as **your user**:

```bash
terraform -chdir=infra apply destroy.tfplan
```

The stack retains final database snapshots and schedules endpoint-secret deletion with a recovery window. Review remaining snapshots, endpoint secrets, logs, and storage charges in AWS. Record what remains and who will remove it when retention expires.

**Gate:** evidence archived privately, compute stopped/deleted as intended, remaining storage documented, and no unrelated resources changed.
