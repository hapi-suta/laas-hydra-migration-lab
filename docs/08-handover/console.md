# Inspect costs and clean up in the Console

**Environment:** assigned AWS account and region. **CLI equivalent:**
[Handover and cleanup](build.md). **Prerequisite:** your decision to clean up
this named disposable lab, final evidence saved, customer practice no longer active.

## 1. Record what is being handed over

In RDS, DMS, EC2 and VPC, filter by the lab's exact project tag. Record database
versions, instance classes, endpoints, DMS task status, resource IDs, owner and
cost-review deadline in the private handover worksheet. Preserve the public guide
URL and exact code revision. Provide access through the assigned AWS login and
SSM; do not email or publish master credentials.

## 2. Check costs before stopping anything

Open **Billing and Cost Management → Cost Explorer**. Choose daily granularity,
the rehearsal dates, and group by service. Filter by the project cost-allocation
tag if it has been activated and billing data has arrived. RDS, DMS, EC2/EBS,
Secrets Manager, VPC endpoints, IPv4 and transfer charges can appear separately.
Tag activation and billing updates are not immediate; an empty graph does not
mean the lab is free.

Stopping either database is temporary, and storage/snapshot charges continue. Stopping EC2 also
retains its EBS storage. A review tag is only a label. Decide whether the lab is
being retained for another practice session or permanently removed.

## 3. Choose the matching cleanup method

**Student-created lab:** follow the sequence below. Reconfirm each selected
resource's exact name, project tag and dependencies. Do not select shared DMS
service roles or other learners' instances.

## 4. Stop and delete migration resources

1. In **DMS → Database migration tasks**, select the lab task → **Actions → Stop**.
   Wait for Stopped, save final statistics, then choose **Delete** and confirm its
   exact identifier.
2. In **Endpoints**, delete only the lab's source and target endpoints.
3. In **Replication instances**, delete only the lab instance and wait until it
   disappears. Then delete its subnet group and imported certificate if unused.

## 5. Remove the databases and runner

First finish the [Windows SCT desktop cleanup](../04-sct/mac-desktop.md#7-pause-or-remove-the-windows-desktop).
Confirm your SCT reports are readable on the Mac. Account for the Windows
instance, its root volume and dedicated key pair before removing the shared
runner security group, subnet or IAM profile.


1. In **RDS → Databases**, select the **source Aurora cluster → Modify**. Clear
   deletion protection and apply. Separately select the **target PostgreSQL DB
   instance → Modify**, clear deletion protection and apply. Verify both changes.
2. For the source, delete any added readers first, then the writer and cluster
   using the Aurora deletion workflow. Retain a uniquely named final **DB cluster
   snapshot**. Wait for the cluster to disappear and the snapshot to be Available.
3. For the target, select its **DB instance → Actions → Delete**. Select **Create
   final snapshot**, enter a unique name and select **Retain automated backups**.
   Enter the requested deletion confirmation and choose **Delete**. Wait for the
   instance to disappear. In **Snapshots → Manual**, require the target **DB
   snapshot** Available. Record its retention deadline and the automated-backup
   expiry. The target has no Aurora cluster to delete.
4. In **EC2 → Instances**, select only the runner → **Instance state → Terminate
   instance**. Check that its root volume and any separately created lab volumes
   are accounted for. Stopping an instance is not teardown.
5. In **Secrets Manager**, schedule deletion of the two dedicated DMS secrets
   with the recovery window. RDS manages its master-secret lifecycle; inspect
   the result instead of deleting unrelated secrets.

[AWS Aurora deletion](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/USER_DeleteCluster.html)
and [RDS DB instance deletion](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_DeleteInstance.html).

Final snapshots, retained automated backups and pending-deletion secrets are retained resources, so a complete
handover must list them. Deleting the final recovery copy is a separate explicit
decision; it is not silently included in this sequence.

## 6. Remove only unused lab network and IAM resources

1. In **VPC → Endpoints**, delete the lab Secrets Manager interface endpoint.
2. Wait for database/DMS/endpoint network interfaces to disappear. Delete the lab
   SG rules/groups once no ENI references them.
3. Delete the lab peering connection. Remove custom route-table associations,
   subnets and route tables. Detach and delete the source internet gateway.
4. Delete the two lab VPCs. Dependency errors identify remaining resources; inspect
   them rather than deleting every resource returned by the Console.
5. In **RDS**, delete the now-unused lab DB subnet groups, source DB cluster parameter
   group and target DB parameter group. Then in **IAM**, delete the lab-specific runner instance profile/role and DMS
   secrets role when unused. Keep shared `dms-vpc-role` and
   `dms-cloudwatch-logs-role` if other migrations use them.
6. Remove lab-only alarms/log groups according to the evidence retention policy.

## 7. Verify the outcome

Revisit RDS, DMS, EC2, EBS, VPC endpoints, VPCs, Secrets Manager, snapshots and
CloudWatch. Filter by the project and check the recorded IDs. Produce two lists:
deleted resources and deliberately retained resources with expiry/owner. Repeat
the inventory: there should be no unaccounted billable resource. Review Cost
Explorer after its next data update and resolve residual charges.

**Evidence:** recorded cleanup scope, deletion results, retained-snapshot/secret list,
zero-unaccounted-resource inventory and final cost review.
