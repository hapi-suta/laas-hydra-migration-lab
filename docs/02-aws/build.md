# Create every AWS resource with the AWS CLI

**You perform this lesson yourself.** Start with a new lab name and unused CIDRs
in your assigned sandbox. No pre-created VPC, database, EC2 instance, IAM role or
DMS instance is required. [Console alternative](console.md).

**Where:** AWS CloudShell, Bash, in us-east-1. CloudShell supplies AWS CLI credentials
from your Console login. It is your AWS control terminal; private database SQL
will run from the EC2 runner you create. Execute each block, inspect its result,
and stop at a failed checkpoint. Do not paste the whole page as a deployment script.

## 1. Identify your account and save your worksheet

Open the AWS Console, select **US East (N. Virginia)**, then open **CloudShell**
from the toolbar. Choose Bash. Run:

```bash
aws --version
```

```bash
aws sts get-caller-identity
```

```bash
export AWS_REGION=us-east-1
```

```bash
export AWS_DEFAULT_REGION=us-east-1
```

```bash
export AWS_PAGER=""
```

```bash
export LAB=hydra-practice-01
```

```bash
export LAB_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
```

```bash
mkdir -p "$HOME/$LAB"
```

```bash
cd "$HOME/$LAB"
```

```bash
umask 077
```

Compare the returned Account with your sandbox assignment. `LAB` is your resource
prefix; change it before creating a second lab. The directory stores your own
JSON and worksheet, not a supplied Terraform state. Check the proposed CIDRs
against **VPC → Your VPCs** before using them.

```bash
aws ec2 describe-vpcs --query 'Vpcs[].{ID:VpcId,CIDR:CidrBlock}' --output table
```

```bash
aws ec2 describe-availability-zones --filters Name=state,Values=available \
  --query 'AvailabilityZones[].ZoneName' --output table
```

```bash
export AZ_A=us-east-1a
```

```bash
export AZ_B=us-east-1b
```

Use two distinct available AZ names from your account's output. Create a private
`worksheet.txt` and record your account, region, LAB, AZs, and every returned ID.
If CloudShell closes, restore these non-secret variables from that worksheet.
[AWS CloudShell getting started](https://docs.aws.amazon.com/cloudshell/latest/userguide/getting-started.html)
and [STS identity](https://docs.aws.amazon.com/cli/latest/reference/sts/get-caller-identity.html).

## 2. Create the two VPCs and five subnets

```bash
export SOURCE_VPC=$(aws ec2 create-vpc --cidr-block 10.81.0.0/16 \
  --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=$LAB-source},{Key=Project,Value=$LAB}]" \
  --query Vpc.VpcId --output text)
```

```bash
aws ec2 modify-vpc-attribute --vpc-id "$SOURCE_VPC" --enable-dns-support '{"Value":true}'
```

```bash
aws ec2 modify-vpc-attribute --vpc-id "$SOURCE_VPC" --enable-dns-hostnames '{"Value":true}'
```

```bash
export TARGET_VPC=$(aws ec2 create-vpc --cidr-block 10.82.0.0/16 \
  --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=$LAB-target},{Key=Project,Value=$LAB}]" \
  --query Vpc.VpcId --output text)
```

```bash
aws ec2 modify-vpc-attribute --vpc-id "$TARGET_VPC" --enable-dns-support '{"Value":true}'
```

```bash
aws ec2 modify-vpc-attribute --vpc-id "$TARGET_VPC" --enable-dns-hostnames '{"Value":true}'
```

```bash
export SOURCE_A=$(aws ec2 create-subnet --vpc-id "$SOURCE_VPC" \
  --cidr-block 10.81.10.0/24 --availability-zone "$AZ_A" \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$LAB-source_a},{Key=Project,Value=$LAB}]" \
  --query Subnet.SubnetId --output text)
```

```bash
export SOURCE_B=$(aws ec2 create-subnet --vpc-id "$SOURCE_VPC" \
  --cidr-block 10.81.11.0/24 --availability-zone "$AZ_B" \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$LAB-source_b},{Key=Project,Value=$LAB}]" \
  --query Subnet.SubnetId --output text)
```

```bash
export RUNNER_SUBNET=$(aws ec2 create-subnet --vpc-id "$SOURCE_VPC" \
  --cidr-block 10.81.1.0/24 --availability-zone "$AZ_A" \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$LAB-runner_subnet},{Key=Project,Value=$LAB}]" \
  --query Subnet.SubnetId --output text)
```

```bash
export TARGET_A=$(aws ec2 create-subnet --vpc-id "$TARGET_VPC" \
  --cidr-block 10.82.10.0/24 --availability-zone "$AZ_A" \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$LAB-target_a},{Key=Project,Value=$LAB}]" \
  --query Subnet.SubnetId --output text)
```

```bash
export TARGET_B=$(aws ec2 create-subnet --vpc-id "$TARGET_VPC" \
  --cidr-block 10.82.11.0/24 --availability-zone "$AZ_B" \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$LAB-target_b},{Key=Project,Value=$LAB}]" \
  --query Subnet.SubnetId --output text)
```

Check **VPC → Subnets**: source has three, target has two; the database
subnets span two AZs. Database subnets must not assign public IP addresses.
[AWS create-vpc](https://docs.aws.amazon.com/cli/latest/reference/ec2/create-vpc.html),
[create-subnet](https://docs.aws.amazon.com/cli/latest/reference/ec2/create-subnet.html),
[DNS attributes](https://docs.aws.amazon.com/cli/latest/reference/ec2/modify-vpc-attribute.html).

## 3. Add peering, return routes and runner internet egress

```bash
export PEER=$(aws ec2 create-vpc-peering-connection --vpc-id "$SOURCE_VPC" \
  --peer-vpc-id "$TARGET_VPC" --query VpcPeeringConnection.VpcPeeringConnectionId --output text)
```

```bash
aws ec2 accept-vpc-peering-connection --vpc-peering-connection-id "$PEER"
```

```bash
aws ec2 wait vpc-peering-connection-exists --vpc-peering-connection-ids "$PEER" --filters Name=status-code,Values=active
```

```bash
aws ec2 modify-vpc-peering-connection-options --vpc-peering-connection-id "$PEER" \
  --requester-peering-connection-options AllowDnsResolutionFromRemoteVpc=true \
  --accepter-peering-connection-options AllowDnsResolutionFromRemoteVpc=true
```

```bash
export SOURCE_RT=$(aws ec2 create-route-table --vpc-id "$SOURCE_VPC" --query RouteTable.RouteTableId --output text)
```

```bash
export TARGET_RT=$(aws ec2 create-route-table --vpc-id "$TARGET_VPC" --query RouteTable.RouteTableId --output text)
```

```bash
export RUNNER_RT=$(aws ec2 create-route-table --vpc-id "$SOURCE_VPC" --query RouteTable.RouteTableId --output text)
```

```bash
aws ec2 associate-route-table --route-table-id "$SOURCE_RT" --subnet-id "$SOURCE_A"
```

```bash
aws ec2 associate-route-table --route-table-id "$SOURCE_RT" --subnet-id "$SOURCE_B"
```

```bash
aws ec2 associate-route-table --route-table-id "$TARGET_RT" --subnet-id "$TARGET_A"
```

```bash
aws ec2 associate-route-table --route-table-id "$TARGET_RT" --subnet-id "$TARGET_B"
```

```bash
aws ec2 associate-route-table --route-table-id "$RUNNER_RT" --subnet-id "$RUNNER_SUBNET"
```

```bash
aws ec2 create-route --route-table-id "$SOURCE_RT" --destination-cidr-block 10.82.0.0/16 --vpc-peering-connection-id "$PEER"
```

```bash
aws ec2 create-route --route-table-id "$TARGET_RT" --destination-cidr-block 10.81.0.0/16 --vpc-peering-connection-id "$PEER"
```

```bash
aws ec2 create-route --route-table-id "$RUNNER_RT" --destination-cidr-block 10.82.0.0/16 --vpc-peering-connection-id "$PEER"
```

```bash
export IGW=$(aws ec2 create-internet-gateway --query InternetGateway.InternetGatewayId --output text)
```

```bash
aws ec2 attach-internet-gateway --internet-gateway-id "$IGW" --vpc-id "$SOURCE_VPC"
```

```bash
aws ec2 create-route --route-table-id "$RUNNER_RT" --destination-cidr-block 0.0.0.0/0 --gateway-id "$IGW"
```

```bash
aws ec2 create-tags --resources "$PEER" "$SOURCE_RT" "$TARGET_RT" "$RUNNER_RT" "$IGW" --tags Key=Project,Value="$LAB"
```

```bash
aws ec2 describe-route-tables --route-table-ids "$SOURCE_RT" "$TARGET_RT" "$RUNNER_RT" \
  --query 'RouteTables[].{ID:RouteTableId,Routes:Routes,Associations:Associations}'
```

**Expected:** peering Active; both private route tables have local and peer routes;
only RUNNER_RT has `0.0.0.0/0`. Peering is not transitive. The DMS instance will
reach Secrets Manager using an interface endpoint, not this internet gateway.
[AWS peering workflow](https://docs.aws.amazon.com/vpc/latest/peering/create-vpc-peering-connection.html),
[peering routes](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-routing.html),
[internet gateways](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html).

## 4. Create and connect security groups

```bash
export RUNNER_SG=$(aws ec2 create-security-group --group-name "$LAB-runner" \
  --description "$LAB runner" --vpc-id "$SOURCE_VPC" --query GroupId --output text)
```

```bash
export DMS_SG=$(aws ec2 create-security-group --group-name "$LAB-dms" \
  --description "$LAB dms" --vpc-id "$TARGET_VPC" --query GroupId --output text)
```

```bash
export SOURCE_SG=$(aws ec2 create-security-group --group-name "$LAB-source-db" \
  --description "$LAB source-db" --vpc-id "$SOURCE_VPC" --query GroupId --output text)
```

```bash
export TARGET_SG=$(aws ec2 create-security-group --group-name "$LAB-target-db" \
  --description "$LAB target-db" --vpc-id "$TARGET_VPC" --query GroupId --output text)
```

```bash
export SECRETS_SG=$(aws ec2 create-security-group --group-name "$LAB-secrets" \
  --description "$LAB secrets" --vpc-id "$TARGET_VPC" --query GroupId --output text)
```

```bash
aws ec2 authorize-security-group-ingress --group-id "$SOURCE_SG" --protocol tcp --port 3306 --source-group "$RUNNER_SG"
```

```bash
aws ec2 authorize-security-group-ingress --group-id "$SOURCE_SG" --protocol tcp --port 3306 --source-group "$DMS_SG"
```

```bash
aws ec2 authorize-security-group-ingress --group-id "$TARGET_SG" --protocol tcp --port 5432 --source-group "$RUNNER_SG"
```

```bash
aws ec2 authorize-security-group-ingress --group-id "$TARGET_SG" --protocol tcp --port 5432 --source-group "$DMS_SG"
```

```bash
aws ec2 authorize-security-group-ingress --group-id "$SECRETS_SG" --protocol tcp --port 443 --source-group "$DMS_SG"
```

```bash
aws ec2 create-tags --resources "$RUNNER_SG" "$DMS_SG" "$SOURCE_SG" "$TARGET_SG" "$SECRETS_SG" --tags Key=Project,Value="$LAB"
```

```bash
aws ec2 describe-security-groups --group-ids "$RUNNER_SG" "$DMS_SG" "$SOURCE_SG" "$TARGET_SG" "$SECRETS_SG" \
  --query 'SecurityGroups[].{ID:GroupId,Name:GroupName,Inbound:IpPermissions}'
```

**Expected:** runner and DMS have no inbound rules; each database accepts only
its port from runner and DMS. The Secrets Manager endpoint accepts 443 from DMS.
Default outbound allow-all is retained for this lab. Cross-VPC SG references
require the active same-region peering above.
[AWS SG references over peering](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-security-groups.html)
and [authorize ingress](https://docs.aws.amazon.com/cli/latest/reference/ec2/authorize-security-group-ingress.html).

## 5. Create Aurora subnet and parameter groups

```bash
aws rds create-db-subnet-group --db-subnet-group-name "$LAB-source" --db-subnet-group-description "$LAB source" --subnet-ids "$SOURCE_A" "$SOURCE_B"
```

```bash
aws rds create-db-subnet-group --db-subnet-group-name "$LAB-target" --db-subnet-group-description "$LAB target" --subnet-ids "$TARGET_A" "$TARGET_B"
```

```bash
aws rds create-db-cluster-parameter-group --db-cluster-parameter-group-name "$LAB-mysql" --db-parameter-group-family aurora-mysql8.0 --description "$LAB MySQL CDC"
```

```bash
aws rds modify-db-cluster-parameter-group --db-cluster-parameter-group-name "$LAB-mysql" --parameters \
  ParameterName=binlog_format,ParameterValue=ROW,ApplyMethod=pending-reboot \
  ParameterName=binlog_row_image,ParameterValue=FULL,ApplyMethod=immediate \
  ParameterName=require_secure_transport,ParameterValue=ON,ApplyMethod=immediate
```

```bash
aws rds create-db-cluster-parameter-group --db-cluster-parameter-group-name "$LAB-pg" --db-parameter-group-family aurora-postgresql17 --description "$LAB PostgreSQL TLS"
```

```bash
aws rds modify-db-cluster-parameter-group --db-cluster-parameter-group-name "$LAB-pg" --parameters \
  ParameterName=rds.force_ssl,ParameterValue=1,ApplyMethod=pending-reboot
```

`ROW` records row changes for CDC; `FULL` includes full before/after row images.
Native SQL checks later must prove these settings are active. Attaching a group
is not enough if an existing writer still has a pending reboot.
[AWS MySQL source prerequisites](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.MySQL.html)
and [Aurora parameter groups](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/USER_WorkingWithParamGroups.html).

## 6. Select engine versions and create both clusters and writers

```bash
aws rds describe-db-engine-versions --engine aurora-mysql \
  --query "DBEngineVersions[?starts_with(EngineVersion, '8.0.mysql_aurora.3.')].EngineVersion" --output table
```

```bash
aws rds describe-db-engine-versions --engine aurora-postgresql \
  --query "DBEngineVersions[?starts_with(EngineVersion, '17.')].EngineVersion" --output table
```

```bash
export MYSQL_VERSION=8.0.mysql_aurora.3.13.0
```

```bash
export PG_VERSION=17.10
```

These were available during engineering testing. Confirm they remain listed,
then check that `db.r6g.large` is orderable for each selected version:

```bash
aws rds describe-orderable-db-instance-options --engine aurora-mysql --engine-version "$MYSQL_VERSION" --db-instance-class db.r6g.large --query 'OrderableDBInstanceOptions[].DBInstanceClass'
```

```bash
aws rds describe-orderable-db-instance-options --engine aurora-postgresql --engine-version "$PG_VERSION" --db-instance-class db.r6g.large --query 'OrderableDBInstanceOptions[].DBInstanceClass'
```

Each must return a nonempty result. Review the cost of two paid Aurora writers,
DMS, EC2, storage/I/O, private endpoints and public IPv4 before continuing.
Create the source and target; managed passwords are generated in Secrets Manager:

```bash
aws rds create-db-cluster --db-cluster-identifier "$LAB-source" \
  --engine aurora-mysql --engine-version "$MYSQL_VERSION" \
  --master-username labadmin --manage-master-user-password --database-name hydra \
  --db-subnet-group-name "$LAB-source" --vpc-security-group-ids "$SOURCE_SG" \
  --db-cluster-parameter-group-name "$LAB-mysql" --storage-encrypted \
  --backup-retention-period 3 --deletion-protection --tags Key=Project,Value="$LAB"
```

```bash
aws rds create-db-instance --db-instance-identifier "$LAB-source-writer" \
  --db-cluster-identifier "$LAB-source" --engine aurora-mysql \
  --db-instance-class db.r6g.large --no-publicly-accessible \
  --no-auto-minor-version-upgrade --tags Key=Project,Value="$LAB"
```

```bash
aws rds wait db-instance-available --db-instance-identifier "$LAB-source-writer"
```

```bash
aws rds create-db-cluster --db-cluster-identifier "$LAB-target" \
  --engine aurora-postgresql --engine-version "$PG_VERSION" \
  --master-username labadmin --manage-master-user-password --database-name hydra \
  --db-subnet-group-name "$LAB-target" --vpc-security-group-ids "$TARGET_SG" \
  --db-cluster-parameter-group-name "$LAB-pg" --storage-encrypted \
  --backup-retention-period 3 --deletion-protection --tags Key=Project,Value="$LAB"
```

```bash
aws rds create-db-instance --db-instance-identifier "$LAB-target-writer" \
  --db-cluster-identifier "$LAB-target" --engine aurora-postgresql \
  --db-instance-class db.r6g.large --no-publicly-accessible \
  --no-auto-minor-version-upgrade --tags Key=Project,Value="$LAB"
```

```bash
aws rds wait db-instance-available --db-instance-identifier "$LAB-target-writer"
```

A waiter may time out while AWS is still provisioning. Describe the named
instance and retry the waiter; do not create another cluster to solve a timeout.
This baseline creates one writer per engine, without reader instances.

```bash
aws rds describe-db-clusters --db-cluster-identifier "$LAB-source" \
  --query 'DBClusters[0].{State:Status,Writer:Endpoint,Port:Port,Secret:MasterUserSecret.SecretArn}'
```

```bash
aws rds describe-db-clusters --db-cluster-identifier "$LAB-target" \
  --query 'DBClusters[0].{State:Status,Writer:Endpoint,Port:Port,Secret:MasterUserSecret.SecretArn}'
```

```bash
export SOURCE_HOST=$(aws rds describe-db-clusters --db-cluster-identifier "$LAB-source" --query 'DBClusters[0].Endpoint' --output text)
```

```bash
export TARGET_HOST=$(aws rds describe-db-clusters --db-cluster-identifier "$LAB-target" --query 'DBClusters[0].Endpoint' --output text)
```

Record both writer endpoints and managed secret ARNs. Also record the actual
writer identifiers, so Console-created writers can use the same later steps:

```bash
export SOURCE_WRITER_ID=$(aws rds describe-db-clusters --db-cluster-identifier "$LAB-source" --query 'DBClusters[0].DBClusterMembers[?IsClusterWriter].DBInstanceIdentifier | [0]' --output text)
```

```bash
export TARGET_WRITER_ID=$(aws rds describe-db-clusters --db-cluster-identifier "$LAB-target" --query 'DBClusters[0].DBClusterMembers[?IsClusterWriter].DBInstanceIdentifier | [0]' --output text)
```

 **Expected:** Available,
ports 3306 and 5432, encrypted clusters, private writers. Verify **RDS → Databases
→ writer → Connectivity & security → Publicly accessible: No**.
[AWS create cluster](https://docs.aws.amazon.com/cli/latest/reference/rds/create-db-cluster.html),
[create writer](https://docs.aws.amazon.com/cli/latest/reference/rds/create-db-instance.html),
[managed master passwords](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-secrets-manager.html).

## 7. Create the runner IAM role and EC2 instance

```bash
cat > ec2-trust.json <<'JSON'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}
JSON
```

```bash
aws iam create-role --role-name "$LAB-runner" --assume-role-policy-document file://ec2-trust.json
```

```bash
aws iam attach-role-policy --role-name "$LAB-runner" --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
```

```bash
aws iam create-instance-profile --instance-profile-name "$LAB-runner"
```

```bash
aws iam add-role-to-instance-profile --instance-profile-name "$LAB-runner" --role-name "$LAB-runner"
```

```bash
export RUNNER_AMI=$(aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 --query Parameter.Value --output text)
```

```bash
export RUNNER_ID=$(aws ec2 run-instances --image-id "$RUNNER_AMI" --instance-type t3.large \
  --subnet-id "$RUNNER_SUBNET" --security-group-ids "$RUNNER_SG" --associate-public-ip-address \
  --iam-instance-profile Name="$LAB-runner" --metadata-options HttpTokens=required \
  --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":60,"VolumeType":"gp3","Encrypted":true,"DeleteOnTermination":true}}]' \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$LAB-runner},{Key=Project,Value=$LAB}]" \
  --query 'Instances[0].InstanceId' --output text)
```

```bash
aws ec2 wait instance-status-ok --instance-ids "$RUNNER_ID"
```

```bash
aws ssm describe-instance-information --filters Key=InstanceIds,Values="$RUNNER_ID" \
  --query 'InstanceInformationList[].{ID:InstanceId,State:PingStatus}'
```

If IAM propagation causes `Invalid IAM Instance Profile`, wait briefly and retry
only `run-instances` after checking **EC2 → Instances** for a created runner.
**Expected:** one runner, SSM Online, no inbound SSH. No user-data installer is
hidden in this launch: you install each package in the next lesson.
[AWS run-instances](https://docs.aws.amazon.com/cli/latest/reference/ec2/run-instances.html)
and [Session Manager setup](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-getting-started.html).

## 8. Create the DMS service roles, subnet group and instance

First inspect these account-level roles:

```bash
aws iam get-role --role-name dms-vpc-role
```

```bash
aws iam get-role --role-name dms-cloudwatch-logs-role
```

For each role that returns `NoSuchEntity`, create only that missing role below.
If it exists, inspect its trust and attached policies and reuse it; do not replace
an account-level role used by other labs.

```bash
cat > dms-service-trust.json <<'JSON'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"dms.amazonaws.com"},"Action":"sts:AssumeRole"}]}
JSON
```

```bash
aws iam create-role --role-name dms-vpc-role --assume-role-policy-document file://dms-service-trust.json
```

```bash
aws iam attach-role-policy --role-name dms-vpc-role --policy-arn arn:aws:iam::aws:policy/service-role/AmazonDMSVPCManagementRole
```

```bash
aws iam create-role --role-name dms-cloudwatch-logs-role --assume-role-policy-document file://dms-service-trust.json
```

```bash
aws iam attach-role-policy --role-name dms-cloudwatch-logs-role --policy-arn arn:aws:iam::aws:policy/service-role/AmazonDMSCloudWatchLogsRole
```

```bash
aws dms create-replication-subnet-group --replication-subnet-group-identifier "$LAB-dms" \
  --replication-subnet-group-description "$LAB private DMS" --subnet-ids "$TARGET_A" "$TARGET_B"
```

```bash
aws dms describe-engine-versions --query 'EngineVersions[].Version' --output table
```

```bash
export DMS_VERSION=3.6.1
```

Confirm your chosen version is listed. The Secrets Manager interface endpoint is
needed because the DMS instance has no internet route:

```bash
export SECRETS_VPCE=$(aws ec2 create-vpc-endpoint --vpc-id "$TARGET_VPC" \
  --service-name "com.amazonaws.$AWS_REGION.secretsmanager" --vpc-endpoint-type Interface \
  --subnet-ids "$TARGET_A" "$TARGET_B" --security-group-ids "$SECRETS_SG" \
  --private-dns-enabled --query VpcEndpoint.VpcEndpointId --output text)
```

```bash
export DMS_ARN=$(aws dms create-replication-instance --replication-instance-identifier "$LAB" \
  --replication-instance-class dms.t3.medium --engine-version "$DMS_VERSION" \
  --allocated-storage 100 --replication-subnet-group-identifier "$LAB-dms" \
  --vpc-security-group-ids "$DMS_SG" --no-publicly-accessible --no-multi-az \
  --no-auto-minor-version-upgrade --tags Key=Project,Value="$LAB" \
  --query ReplicationInstance.ReplicationInstanceArn --output text)
```

```bash
aws dms wait replication-instance-available --filters Name=replication-instance-arn,Values="$DMS_ARN"
```

```bash
aws dms describe-replication-instances --filters Name=replication-instance-arn,Values="$DMS_ARN" \
  --query 'ReplicationInstances[].{ID:ReplicationInstanceIdentifier,State:ReplicationInstanceStatus,Public:PubliclyAccessible}'
```

**Expected:** Available and Public=false. Create endpoint database users, endpoint
secrets and the separate DMS secrets-access role in Module 05 after initializing
the schemas. Do not store placeholder credentials now.
[AWS DMS prerequisites](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Security.html),
[replication instance CLI](https://docs.aws.amazon.com/cli/latest/reference/dms/create-replication-instance.html),
[DMS Secrets Manager access](https://docs.aws.amazon.com/dms/latest/userguide/security_iam_secretsmanager.html).

## 9. Record your resources and install Hydra yourself

In `worksheet.txt`, record SOURCE_VPC, TARGET_VPC, all five subnets, three route
tables, PEER, IGW, five SGs, both cluster/writer names and endpoints, both master
secret ARNs, RUNNER_ID, SECRETS_VPCE, DMS_ARN and any shared roles you reused.
These values let you reconnect and later delete only your lab.

Continue to [install the runner packages, create database users and start Hydra](application.md).
That page contains the actual package, SQL and Docker commands. Do not use the
optional Terraform or Python bootstrap tools to bypass the learning steps.

**Checkpoint:** your own worksheet, both private writers Available, DMS Available,
runner Online, correct routes and SGs. Infrastructure availability is not a
successful migration.
