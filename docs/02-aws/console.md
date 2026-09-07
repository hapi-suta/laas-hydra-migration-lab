# Build AWS with the Console

**Environment:** AWS Console, your instructor-assigned sandbox, **us-east-1**.
**CLI equivalent:** [Terraform build path](build.md). **Outcome:** the same private
network, Aurora source/target, DMS instance and SSM runner.

Choose one creation method per lab name. If Terraform already created your lab,
use the steps below to inspect it; do not create duplicate resources or manually
modify its settings without updating Terraform. Console-only practice uses a fresh
name such as `hydra-console`. Record each resource ID in your private worksheet.
Every resource gets `Project=hydra-console`, `Owner=your-lab-id`, and a cost-review
deadline tag. A tag does not stop resources.

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
   with source-db-a/source-db-b, and a target group with target-db-a/target-db-b.
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
| Version used in instructor run | 8.0.mysql_aurora.3.13.0 | 17.10 |
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
from the instructor's run. Create each database and wait for its writer to be
**Available**. Copy the cluster **writer endpoint** and the managed secret ARN
from its details to your private worksheet. Do not copy a reader endpoint.
[AWS's Aurora creation procedure](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.CreateInstance.html).

## 6. Create DMS endpoint secrets and its IAM role

1. Open **Secrets Manager → Store a new secret → Other type of secret**. Create
   `hydra-console/dms-source` and `hydra-console/dms-target`, initially with an
   `uninitialized=true` key/value. Bootstrap grants will replace these placeholders
   with actual dedicated migration credentials before endpoint tests. Use the
   default Secrets Manager encryption key; do not put the RDS master password here.
2. Open **IAM → Roles → Create role → Custom trust policy**. Name the role
   `hydra-console-dms-secrets`. Use this trust policy for us-east-1:

```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"dms.us-east-1.amazonaws.com"},"Action":"sts:AssumeRole"}]}
```

3. On the created role, choose **Add permissions → Create inline policy → JSON**.
   Allow `secretsmanager:GetSecretValue` and `secretsmanager:DescribeSecret` on
   **only the two complete DMS secret ARNs**. The JSON structure is:

```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["secretsmanager:GetSecretValue","secretsmanager:DescribeSecret"],"Resource":["SOURCE_DMS_SECRET_ARN","TARGET_DMS_SECRET_ARN"]}]}
```

Replace both placeholders before saving. Record the role ARN. The operator also
needs permission to pass this specific role to DMS.

## 7. Provide private Secrets Manager access and DMS compute

1. In **VPC → Endpoints → Create endpoint**, choose **AWS services**, service
   `com.amazonaws.us-east-1.secretsmanager`, type **Interface**, target VPC,
   target-db-a and target-db-b, private DNS enabled, secrets-endpoint SG.
2. Open **DMS → Subnet groups → Create subnet group**. Choose target VPC and its
   two DB subnets. Name it `hydra-console-dms`.
3. Open **DMS → Replication instances → Create replication instance**. Choose
   `hydra-console`, `dms.t3.medium`, engine `3.6.1`, 100 GiB allocated storage,
   Single-AZ for this baseline, target VPC, the new subnet group, and dms SG.
   Clear **Publicly accessible**. Disable automatic minor upgrades during the
   pinned rehearsal.
4. If the account lacks DMS service roles, follow the console's IAM-role setup:
   `dms-vpc-role` with `AmazonDMSVPCManagementRole`, and
   `dms-cloudwatch-logs-role` with `AmazonDMSCloudWatchLogsRole`, trusted by
   `dms.amazonaws.com`. Reuse existing correctly configured roles.
5. Wait for **Available**; record the replication-instance ARN.
[AWS DMS setup procedure](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_GettingStarted.Replication.html).

## 8. Create the runner role and EC2 instance

1. In **IAM → Roles → Create role**, choose **AWS service → EC2** and attach
   `AmazonSSMManagedInstanceCore`. Name it `hydra-console-runner`.
2. Add an inline policy allowing `secretsmanager:GetSecretValue` on the **two RDS
   managed master-secret ARNs**, and `secretsmanager:PutSecretValue` on the **two
   dedicated DMS-secret ARNs**. Keep these as two separate statements.
3. In **EC2 → Instances → Launch instances**, choose Amazon Linux 2023 x86_64,
   t3.large, source VPC, runner-public subnet, public IP enabled, existing runner
   SG, and no SSH key pair. Select 60 GiB encrypted gp3 root storage.
4. Expand **Advanced details**. Select the runner IAM instance profile, require
   IMDSv2, and paste the contents of the bundle's `infra/runner.sh` into **User
   data**. Launch and wait for instance/status checks to pass.
5. Select the instance, choose **Connect → Session Manager → Connect**. If unavailable,
   check IAM profile, outbound route, public IP, SSM agent and bootstrap logs.

**Check:** no inbound rules on the runner; no public database endpoints; DMS is
private. Record the runner instance ID.

## 9. Create the runtime manifest and bootstrap the app

In the Session Manager terminal, as **ssm-user**, run `sudo su - ec2-user`, then
`cd /opt/hydra-practice`. Follow the [CLI build's runner installation](build.md#3-open-the-runner).
Create `runtime/cloud.json` with `vi`, using your recorded values:

```json
{
  "account_id":"YOUR_12_DIGIT_ACCOUNT", "region":"us-east-1", "name":"hydra-console",
  "runner_id":"YOUR_RUNNER_ID", "dms_instance_arn":"YOUR_DMS_INSTANCE_ARN",
  "dms_secrets_role_arn":"YOUR_DMS_SECRETS_ROLE_ARN",
  "source":{"host":"SOURCE_WRITER_ENDPOINT","port":3306,"master_secret_arn":"SOURCE_MASTER_SECRET_ARN","dms_secret_arn":"SOURCE_DMS_SECRET_ARN"},
  "target":{"host":"TARGET_WRITER_ENDPOINT","port":5432,"master_secret_arn":"TARGET_MASTER_SECRET_ARN","dms_secret_arn":"TARGET_DMS_SECRET_ARN"}
}
```

Run the same bootstrap/app commands from the CLI path inside this browser terminal.
Console Session Manager supplies a shell; it does not provide browser port
forwarding. To view the private portal on your laptop, use the documented SSM CLI
port-forward command. Database creation can be Console-only, but private local
browser access still requires that tunnel.

**Evidence:** account/region check, resource worksheet, route and SG inspection,
Available database/DMS states, SSM session, TLS bootstrap, successful portal login.
The manual Console creation path is documented from AWS references; it is not
claimed as separately replayed merely because the Terraform path succeeded.
