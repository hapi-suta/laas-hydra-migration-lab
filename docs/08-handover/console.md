# Inspect costs and clean up in the Console

**Environment:** assigned AWS account and region. **CLI equivalent:**
[Handover and cleanup](build.md). **Prerequisite:** instructor-approved cleanup of
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

Aurora stop is temporary, and storage/snapshot charges continue. Stopping EC2 also
retains its EBS storage. A review tag is only a label. Decide whether the lab is
being retained for another practice session or permanently removed.

## 3. Choose the matching cleanup method

**Terraform-created lab:** use the [CLI teardown procedure](build.md) with its
original state. Use the Console to inspect the plan's target resources and verify
the result. Deleting Terraform resources manually creates state drift; don't mix
cleanup methods without reconciling state.

**Console-created lab:** follow the sequence below. Reconfirm each selected
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

1. In **RDS → Databases**, select each lab cluster → **Modify**, clear deletion
   protection and apply the change deliberately. Wait for it to apply.
2. Delete any lab readers first, then the writer/cluster using the Console's
   deletion workflow. Choose a uniquely named **final snapshot** if the handover
   calls for retained recovery. Record its owner and retention deadline.
3. In **EC2 → Instances**, select only the lab runner → **Instance state →
   Terminate instance**. Verify its root volume was deleted and no separately
   created lab volumes remain. Stopping the instance is not teardown.
4. In **Secrets Manager**, schedule deletion of the two dedicated DMS secrets
   using the recovery window. RDS manages its own master-secret lifecycle;
   inspect the result instead of deleting unrelated RDS secrets.

Final snapshots and pending-deletion secrets are retained resources, so a complete
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
5. In **IAM**, delete the lab-specific runner instance profile/role and DMS
   secrets role when unused. Keep shared `dms-vpc-role` and
   `dms-cloudwatch-logs-role` if other migrations use them.
6. Remove lab-only alarms/log groups according to the evidence retention policy.

## 7. Verify the outcome

Revisit RDS, DMS, EC2, EBS, VPC endpoints, VPCs, Secrets Manager, snapshots and
CloudWatch. Filter by the project and check the recorded IDs. Produce two lists:
deleted resources and deliberately retained resources with expiry/owner. Repeat
the inventory: there should be no unaccounted billable resource. Review Cost
Explorer after its next data update and resolve residual charges.

**Evidence:** approved scope, deletion results, retained-snapshot/secret list,
zero-unaccounted-resource inventory and final cost review.
