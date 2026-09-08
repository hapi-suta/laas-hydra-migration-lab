# Start here: use your laptop

**Start on your own laptop or desktop computer.** In this guide, **workstation**
means that computer. You will use its browser to create the lab in AWS. Later,
you will open a terminal connected to an EC2 machine in AWS and run the app and
database commands there.

## Before opening AWS

Have these details from your instructor or AWS administrator:

- Your AWS sign-in link, assigned account and training role. **KA001** is a lab
  account label; ask for its actual 12-digit AWS account ID so you can check it.
- Your approved AWS CLI sign-in method. For IAM Identity Center, get the SSO
  start URL and SSO Region as well as the account and role.
- Permission to install the laptop tools below and create the lab resources.
- A new resource name such as `comcast-student-01`, plus your cleanup date.

If those details have not been supplied, get them before creating resources.
The public guide and lab downloads do not require a GitHub account.

## Choose the computer for the SCT desktop exercise

The browser and AWS CLI parts can start on Windows, macOS or Linux. For the SCT
desktop exercise in task 3, arrange a **64-bit Windows, Ubuntu or Fedora desktop**.
Windows lets you follow the PowerShell and SCT desktop steps on one computer.
AWS does not list a native macOS SCT desktop app. If you use a Mac, arrange access
to a supported desktop for that exercise, or choose the clearly marked SCT CLI
alternative on your AWS runner.
[AWS SCT supported operating systems](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Installing.html).

## Which computer does each job?

| Place | What you do there | When |
|---|---|---|
| Laptop browser | Read this guide and use the AWS Console | Start here and task 1 |
| Laptop terminal | Sign in with AWS CLI and keep private connections open | Setup below, then tasks 2 and 3 |
| EC2 runner in AWS | Download the lab files and data, run Hydra and run SQL clients | Create it in task 1; use it from task 2 |
| SCT desktop on your supported computer | View the schema assessment and conversion | Task 3 |
| AWS DMS service | Copy rows between the two AWS databases | Task 4 |
| Laptop browser again | Sign in as Alice and Bob and check the app | Tasks 2, 4, 5 and 6 |

The 35 GiB dataset goes into **Aurora MySQL in AWS**. You download its archive
on the runner during task 2. You do not need to install MySQL, PostgreSQL or
Docker on your laptop for this route.

**First actions:** keep this guide open in one browser tab, open your AWS
sign-in link in a second tab, then follow step 1 below. After steps 1-4 you should
have verified access and a completed setup worksheet. Only then begin task 1.
`http://localhost:8080` will become useful after you start the app and open its
connection in task 2; it will not show a lab app on a fresh laptop.

## Use your own empty lab resources

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
4. Keep the account ID and Region in your worksheet. These are the values you will check before creating resources.

<details class="instructions" markdown="1">
<summary>CLI alternative: verify the same account in CloudShell</summary>

Open **CloudShell** from the Console toolbar. Select Bash and run:

```bash
aws sts get-caller-identity
```

```bash
aws --version
```

The returned account must match the Console. CloudShell is already authenticated. Expected: an `Account` value matching your 12-digit account ID and a version starting with `aws-cli/2`.

</details>

## 2. Install workstation tools

On **your laptop**, follow the [numbered installation steps](workstation.md) for
your operating system. Install and verify **AWS CLI v2** and the **Session Manager
plugin** now. Return here for step 3. Install SCT and its JDBC drivers when you
reach task 3; confirm access to a supported desktop now.

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
task 2. A preinstalled instructor workstation, Terraform state or runtime
JSON file is not required. Terraform/Python deployment helpers in the source
repository are optional engineering references, not the main learning path.

## 3. Sign in on your workstation for the private app connection

Even on the Console path, your browser needs a Session Manager tunnel to reach
the private app later. A tunnel forwards a port on your laptop to the app in AWS.
Your browser's AWS sign-in does not automatically sign in the CLI on your laptop.

On Windows, open **Start**, type **PowerShell**, and open it. On macOS, open
**Terminal** from Applications → Utilities. On Linux, open your terminal app.
The three commands below work in those terminals. Run one at a time.

With IAM Identity Center, on **your laptop**:

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

**Expected:** the last command returns JSON containing your assigned 12-digit
`Account`. Compare it with the AWS Console account you recorded in step 1.
If your organization does not use IAM Identity Center, use the CLI login method
and profile supplied by its administrator instead of running `aws configure sso`.
Resolve laptop CLI access before creating the lab; you will need it to reach the
private app.

[AWS SSO configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
and [CloudShell setup](https://docs.aws.amazon.com/cloudshell/latest/userguide/getting-started.html).

## 4. Record your lab settings before provisioning

Copy the [complete lab worksheet](worksheet.md) into your private notes. Begin
with these settings:

| Setting | Your value |
|---|---|
| Account / role | Your assigned sandbox account and role |
| Region | us-east-1 |
| Resource prefix | A new name, for example hydra-practice-01 |
| Source / target CIDRs | 10.81.0.0/16 and 10.82.0.0/16, after checking for conflicts |
| Two available AZs | Choose two available zones in the Console subnet form in task 1 |
| Spend limit / cleanup date | Record before creating paid resources |
| Hydra baseline | v2.2.0 on both engines; customer-version confirmation remains necessary |

Your role needs the lab's VPC, EC2, RDS, DMS, IAM/PassRole, SSM, Secrets Manager
and CloudWatch permissions. If an operation returns AccessDenied, record the
exact action and ask your account administrator to grant the required lab-scoped
access; do not switch to an unrelated AWS account.

The Aurora source writer, RDS PostgreSQL instance, DMS, EC2, storage, I/O, private endpoints and public IPv4 all
incur charges. Use [AWS Pricing Calculator](https://calculator.aws/) for your
region and record a cleanup date. A tag or closed browser does not stop billing.

## 5. Understand the workspaces

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

### Enter commands and edit files

- Read **Where** before each procedure. Run Bash commands in the named terminal
  and SQL statements inside the named MySQL or PostgreSQL client.
- Replace `YOUR_...` placeholders with values from your worksheet before running
  a command. Variables such as `$LAB` use values you exported in that terminal.
  A new terminal needs those exports again.
- Copy one code block at a time and check its expected result. Do not continue
  past an error or run both creation alternatives for the same resource.
- When a step says `vi filename`, press **i**, paste or type the shown content,
  replace its placeholders, then press **Esc**, type **:wq** and press **Enter**
to save. To leave without saving, press **Esc**, type **:q!** and press **Enter**.
- `export`, `mkdir` and `chmod` often return to the prompt without printing anything. That is normal if no error appears. Commands that create AWS resources may take several minutes; wait for the stated status before continuing.
- Leave a MySQL prompt with `exit`; leave a PostgreSQL prompt with `\q`.
  This returns you to the runner shell.

## 6. Begin the six tasks

Open [task 1: build the source and target](lab/01-build.md). Each task ends with the checks to complete and a link to the next task.

Save your own timestamps, settings and results. Keep secrets and tokens out of evidence. The browser's completion checkbox records your progress; it does not verify AWS resources.
