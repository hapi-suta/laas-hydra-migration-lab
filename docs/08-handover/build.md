# Save evidence and remove your lab with the AWS CLI

**Where:** runner for the report; CloudShell for AWS deletion commands.
**Before starting:** decide this named disposable lab is finished and save the
evidence you need. Deletion permanently removes resources. Verify every ID against
your own worksheet and account before executing it. [Console alternative](console.md).

## 1. Record the outcome

On the runner, as ec2-user, open `vi evidence/handover.md`. Record:

- Your account, region, lab prefix, guide commit and exact engine/tool versions.
- Restore fixture checksum, exact restored counts/bytes and restore duration.
- SCT action items, reviewed SQL and mapping decisions.
- DMS settings, endpoint tests, full-load duration and final validation status.
- CDC insert/update/delete proof, writer fence, downtime and continuity results.
- Failures, corrections, unresolved gaps and the post-write recovery boundary.
- Resources to delete and any final snapshots/logs intentionally retained.

Keep reports private. Copy needed text reports from Session Manager to your
workstation before terminating the runner. Do not copy `.env`, credential files,
SCT raw logs, cookies, tokens or database row dumps into shared evidence.
Stop the practice containers on the runner:

```bash
docker compose --profile target stop
```

## 2. Verify identity and restore your cleanup worksheet

In CloudShell, set `AWS_REGION`, `LAB` and the IDs recorded during Modules 02/05.
Use your actual values; do not derive another learner's IDs by selecting the first
returned resource. Run:

```bash
aws sts get-caller-identity
```

```bash
aws rds describe-db-clusters --db-cluster-identifier "$LAB-source" --query 'DBClusters[0].{ID:DBClusterIdentifier,Endpoint:Endpoint,Members:DBClusterMembers,Tags:TagList}'
```

```bash
aws rds describe-db-clusters --db-cluster-identifier "$LAB-target" --query 'DBClusters[0].{ID:DBClusterIdentifier,Endpoint:Endpoint,Members:DBClusterMembers,Tags:TagList}'
```

```bash
aws ec2 describe-instances --instance-ids "$RUNNER_ID" --query 'Reservations[].Instances[].{ID:InstanceId,Tags:Tags,Volumes:BlockDeviceMappings}'
```

Expected: only the two clusters and one runner in your worksheet. If you created
readers or extra disks during extensions, inventory those dependencies too.

## 3. Delete DMS task, endpoints, instance and certificate

If the task is running, stop it first. If already stopped, skip the stop command:

```bash
aws dms stop-replication-task --replication-task-arn "$TASK_ARN"
```

```bash
aws dms wait replication-task-stopped --filters Name=replication-task-arn,Values="$TASK_ARN"
```

Save final statistics, then delete:

```bash
aws dms delete-replication-task --replication-task-arn "$TASK_ARN"
```

```bash
aws dms wait replication-task-deleted --filters Name=replication-task-arn,Values="$TASK_ARN"
```

```bash
aws dms delete-endpoint --endpoint-arn "$SOURCE_ENDPOINT"
```

```bash
aws dms delete-endpoint --endpoint-arn "$TARGET_ENDPOINT"
```

```bash
aws dms delete-replication-instance --replication-instance-arn "$DMS_ARN"
```

```bash
aws dms wait replication-instance-deleted --filters Name=replication-instance-arn,Values="$DMS_ARN"
```

```bash
aws dms delete-replication-subnet-group --replication-subnet-group-identifier "$LAB-dms"
```

```bash
aws dms delete-certificate --certificate-arn "$DMS_CA"
```

If teardown starts before a task was ever created, skip only nonexistent objects
and record that fact. Do not turn every error into an ignored result.
[AWS delete DMS task](https://docs.aws.amazon.com/cli/latest/reference/dms/delete-replication-task.html)
and [delete replication instance](https://docs.aws.amazon.com/cli/latest/reference/dms/delete-replication-instance.html).

## 4. Delete writers and clusters, retaining final snapshots

Disable deletion protection on each named cluster:

```bash
aws rds modify-db-cluster --db-cluster-identifier "$LAB-source" --no-deletion-protection --apply-immediately
```

```bash
aws rds modify-db-cluster --db-cluster-identifier "$LAB-target" --no-deletion-protection --apply-immediately
```

Verify `DeletionProtection` is false with `describe-db-clusters`. The baseline has
one writer per cluster. Delete those instances first:

```bash
aws rds delete-db-instance --db-instance-identifier "$SOURCE_WRITER_ID" --skip-final-snapshot
```

```bash
aws rds wait db-instance-deleted --db-instance-identifier "$SOURCE_WRITER_ID"
```

```bash
aws rds delete-db-instance --db-instance-identifier "$TARGET_WRITER_ID" --skip-final-snapshot
```

```bash
aws rds wait db-instance-deleted --db-instance-identifier "$TARGET_WRITER_ID"
```

The writer deletion skips an instance snapshot; Aurora recovery is retained by
the **cluster snapshots** below. Choose a unique suffix for this teardown:

```bash
export SNAPSHOT_SUFFIX=$(date -u +%Y%m%d%H%M%S)
```

```bash
aws rds delete-db-cluster --db-cluster-identifier "$LAB-source" --no-skip-final-snapshot --final-db-snapshot-identifier "$LAB-source-final-$SNAPSHOT_SUFFIX"
```

```bash
aws rds delete-db-cluster --db-cluster-identifier "$LAB-target" --no-skip-final-snapshot --final-db-snapshot-identifier "$LAB-target-final-$SNAPSHOT_SUFFIX"
```

```bash
aws rds wait db-cluster-deleted --db-cluster-identifier "$LAB-source"
```

```bash
aws rds wait db-cluster-deleted --db-cluster-identifier "$LAB-target"
```

Record the final snapshots and their retention deadline. They continue to incur
storage charges. Keep them until you deliberately decide the recovery copies are
no longer needed. RDS manages deletion of its managed master secrets; inspect the
result instead of deleting unrelated secrets.
[AWS deleting Aurora clusters](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/USER_DeleteCluster.html).

## 5. Remove runner, dedicated secrets and database groups

```bash
aws ec2 terminate-instances --instance-ids "$RUNNER_ID"
```

```bash
aws ec2 wait instance-terminated --instance-ids "$RUNNER_ID"
```

Check the root EBS volume recorded in step 2 is gone. Remove separately created
lab volumes only after recording their IDs and deciding their contents are no
longer needed. Schedule dedicated endpoint-secret deletion with a recovery window:

```bash
aws secretsmanager delete-secret --secret-id "$SOURCE_SECRET" --recovery-window-in-days 7
```

```bash
aws secretsmanager delete-secret --secret-id "$TARGET_SECRET" --recovery-window-in-days 7
```

```bash
aws rds delete-db-subnet-group --db-subnet-group-name "$LAB-source"
```

```bash
aws rds delete-db-subnet-group --db-subnet-group-name "$LAB-target"
```

```bash
aws rds delete-db-cluster-parameter-group --db-cluster-parameter-group-name "$LAB-mysql"
```

```bash
aws rds delete-db-cluster-parameter-group --db-cluster-parameter-group-name "$LAB-pg"
```

[AWS secret deletion recovery window](https://docs.aws.amazon.com/secretsmanager/latest/userguide/manage_delete-secret.html).

## 6. Remove the endpoint and security-group dependencies

```bash
aws ec2 delete-vpc-endpoints --vpc-endpoint-ids "$SECRETS_VPCE"
```

Wait for its network interfaces to disappear. Inspect both VPCs:

```bash
aws ec2 describe-network-interfaces --filters Name=vpc-id,Values="$SOURCE_VPC","$TARGET_VPC" --query 'NetworkInterfaces[].{ID:NetworkInterfaceId,Description:Description,Status:Status}'
```

Require no remaining lab service ENIs before deleting SGs/subnets. Do not manually
delete requester-managed RDS/DMS ENIs to bypass a dependency error. Remove the
five rules you created, then their groups:

```bash
aws ec2 revoke-security-group-ingress --group-id "$SOURCE_SG" --protocol tcp --port 3306 --source-group "$RUNNER_SG"
```

```bash
aws ec2 revoke-security-group-ingress --group-id "$SOURCE_SG" --protocol tcp --port 3306 --source-group "$DMS_SG"
```

```bash
aws ec2 revoke-security-group-ingress --group-id "$TARGET_SG" --protocol tcp --port 5432 --source-group "$RUNNER_SG"
```

```bash
aws ec2 revoke-security-group-ingress --group-id "$TARGET_SG" --protocol tcp --port 5432 --source-group "$DMS_SG"
```

```bash
aws ec2 revoke-security-group-ingress --group-id "$SECRETS_SG" --protocol tcp --port 443 --source-group "$DMS_SG"
```

```bash
aws ec2 delete-security-group --group-id "$SOURCE_SG"
```

```bash
aws ec2 delete-security-group --group-id "$TARGET_SG"
```

```bash
aws ec2 delete-security-group --group-id "$RUNNER_SG"
```

```bash
aws ec2 delete-security-group --group-id "$DMS_SG"
```

```bash
aws ec2 delete-security-group --group-id "$SECRETS_SG"
```

## 7. Remove your network

```bash
aws ec2 delete-vpc-peering-connection --vpc-peering-connection-id "$PEER"
```

```bash
aws ec2 delete-subnet --subnet-id "$SOURCE_A"
```

```bash
aws ec2 delete-subnet --subnet-id "$SOURCE_B"
```

```bash
aws ec2 delete-subnet --subnet-id "$RUNNER_SUBNET"
```

```bash
aws ec2 delete-subnet --subnet-id "$TARGET_A"
```

```bash
aws ec2 delete-subnet --subnet-id "$TARGET_B"
```

Subnet deletion removes its explicit route-table association. Delete only the
three custom route tables; VPC deletion handles its default resources:

```bash
aws ec2 delete-route-table --route-table-id "$SOURCE_RT"
```

```bash
aws ec2 delete-route-table --route-table-id "$TARGET_RT"
```

```bash
aws ec2 delete-route-table --route-table-id "$RUNNER_RT"
```

```bash
aws ec2 detach-internet-gateway --internet-gateway-id "$IGW" --vpc-id "$SOURCE_VPC"
```

```bash
aws ec2 delete-internet-gateway --internet-gateway-id "$IGW"
```

```bash
aws ec2 delete-vpc --vpc-id "$SOURCE_VPC"
```

```bash
aws ec2 delete-vpc --vpc-id "$TARGET_VPC"
```

[AWS VPC deletion dependencies](https://docs.aws.amazon.com/vpc/latest/userguide/delete-vpc.html).

## 8. Remove only your dedicated IAM roles

```bash
aws iam remove-role-from-instance-profile --instance-profile-name "$LAB-runner" --role-name "$LAB-runner"
```

```bash
aws iam delete-instance-profile --instance-profile-name "$LAB-runner"
```

```bash
aws iam detach-role-policy --role-name "$LAB-runner" --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
```

```bash
aws iam delete-role --role-name "$LAB-runner"
```

```bash
aws iam delete-role-policy --role-name "$LAB-dms-secrets" --policy-name ReadLabEndpoints
```

```bash
aws iam delete-role --role-name "$LAB-dms-secrets"
```

Keep account-level `dms-vpc-role` and `dms-cloudwatch-logs-role`; another lab may use
them. If you added policies beyond this lesson, inspect them before role deletion.

## 9. Account for retained resources and costs

Open **CloudWatch → Log groups** and identify the exact DMS log group using your
saved task log link. Decide whether to retain it for evidence. To retain 7 days,
use your verified group name in CloudShell:

```bash
aws logs put-retention-policy --log-group-name YOUR_LAB_DMS_LOG_GROUP --retention-in-days 7
```

If you created alarms, delete only their recorded names using Console or
`aws cloudwatch delete-alarms --alarm-names YOUR_LAB_ALARM_NAME`. No alarms are
silently assumed to have been created by this guide.

Revisit RDS snapshots, EC2/EBS, DMS, VPC endpoints, Secrets Manager and CloudWatch.
List what is deleted and what remains with owner/expiry. Review **Billing → Cost
Explorer** after its next data update. Stopping a service or closing the browser
does not eliminate storage charges.

**Gate:** no unaccounted billable resource; final snapshots, log retention and
pending secret deletion documented; shared resources preserved. A repeat practice
run starts with a new prefix and its own worksheet.
