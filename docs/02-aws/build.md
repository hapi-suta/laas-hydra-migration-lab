# Provision the Aurora practice environment

**Environment:** Laptop with sandbox AWS credentials, then Runner as ec2-user. **Checkpoint:** both Aurora writers available, SSM runner online, DMS instance available.

## 1. Select the sandbox account

On **Laptop**, as **your user**, set the AWS profile your instructor assigned:

```bash
export AWS_PROFILE=your-sandbox-profile
```

Replace the profile name with a configured profile; do not type a production profile. On **Laptop**, as **your user**:

```bash
.venv/bin/python scripts/cloud.py preflight
```

This is read-only. It displays the authenticated account, available engine versions, and whether DMS service roles already exist. Save the result. Choose an Aurora MySQL 3.x release and Aurora PostgreSQL 17.x release from your region's output; check that DMS 3.5.4 or a later tested version is available.

## 2. Configure Terraform

On **Laptop**, as **your user**:

```bash
cp infra/terraform.tfvars.example infra/terraform.tfvars
```

On **Laptop**, as **your user**:

```bash
vi infra/terraform.tfvars
```

Set `expected_account_id`, the two engine versions, and your unique lab name. Set `create_dms_service_roles=false` if both named service roles already exist. Leave deletion protection enabled. Do not put passwords in this file.

On **Laptop**, as **your user**:

```bash
terraform -chdir=infra init
```

`-chdir` runs Terraform in the infrastructure directory. On **Laptop**, as **your user**:

```bash
terraform -chdir=infra plan -out=lab.tfplan
```

`-out` saves the reviewed execution plan. Inspect the account, resource names, subnet routes, two Aurora clusters, instance classes, and absence of public database access. Approve the expected spend with your instructor.

On **Laptop**, as **your user**:

```bash
terraform -chdir=infra apply lab.tfplan
```

Wait for Terraform to finish. AWS provisioning time varies; do not interrupt just because Aurora takes longer than EC2.

On **Laptop**, as **your user**:

```bash
terraform -chdir=infra output -json lab > runtime/cloud.json
```

`-json` exports endpoints and resource IDs, not secret values.

## 3. Open the runner

Use the EC2 console's **Connect → Session Manager**, or the AWS CLI with the `runner_id` from `runtime/cloud.json`.

On **Runner**, as **ssm-user**, switch to the lab owner:

```bash
sudo su - ec2-user
```

On **Runner**, as **ec2-user**:

```bash
cd /opt/hydra-practice
```

Download and extract the same versioned lab bundle from the customer site into this directory. Copy the non-secret `runtime/cloud.json` contents from your laptop into a file at the same relative path using `vi`. Do not transfer your laptop `.env`; initialize fresh cloud credentials.

On **Runner**, as **ec2-user**:

```bash
python3 -m venv .venv
```

On **Runner**, as **ec2-user**:

```bash
.venv/bin/pip install -r requirements.txt
```

On **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/cloud.py bootstrap
```

The script verifies the AWS account, retrieves administrator secrets using the instance role, creates Hydra schema-owner roles, enables 72-hour source binlog retention, and writes private connection configuration. It selects `compose.cloud.yaml` for subsequent Compose commands.

On **Runner**, as **ec2-user**:

```bash
python3 scripts/lab.py up
```

## 4. Open the portal through SSM

On **Laptop**, as **your user**, replace the instance ID from your Terraform output:

```bash
aws ssm start-session --target i-REPLACE --document-name AWS-StartPortForwardingSession --parameters '{"portNumber":["8080"],"localPortNumber":["8080"]}'
```

`--target` selects your runner; the document forwards its port 8080 to your laptop. Keep this terminal open. Stop the local demo first if it occupies that port. Open `http://localhost:8080` and repeat the Alice login and refresh checks.

**Gate:** capture real Terraform output, successful SSM connection, and application checks. These procedures remain cloud-unverified until the instructor executes this gate.
