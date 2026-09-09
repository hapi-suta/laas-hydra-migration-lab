# Build AWS with the Console

**Environment:** AWS Console, your assigned sandbox, **us-east-1**.
**CLI equivalent:** [native AWS CLI build path](build.md). **Outcome:** the same private
network, Aurora MySQL source, RDS PostgreSQL target, DMS instance and SSM runner.

Create this lab yourself from a fresh resource namespace. Choose Console or
native AWS CLI for each resource; do not execute both creation alternatives for
the same object. Record all returned IDs in your own worksheet. Use a unique
prefix such as `hydra-practice-01`; replace `hydra-console` below with that prefix.
Tag resources with `Project=your-prefix` and `Owner=your-lab-id`.
A cost-review tag is a reminder, not automatic shutdown.

## Read the layout first

A **VPC** is a private network in AWS. A **subnet** is a smaller address range inside it. An **Availability Zone** is an AWS location within a Region. Database subnet groups need subnets in two zones even though this practice target runs in one zone.

You create one network for the source and one for the target, then connect them. The databases stay private. Your runner downloads tools through an internet gateway, but accepts no incoming internet connections. You reach it through Session Manager.

## 1. Verify the account and create VPCs

- In the top-right account menu, compare the **Account ID** with your assignment.
   In the region selector, choose **US East (N. Virginia)**.
- Use the Console search box to open **VPC**. Select **Your VPCs** and inspect the existing IPv4 CIDRs. The proposed `10.81.0.0/16` and `10.82.0.0/16` ranges must not overlap other networks that will be connected. If they do, agree on unused ranges with the lab administrator before continuing. Choose **Create VPC → VPC only**.
- Create `hydra-console-source` with IPv4 CIDR `10.81.0.0/16`, no IPv6 block,
   default tenancy. Select it, choose **Actions → Edit VPC settings**, and enable
   DNS resolution and DNS hostnames.
- Repeat for `hydra-console-target`, CIDR `10.82.0.0/16`, with both DNS settings.
- Open **Subnets → Create subnet**. Create the following subnets; select two
   available AZs in your account and use the same AZ pair for both VPCs.

| VPC | Name | CIDR | AZ |
|---|---|---|---|
| source | source-db-a | 10.81.10.0/24 | first |
| source | source-db-b | 10.81.11.0/24 | second |
| source | runner-public | 10.81.1.0/24 | first |
| target | target-db-a | 10.82.10.0/24 | first |
| target | target-db-b | 10.82.11.0/24 | second |

For each subnet, choose the VPC first, enter the name, select its Availability Zone and enter its CIDR. Choose **Create subnet**. On the subnet details, record its subnet ID. Do not enable public-IP assignment on database subnets.

**Expected:** two VPCs and five subnets. Each database VPC has one database subnet in each of your two chosen zones. Save their IDs in the worksheet.

**Why:** the database subnet groups will use these addresses, and the separate networks let you practise a migration across a network connection.
[AWS VPC creation](https://docs.aws.amazon.com/vpc/latest/userguide/create-vpc.html).

## 2. Connect the networks

- Open **Peering connections → Create peering connection**. Select the source VPC
   as requester, **My account**, **This region**, and the target VPC as accepter.
- Select the pending connection and **Actions → Accept request**. Require
   **Active**. Edit its DNS settings to enable resolution for both directions.
- Open **Route tables → Create route table**. Create `source-private` in the
   source VPC and `target-private` in the target VPC.
- Under **Subnet associations → Edit subnet associations**, associate the source
   DB subnets with source-private and the target DB subnets with target-private.
- Under **Routes → Edit routes**, add `10.82.0.0/16 → Peering connection` on
   source-private and `10.81.0.0/16 → Peering connection` on target-private. Keep
   each VPC's automatically created local route.
- Open **Internet gateways → Create internet gateway**. Attach the new gateway
   to the source VPC only. Create a third route table, `runner-egress`, in source.
   Associate only runner-public. Add `0.0.0.0/0 → Internet gateway` and
   `10.82.0.0/16 → Peering connection`.

**Check:** the private DB route tables have no default internet route. The runner
uses a public IP for outbound package/SSM traffic, with no inbound service access.

**Why:** a route tells AWS where to send traffic for an address range. Peering routes let the source and target communicate. The runner's internet route lets it download packages. The database routes stay private.

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

Create runner and dms first, then use their IDs in the database rules. In a database group's **Inbound rules → Edit inbound rules**, add two rules for its port: one with the runner group as source, and one with the DMS group as source. Select **Custom TCP** if you do not see the matching database type. Save the rules.

**Expected:** source-db has two rules for port 3306; target-db has two for port 5432. The runner and DMS groups have no inbound rules. The secrets-endpoint group has one rule for port 443 from DMS.

**Why:** a security group decides which connections are allowed. These rules permit the runner and DMS to reach the databases without opening the databases to everyone.

For a source selector across the peer, enter the other VPC's security-group ID;
do not substitute `0.0.0.0/0`. Same-region peering must be active first.

## 4. Create database subnet and parameter groups

- Open **RDS → Subnet groups → Create DB subnet group**. Create a source group
   named `your-prefix-source` with source-db-a/source-db-b, and a target group
   named `your-prefix-target` with target-db-a/target-db-b.
- Open **Parameter groups → Create parameter group**. Select family
   `aurora-mysql8.0`, type **DB cluster parameter group**, name `hydra-console-mysql`.
- Edit its parameters: `binlog_format=ROW`, `binlog_row_image=FULL`,
   `require_secure_transport=ON` (or `1` where the field uses numeric values).
- Create a target **DB parameter group**, family `postgres17`,
   name `hydra-console-pg`, with `rds.force_ssl=1`.

In each subnet-group form, select the correct VPC, select both Availability Zones, add the two database subnets, then choose **Create**. Do not put runner-public in a database subnet group.

**Expected:** the source and target subnet groups each contain two database subnets. The source parameter group is a **cluster** group; the PostgreSQL parameter group is a **DB instance** group.

**Why:** the subnet groups tell RDS where it may place the databases. The source parameters make MySQL record row changes for DMS. The TLS parameters require encrypted database connections.

Create these groups before the databases so startup applies the intended settings.
For an existing database, a static parameter change may require an instance reboot;
check the parameter status instead of assuming it applied immediately.

## 5. Create the Aurora MySQL source and RDS PostgreSQL target

Open **RDS → Databases → Create database → Standard create** twice. Apply these
settings; expand **Connectivity** and **Additional configuration** where needed.

| Field | Source: Aurora MySQL | Target: RDS PostgreSQL |
|---|---|---|
| Engine | Aurora, MySQL compatible | PostgreSQL |
| Version | 8.0.mysql_aurora.3.13.0 if still available | Select an available RDS PostgreSQL 17.x minor version; record it |
| Template | Dev/Test | Dev/Test |
| Identifier (cluster for source, instance for target) | hydra-console-source | hydra-console-target |
| Credentials | labadmin; manage master password in Secrets Manager | same selection, separate generated secret |
| Instance | db.r6g.large provisioned | db.r6g.large provisioned |
| Storage | Aurora Standard, encrypted | General Purpose SSD gp3, 100 GiB, encrypted; storage autoscaling maximum 200 GiB |
| Availability | No Aurora Replica for this baseline | Single DB instance / Single-AZ; do not choose a Multi-AZ DB cluster |
| VPC / subnet group | source / source DB group | target / target DB group |
| Public access | No | No |
| Existing SG | source-db only | target-db only |
| Initial database | hydra | hydra |
| Parameter group | DB cluster group hydra-console-mysql | DB parameter group hydra-console-pg |
| Backup retention | 3 days | 3 days |
| Deletion protection | Enabled | Enabled |

For the target, choose the **PostgreSQL** engine tile. You are creating an
**Amazon RDS for PostgreSQL DB instance**.
Under **Availability and durability**, choose the Single-AZ DB instance option.
For a separate availability exercise, choose **Multi-AZ DB instance deployment**;
the three-instance Multi-AZ DB cluster option is outside this baseline.
Under **Connectivity**, choose not to connect automatically to an EC2 resource:
you already configured the specific runner/DMS security-group paths yourself.
Under **Additional configuration**, select the target DB parameter group and
initial database `hydra`. Disable optional paid add-ons not used by this lab.

Select engine versions supported by your DMS release. Use the engine/class
availability commands in the [CLI path](build.md#6-create-the-aurora-mysql-source-and-rds-postgresql-target)
if a version or class is missing. The author RDS rehearsal used PostgreSQL 17.11
on db.r6g.large; availability can differ in your account.
Create each database and wait for **Available**.

- Select the **source Aurora cluster**. Copy its **writer endpoint** as SOURCE_HOST.
   Expand the cluster and record its writer DB instance identifier as SOURCE_WRITER_ID.
- Select the **target PostgreSQL DB instance**. Under **Connectivity & security**,
   copy its **Endpoint** as TARGET_HOST and port `5432`. Record the DB instance
   identifier as TARGET_DB_ID. Confirm engine PostgreSQL, Publicly accessible No,
   storage encryption enabled and the intended Single-AZ deployment.
- Under **Configuration**, verify the target DB parameter group is `hydra-console-pg`
   and in-sync. If pending-reboot, use **Actions → Reboot**, wait for Available and
   check again before continuing. Open **Parameter groups → your target group**
   and confirm `rds.force_ssl=1`. Later SQL checks must prove TLS is in use;
   `SHOW rds.force_ssl` is not supported by PostgreSQL SQL.
- Record both managed master-secret ARNs in your private worksheet. RDS target
   storage is allocated explicitly; monitor **Monitoring → FreeStorageSpace**
   during loading. 100 GiB is a starting size, not a measured capacity guarantee.

[AWS Aurora creation](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.CreateInstance.html),
[RDS DB instance creation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_CreateDBInstance.html),
[RDS creation settings](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_CreateDBInstance.Settings.html),
[PostgreSQL SSL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html).

**Expected:** the source appears as an Aurora cluster with a writer underneath it. The target appears as a PostgreSQL DB instance. Both are **Available**. You have saved the source writer endpoint and target endpoint; their hostnames will differ from anyone else's lab.

## 6. Record the administrator secrets

- Select the source cluster in **RDS → Databases → Configuration**.
- Follow its **Master credentials ARN** into Secrets Manager. Record the secret
   ARN, not its password, in your worksheet.
- Repeat for the target DB instance. They are separate managed secrets.
- Do not create DMS credentials yet: you create the SQL users and matching
   dedicated endpoint secrets explicitly in [task 4](../05-dms/console.md).

[AWS Aurora managed credentials](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-secrets-manager.html)
and [RDS DB instance managed credentials](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-secrets-manager.html).

**Why:** you will use each administrator password to create the separate application and migration users. An ARN is AWS's full identifier for a resource; storing the ARN in your notes does not expose its password.

## 7. Create DMS roles, private service access and replication instance

- In **IAM → Roles**, search for `dms-vpc-role` and `dms-cloudwatch-logs-role`.
   Reuse them only if their trust and policies match below. Create missing roles
   before the replication instance.
- For each missing role choose **Create role → Custom trust policy** and enter:

```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"dms.amazonaws.com"},"Action":"sts:AssumeRole"}]}
```

- For `dms-vpc-role`, attach the AWS-managed `AmazonDMSVPCManagementRole` policy.
   For `dms-cloudwatch-logs-role`, attach `AmazonDMSCloudWatchLogsRole`. Use these
   exact role names. Do not replace another lab's existing role or policy.
- In **VPC → Endpoints → Create endpoint**, choose **AWS services**, service
   `com.amazonaws.us-east-1.secretsmanager`, type **Interface**, target VPC,
   target-db-a/target-db-b, private DNS enabled and secrets-endpoint SG.
- In **DMS → Subnet groups → Create subnet group**, choose target VPC and its
   two DB subnets. Name it with your prefix plus `-dms`.
- In **DMS → Replication instances → Create replication instance**, select your
   prefix, `dms.t3.medium`, engine `3.6.1` if still available, 100 GiB storage,
   Single-AZ, target VPC, your DMS subnet group and dms SG. Clear **Publicly
   accessible**. Disable automatic minor upgrades during this pinned rehearsal.
- Wait for **Available** and record the replication-instance ARN. Check the
   Secrets Manager VPC endpoint is **Available** too.

[AWS DMS service roles](https://docs.aws.amazon.com/dms/latest/userguide/security-iam.html)
and [replication instance setup](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_GettingStarted.Replication.html).

**Why:** the DMS role permits network setup and logging. The private Secrets Manager endpoint lets DMS retrieve its credentials without an internet route. The replication instance is the machine that will run your migration task.

## 8. Create the runner role and EC2 instance

- In **IAM → Roles → Create role**, choose **AWS service → EC2** and attach
   `AmazonSSMManagedInstanceCore`. Name it `hydra-console-runner`.
- The runner needs only `AmazonSSMManagedInstanceCore` for this manual path.
   You retrieve credentials using your own Console identity and create SQL users
   interactively; no bootstrap program needs master-secret access.
- In **EC2 → Instances → Launch instances**, choose Amazon Linux 2023 x86_64,
   t3.large, source VPC, runner-public subnet, public IP enabled, existing runner
   SG, and no SSH key pair. Select 60 GiB encrypted gp3 root storage.
- Expand **Advanced details**. Select the runner IAM instance profile, require
   IMDSv2, and leave **User data** empty. You will install every package yourself.
   Launch and wait for instance/status checks to pass.
- Select the instance, choose **Connect → Session Manager → Connect**. If unavailable,
   check IAM profile, outbound route, public IP, SSM agent and its logs.

**Expected:** the instance reaches **Running**, its status checks pass, and **Connect → Session Manager** opens a shell. A prompt with a cursor means you are connected; it does not mean the app is installed.

**Check:** no inbound rules on the runner; no public database endpoints; DMS is
private. Record the runner instance ID.

## 9. Save your resource details

Record both database endpoints, the source writer and target instance names, master-secret ARNs, runner ID, network IDs and DMS instance ARN in your worksheet.

**Expected:** both databases and the DMS instance show **Available**, and you can open a Session Manager terminal on the runner. The app is not installed yet, so there is no portal to open at this point.

Continue to [task 2: restore data and run Hydra](../lab/02-restore.md). That task installs the application and creates the database users before the restore. Perform the setup once.
