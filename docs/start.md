# Start with an empty lab

You will create, configure, test and remove the lab yourself. An instructor's
previous deployment is not a prerequisite and does not count as your work.
Use a new resource prefix in your assigned sandbox; do not delete or reuse
someone else's resources to obtain an empty starting point.

## 1. Sign in and identify the account

1. Open your organization's AWS access portal and select the assigned sandbox
   account and training role. If it uses direct IAM sign-in, use the account's
   supplied sign-in URL. Never create access keys just to follow this guide.
2. In the AWS Console's account menu, record the 12-digit account ID.
3. Select **US East (N. Virginia), us-east-1**.
4. Open **CloudShell** from the Console toolbar. Select Bash and run:

```bash
aws sts get-caller-identity
```

```bash
aws --version
```

The returned account must match the Console. Use CloudShell for the AWS CLI
creation steps; it is already authenticated. You also need workstation AWS CLI
credentials for SSM port forwarding. With IAM Identity Center, on your workstation:

```bash
aws configure sso --profile hydra-lab
```

```bash
aws sso login --profile hydra-lab
```

```bash
aws sts get-caller-identity --profile hydra-lab
```

Enter the SSO start URL, SSO region, account and role from your organization's
access portal. Choose us-east-1 as the default service region. Follow the browser
sign-in prompt. For Bash terminals set `export AWS_PROFILE=hydra-lab`; in PowerShell
set `$env:AWS_PROFILE="hydra-lab"`. Do not invent SSO settings.
[AWS SSO configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
and [CloudShell setup](https://docs.aws.amazon.com/cloudshell/latest/userguide/getting-started.html).

## 2. Install workstation tools

Follow the [numbered workstation installation steps](workstation.md) for your OS.

| Tool | Installation and check | Used for |
|---|---|---|
| AWS CLI v2 | Follow the OS-specific installer in [AWS CLI installation](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html); open a new terminal; `aws --version` must show aws-cli/2 | SSM tunnel and CLI alternative |
| Session Manager plugin | Select your OS in [AWS plugin installation](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html); run `session-manager-plugin` | Private portal and database tunnels |
| AWS SCT desktop | Follow the complete [SCT installation/connection lesson](04-sct/console.md) | Schema assessment and conversion GUI |
| MySQL and PostgreSQL JDBC | Download the versions/URLs shown in the SCT lesson; select both JARs in SCT | Database connectivity |

The native AWS CLI blocks use **Bash** (CloudShell or Linux/macOS terminal).
For SCT desktop, AWS currently lists **Windows, Fedora and Ubuntu 64-bit**.
Use a supported desktop for the GUI route. A Mac can use the documented SCT CLI
on the runner, but this is a separate interface, not a claim of native Mac GUI support.

You install Docker, Python and the application on your newly created runner in
Module 02. A preinstalled instructor workstation, Terraform state or runtime
JSON file is not required. Terraform/Python deployment helpers in the source
repository are optional engineering references, not the main learning path.

## 3. Record your lab settings before provisioning

Copy the [complete lab worksheet](worksheet.md) into your private notes. Begin
with these settings:

| Setting | Your value |
|---|---|
| Account / role | Your assigned sandbox account and role |
| Region | us-east-1 |
| Resource prefix | A new name, for example hydra-practice-01 |
| Source / target CIDRs | 10.81.0.0/16 and 10.82.0.0/16, after checking for conflicts |
| Two available AZs | Select from your account's describe-availability-zones output |
| Spend limit / cleanup date | Record before creating paid resources |
| Hydra baseline | v2.2.0 on both engines; customer-version confirmation remains necessary |

Your role needs the lab's VPC, EC2, RDS, DMS, IAM/PassRole, SSM, Secrets Manager
and CloudWatch permissions. If an operation returns AccessDenied, record the
exact action and ask your account administrator to grant the required lab-scoped
access; do not switch to an unrelated AWS account.

Two Aurora writers, DMS, EC2, storage, I/O, private endpoints and public IPv4 all
incur charges. Use [AWS Pricing Calculator](https://calculator.aws/) for your
region and record a cleanup date. A tag or closed browser does not stop billing.

## 4. Understand the workspaces

| Name in the guide | Where commands run |
|---|---|
| CloudShell / AWS operator | AWS CLI control commands using your Console identity |
| Workstation | SCT desktop and local browser; AWS CLI SSM tunnels |
| Runner / ec2-user | Your EC2 machine, /opt/hydra-practice; SQL clients and application containers |
| MySQL prompt | Commands after opening the source mysql client |
| PostgreSQL prompt | Commands after opening psql against the stated target database |

The training topology uses one account, two peered VPCs and Docker on EC2.
It demonstrates real Aurora/SCT/DMS. Cross-account IAM, production EKS/ArgoCD and
customer-specific traffic require a separate rehearsal. All identities/data here
are synthetic; the 35 GiB client-heavy profile is not a measured customer distribution.

## 5. Follow this order and save your own evidence

1. [Create the infrastructure - Console](02-aws/console.md) or [AWS CLI](02-aws/build.md).
2. [Install Hydra and create SQL users](02-aws/application.md).
3. [Restore MySQL and exercise the application](03-data/build.md).
4. [Assess and convert - SCT GUI](04-sct/console.md) or [SCT CLI](04-sct/build.md).
5. [Configure full load and CDC - DMS Console](05-dms/console.md) or [AWS CLI](05-dms/build.md).
6. [Validate and cut over](06-cutover/build.md), then recover failures and clean up.

At every checkpoint record your own timestamps, settings and observed results.
Keep secrets/tokens out of evidence. The browser's completion checkbox tracks
reading, not whether AWS actually passed a test.
