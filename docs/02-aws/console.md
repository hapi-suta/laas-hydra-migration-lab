# Build AWS with the Console

**Environment:** AWS Console, your assigned sandbox, **us-east-1**.
**CLI equivalent:** [native AWS CLI build path](build.md). **Outcome:** the same private
network, Aurora source/target, DMS instance and SSM runner.

Create this lab yourself from a fresh resource namespace. Choose Console or
native AWS CLI for each resource; do not execute both creation alternatives for
the same object. Record all returned IDs in your own worksheet. Use a unique
prefix such as `hydra-practice-01`; replace `hydra-console` below with that prefix.
Tag resources with `Project=your-prefix` and `Owner=your-lab-id`.
A cost-review tag is a reminder, not automatic shutdown.

## 1. Verify the account and create VPCs

1. In the top-right account menu, compare the **Account ID** with your assignment.
   In the region selector, choose **US East (N. Virginia)**.
2. Open **VPC → Your VPCs → Create VPC**. Choose **VPC only**.
3. Create `hydra-console-source` with IPv4 CIDR `10.81.0.0/16`, no IPv6 block,
   default tenancy. Select it, choose **Actions → Edit VPC settings**, and enable
   DNS resolution and DNS hostnames.
4. Repeat for `hydra-console-target`, CIDR `10.82.0.0/16`, with both DNS settings.
5. Open **Subnets → Create subnet**. Create the following subnets; select two
   available AZs in your account and use the same AZ pair for both VPCs.

| VPC | Name | CIDR | AZ |
|---|---|---|---|
| source | source-db-a | 10.81.10.0/24 | first |
| source | source-db-b | 10.81.11.0/24 | second |
| source | runner-public | 10.81.1.0/24 | first |
| target | target-db-a | 10.82.10.0/24 | first |
| target | target-db-b | 10.82.11.0/24 | second |

Do not enable public-IP assignment on database subnets.
[AWS VPC creation](https://docs.aws.amazon.com/vpc/latest/userguide/create-vpc.html).

## 2. Connect the networks

1. Open **Peering connections → Create peering connection**. Select the source VPC
   as requester, **My account**, **This region**, and the target VPC as accepter.
2. Select the pending connection and **Actions → Accept request**. Require
   **Active**. Edit its DNS settings to enable resolution for both directions.
3. Open **Route tables → Create route table**. Create `source-private` in the
   source VPC and `target-private` in the target VPC.
4. Under **Subnet associations → Edit subnet associations**, associate the source
   DB subnets with source-private and the target DB subnets with target-private.
5. Under **Routes → Edit routes**, add `10.82.0.0/16 → Peering connection` on
   source-private and `10.81.0.0/16 → Peering connection` on target-private. Keep
   each VPC's automatically created local route.
6. Open **Internet gateways → Create internet gateway**. Attach the new gateway
   to the source VPC only. Create a third route table, `runner-egress`, in source.
   Associate only runner-public. Add `0.0.0.0/0 → Internet gateway` and
   `10.82.0.0/16 → Peering connection`.

**Check:** the private DB route tables have no default internet route. The runner
uses a public IP for outbound package/SSM traffic, with no inbound service access.

## 3. Create security groups

Open **EC2 → Security Groups → Create security group** for each row below. Remove
any automatically proposed inbound SSH rule. Keep outbound allow-all for this
bounded training baseline; production egress restriction is a separate exercise.
[AWS security groups](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html).

| Group | VPC | Inbound rules |
|---|---|---|
| runner | source | None |
| dms | target | None |
| source-db | source | TCP 3306 from runner SG and dms SG |
| target-db | target | TCP 5432 from runner SG and dms SG |
| secrets-endpoint | target | TCP 443 from dms SG |

For a source selector across the peer, enter the other VPC's security-group ID;
do not substitute `0.0.0.0/0`. Same-region peering must be active first.

## 4. Create database subnet and parameter groups

1. Open **RDS → Subnet groups → Create DB subnet group**. Create a source group
   named `your-prefix-source` with source-db-a/source-db-b, and a target group
   named `your-prefix-target` with target-db-a/target-db-b.
2. Open **Parameter groups → Create parameter group**. Select family
   `aurora-mysql8.0`, type **DB cluster parameter group**, name `hydra-console-mysql`.
3. Edit its parameters: `binlog_format=ROW`, `binlog_row_image=FULL`,
   `require_secure_transport=ON` (or `1` where the field uses numeric values).
4. Create a target **DB cluster parameter group**, family `aurora-postgresql17`,
   name `hydra-console-pg`, with `rds.force_ssl=1`.

Create these groups before the clusters so startup applies the intended settings.
For an existing cluster, a static parameter change may require a writer reboot;
check the parameter status instead of assuming it applied immediately.

## 5. Create the Aurora source and target

Open **RDS → Databases → Create database → Standard create** twice. Apply these
settings; expand **Connectivity** and **Additional configuration** where needed.

| Field | Source | Target |
|---|---|---|
| Engine | Aurora, MySQL compatible | Aurora, PostgreSQL compatible |
| Version used in engineering test | 8.0.mysql_aurora.3.13.0 | 17.10 |
| Identifier | hydra-console-source | hydra-console-target |
| Credentials | labadmin; manage master password in Secrets Manager | same selection, separate generated secret |
| Instance | db.r6g.large provisioned | db.r6g.large provisioned |
| Storage | Aurora Standard, encrypted | Aurora Standard, encrypted |
| Reader | No additional reader for baseline | No additional reader for baseline |
| VPC / subnet group | source / source DB group | target / target DB group |
| Public access | No | No |
| Existing SG | source-db only | target-db only |
| Initial database | hydra | hydra |
| Cluster parameter group | hydra-console-mysql | hydra-console-pg |
| Backup retention | 3 days | 3 days |
| Deletion protection | Enabled | Enabled |

Disable optional paid add-ons not used by this baseline. Select versions that
remain available and are supported by your DMS release; record any difference
from the engineering test. Create each database and wait for its writer to be
**Available**. Copy the cluster **writer endpoint** and the managed secret ARN
from its details to your private worksheet. Record the actual writer instance
identifiers as SOURCE_WRITER_ID and TARGET_WRITER_ID; the Console can generate
names different from the CLI examples. Do not copy a reader endpoint.
[AWS's Aurora creation procedure](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.CreateInstance.html).

## 6. Record the administrator secrets

1. Select the source cluster in **RDS → Databases → Configuration**.
2. Follow its **Master credentials ARN** into Secrets Manager. Record the secret
   ARN, not its password, in your worksheet.
3. Repeat for the target cluster. They are separate managed secrets.
4. Do not create DMS credentials yet: you create the SQL users and matching
   dedicated endpoint secrets explicitly in [Module 05](../05-dms/console.md).

[AWS Aurora managed credentials](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-secrets-manager.html).

## 7. Create DMS roles, private service access and replication instance

1. In **IAM → Roles**, search for `dms-vpc-role` and `dms-cloudwatch-logs-role`.
   Reuse them only if their trust and policies match below. Create missing roles
   before the replication instance.
2. For each missing role choose **Create role → Custom trust policy** and enter:

```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"dms.amazonaws.com"},"Action":"sts:AssumeRole"}]}
```

3. For `dms-vpc-role`, attach the AWS-managed `AmazonDMSVPCManagementRole` policy.
   For `dms-cloudwatch-logs-role`, attach `AmazonDMSCloudWatchLogsRole`. Use these
   exact role names. Do not replace another lab's existing role or policy.
4. In **VPC → Endpoints → Create endpoint**, choose **AWS services**, service
   `com.amazonaws.us-east-1.secretsmanager`, type **Interface**, target VPC,
   target-db-a/target-db-b, private DNS enabled and secrets-endpoint SG.
5. In **DMS → Subnet groups → Create subnet group**, choose target VPC and its
   two DB subnets. Name it with your prefix plus `-dms`.
6. In **DMS → Replication instances → Create replication instance**, select your
   prefix, `dms.t3.medium`, engine `3.6.1` if still available, 100 GiB storage,
   Single-AZ, target VPC, your DMS subnet group and dms SG. Clear **Publicly
   accessible**. Disable automatic minor upgrades during this pinned rehearsal.
7. Wait for **Available** and record the replication-instance ARN. Check the
   Secrets Manager VPC endpoint is **Available** too.

[AWS DMS service roles](https://docs.aws.amazon.com/dms/latest/userguide/security-iam.html)
and [replication instance setup](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_GettingStarted.Replication.html).

## 8. Create the runner role and EC2 instance

1. In **IAM → Roles → Create role**, choose **AWS service → EC2** and attach
   `AmazonSSMManagedInstanceCore`. Name it `hydra-console-runner`.
2. The runner needs only `AmazonSSMManagedInstanceCore` for this manual path.
   You retrieve credentials using your own Console identity and create SQL users
   interactively; no bootstrap program needs master-secret access.
3. In **EC2 → Instances → Launch instances**, choose Amazon Linux 2023 x86_64,
   t3.large, source VPC, runner-public subnet, public IP enabled, existing runner
   SG, and no SSH key pair. Select 60 GiB encrypted gp3 root storage.
4. Expand **Advanced details**. Select the runner IAM instance profile, require
   IMDSv2, and leave **User data** empty. You will install every package yourself.
   Launch and wait for instance/status checks to pass.
5. Select the instance, choose **Connect → Session Manager → Connect**. If unavailable,
   check IAM profile, outbound route, public IP, SSM agent and its logs.

**Check:** no inbound rules on the runner; no public database endpoints; DMS is
private. Record the runner instance ID.

## 9. Install the application and create SQL users

Continue to [Install the application and create database users](application.md).
Follow its numbered steps in your Session Manager terminal: install Docker and
Compose, clone and inspect the application source, download the public RDS CA,
generate your own secrets, connect with the database clients, execute each SQL
user/grant statement, initialize the native PostgreSQL schema and verify MySQL is empty for restore.

The page includes both Console and AWS CLI ways to open the session and retrieve
managed credentials. Viewing the private portal requires the documented SSM
port-forward session on your workstation; a Console shell alone cannot forward
a port to your local browser.

**Checkpoint:** your worksheet, Available database/DMS states, runner Online,
private routes and SGs, native PostgreSQL migrations complete, and MySQL empty for restore.
You must obtain these results yourself. The manual Console route has not been
independently replayed end to end; save your actual results and errors.
